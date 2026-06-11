// 기록 입력 모달 — Strava 자동 채움 + 최소 입력(거리·시간·몸상태)
import React, { useEffect, useMemo, useState } from 'react';
import { Modal, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { api } from './api';
import { autoPace, C, FEEL_OPTIONS, wmeta } from './theme';
import { Banner, Card, Chip, CTA, Loading, Metric, RecoveryBadge } from './ui';

const BODY_PARTS = ['무릎', '발목', '정강이', '햄스트링', '종아리', '발바닥', '고관절', '허리'];

function Num({ value, onChange, placeholder, unit, flex = 1 }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: C.fill,
      borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, flex }}>
      <TextInput value={value} onChangeText={onChange} placeholder={placeholder}
        placeholderTextColor={C.label3} keyboardType="decimal-pad"
        style={{ flex: 1, fontSize: 22, fontWeight: '700', color: C.label }} />
      {unit ? <Text style={{ color: C.label3, fontSize: 14, fontWeight: '600' }}>{unit}</Text> : null}
    </View>
  );
}

function Label({ children }) {
  return <Text style={{ fontSize: 13, fontWeight: '600', color: C.label2, textTransform: 'uppercase',
    letterSpacing: 0.4, marginTop: 18, marginBottom: 8 }}>{children}</Text>;
}

export default function RecordSheet({ visible, session, todayDate, onClose }) {
  const [form, setForm] = useState({ distance: '', minutes: '', seconds: '', avgHr: '', cadence: '', feel: 3, note: '' });
  const [pain, setPain] = useState([]);
  const [phase, setPhase] = useState('form'); // form | saving | review
  const [review, setReview] = useState(null);
  const [error, setError] = useState(null);
  const [logId, setLogId] = useState(null);
  const [strava, setStrava] = useState(null); // null | 'loading' | items
  const w = wmeta(session?.kind || 'easy');
  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  const durationSec = (parseInt(form.minutes, 10) || 0) * 60 + (parseInt(form.seconds, 10) || 0);
  const pace = useMemo(() => autoPace(form.distance, durationSec), [form.distance, durationSec]);

  useEffect(() => {
    if (!visible) { setPhase('form'); setReview(null); setError(null); setStrava(null); }
  }, [visible]);

  const loadStrava = async () => {
    setStrava('loading');
    try {
      const integ = await api.integrations();
      if (!integ.strava.connected) { setStrava('off'); return; }
      const res = await api.stravaActivities(5);
      setStrava(res.items.length ? res.items : 'empty');
    } catch { setStrava('empty'); }
  };

  const pick = (a) => {
    setForm((p) => ({ ...p, distance: String(a.distance_km ?? ''),
      minutes: a.duration_sec ? String(Math.floor(a.duration_sec / 60)) : '',
      seconds: a.duration_sec ? String(a.duration_sec % 60) : '',
      avgHr: a.avg_hr ? String(a.avg_hr) : '', cadence: a.cadence ? String(a.cadence) : '' }));
    setStrava(null);
  };

  const save = async () => {
    setPhase('saving'); setError(null);
    try {
      const res = await api.saveLog({
        log_date: todayDate, kind: session?.kind || 'easy',
        distance_km: parseFloat(form.distance) || 0,
        duration_sec: durationSec || null,
        avg_pace: pace || null,
        avg_hr: parseInt(form.avgHr, 10) || null,
        cadence: parseInt(form.cadence, 10) || null,
        feel: form.feel, fatigue_num: { 1: 9, 2: 7, 3: 3, 4: 1 }[form.feel],
        pain_part: pain.join(', ') || null, pain_level: pain.length ? 3 : 0,
        user_comment: form.note || null, source: 'manual',
      });
      setLogId(res.id);
      setPhase('review');
      try { setReview(await api.review(res.id)); }
      catch { setError('리뷰 생성 실패 — 기록은 저장됐어요.'); }
    } catch (e) {
      setPhase('form'); setError(`저장 실패: ${e.message}`);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={() => onClose(phase === 'review')}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <View style={{ backgroundColor: C.bg, borderTopLeftRadius: 26, borderTopRightRadius: 26, maxHeight: '92%' }}>
          <View style={{ alignItems: 'center', paddingTop: 10 }}>
            <View style={{ width: 36, height: 4, borderRadius: 2, backgroundColor: C.fill2 }} />
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
            padding: 20, paddingBottom: 14, borderBottomWidth: 0.5, borderBottomColor: C.sep }}>
            <View>
              <Text style={{ color: C.label, fontSize: 20, fontWeight: '700' }}>
                {phase === 'review' ? 'AI 코치 분석' : '훈련 기록'}</Text>
              <Text style={{ color: C.label2, fontSize: 14, marginTop: 2 }}>{session?.title || '오늘 훈련'}</Text>
            </View>
            <Pressable onPress={() => onClose(phase === 'review')}
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: C.fill,
                alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: C.label2, fontSize: 15 }}>✕</Text>
            </Pressable>
          </View>

          <ScrollView style={{ paddingHorizontal: 20 }} contentContainerStyle={{ paddingBottom: 44 }}>
            {phase === 'saving' && <Loading label="저장하고 분석 중…" />}

            {phase === 'review' && (
              <View style={{ paddingTop: 16, gap: 14 }}>
                <Card>
                  <View style={{ flexDirection: 'row' }}>
                    <Metric value={form.distance || '0'} unit="km" label="거리" size={24} />
                    <Metric value={pace || '--'} label="페이스" size={24} />
                    <Metric value={form.avgHr || '--'} label="평균 심박" size={24} />
                  </View>
                </Card>
                {review ? (
                  <Card style={{ backgroundColor: `${w.color}14` }}>
                    <Text style={{ color: w.color, fontSize: 13, fontWeight: '700', marginBottom: 6 }}>코치 분석</Text>
                    <Text style={{ color: C.label, fontSize: 15, lineHeight: 23 }}>{review.coach_comment}</Text>
                    {review.improvements ? (
                      <Text style={{ color: C.label2, fontSize: 14, lineHeight: 21, marginTop: 8 }}>{review.improvements}</Text>
                    ) : null}
                    <View style={{ marginTop: 12 }}><RecoveryBadge level={review.recovery} /></View>
                  </Card>
                ) : error ? <Banner tone="error">{error}</Banner> : <Loading label="AI 코치가 분석 중…" />}
                <CTA onPress={() => onClose(true)}>확인</CTA>
              </View>
            )}

            {phase === 'form' && (
              <View>
                {/* Strava 가져오기 */}
                {strava === null && (
                  <Pressable onPress={loadStrava} style={{ flexDirection: 'row', alignItems: 'center', gap: 12,
                    backgroundColor: `${C.strava}1F`, borderRadius: 16, padding: 14, marginTop: 16 }}>
                    <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: C.strava,
                      alignItems: 'center', justifyContent: 'center' }}>
                      <Text style={{ fontSize: 18 }}>⚡</Text></View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: C.label, fontSize: 15, fontWeight: '700' }}>Strava에서 가져오기</Text>
                      <Text style={{ color: C.label2, fontSize: 13 }}>거리·시간·페이스·심박 자동 입력</Text>
                    </View>
                  </Pressable>
                )}
                {strava === 'loading' && <Text style={{ color: C.label2, marginTop: 16 }}>불러오는 중…</Text>}
                {strava === 'off' && <View style={{ marginTop: 16 }}>
                  <Banner tone="info">설정 탭에서 Strava를 연결하면 자동으로 채워져요.</Banner></View>}
                {strava === 'empty' && <View style={{ marginTop: 16 }}>
                  <Banner tone="info">가져올 활동이 없어요. 직접 입력해 주세요.</Banner></View>}
                {Array.isArray(strava) && strava.map((a) => (
                  <Pressable key={a.id} onPress={() => pick(a)} style={{ flexDirection: 'row', alignItems: 'center',
                    gap: 10, backgroundColor: C.fill, borderRadius: 14, padding: 12, marginTop: 8 }}>
                    <Text style={{ fontSize: 16 }}>🏃</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: C.label, fontSize: 14, fontWeight: '600' }} numberOfLines={1}>{a.name || '러닝'}</Text>
                      <Text style={{ color: C.label2, fontSize: 12.5 }}>
                        {a.start_date?.slice(5, 10)} · {a.distance_km}km · {a.avg_pace}/km</Text>
                    </View>
                    <Text style={{ color: C.strava, fontWeight: '700', fontSize: 13 }}>채우기</Text>
                  </Pressable>
                ))}

                <Label>기본 기록</Label>
                <View style={{ flexDirection: 'row', gap: 10 }}>
                  <Num value={form.distance} onChange={(v) => set('distance', v)} placeholder="0.0" unit="km" />
                  <Num value={form.minutes} onChange={(v) => set('minutes', v)} placeholder="분" />
                  <Num value={form.seconds} onChange={(v) => set('seconds', v)} placeholder="초" />
                </View>
                {pace ? <Text style={{ color: C.label2, fontSize: 13, marginTop: 8 }}>
                  평균 페이스 <Text style={{ color: C.label, fontWeight: '700' }}>{pace} /km</Text> (자동 계산)</Text> : null}

                <Label>오늘 몸 상태</Label>
                <View style={{ flexDirection: 'row', gap: 10 }}>
                  {FEEL_OPTIONS.map((f) => (
                    <Pressable key={f.v} onPress={() => set('feel', f.v)}
                      style={{ flex: 1, paddingVertical: 12, borderRadius: 14, alignItems: 'center',
                        backgroundColor: form.feel === f.v ? C.tint : C.fill }}>
                      <Text style={{ fontSize: 22 }}>{f.emoji}</Text>
                      <Text style={{ fontSize: 11, fontWeight: '600', marginTop: 4,
                        color: form.feel === f.v ? '#fff' : C.label3 }}>{f.label}</Text>
                    </Pressable>
                  ))}
                </View>

                <Label>심박 · 케이던스 (선택)</Label>
                <View style={{ flexDirection: 'row', gap: 10 }}>
                  <Num value={form.avgHr} onChange={(v) => set('avgHr', v)} placeholder="평균" unit="bpm" />
                  <Num value={form.cadence} onChange={(v) => set('cadence', v)} placeholder="170" unit="spm" />
                </View>

                <Label>불편한 곳 (선택)</Label>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {BODY_PARTS.map((p) => (
                    <Chip key={p} label={p} color={C.red} on={pain.includes(p)}
                      onPress={() => setPain((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p])} />
                  ))}
                </View>

                <Label>한 줄 소감 (선택)</Label>
                <View style={{ backgroundColor: C.fill, borderRadius: 12, padding: 12 }}>
                  <TextInput value={form.note} onChangeText={(v) => set('note', v)} multiline
                    placeholder="오늘 훈련 어땠나요?" placeholderTextColor={C.label3}
                    style={{ color: C.label, fontSize: 16, minHeight: 48 }} />
                </View>

                {error ? <View style={{ marginTop: 14 }}><Banner tone="error">{error}</Banner></View> : null}
                <View style={{ marginTop: 18 }}>
                  <CTA onPress={save} disabled={!form.distance && !form.minutes}>저장하고 리뷰 받기</CTA>
                </View>
              </View>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
