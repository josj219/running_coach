// 이번 주 화면 — 진행률 + 세션 리스트 + 생성/조정/리포트
import React, { useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';
import { api } from '../api';
import { C, sessionSubtitle, wmeta } from '../theme';
import { Banner, Card, Chip, CTA, Loading, SectionLabel } from '../ui';

const STATUS = { done: '✅', partial: '⚠️', missed: '❌', planned: '○' };

export default function Week({ refreshToday }) {
  const [week, setWeek] = useState(null);
  const [noPlan, setNoPlan] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [schedule, setSchedule] = useState('');
  const [adjustReason, setAdjustReason] = useState('');
  const [showAdjust, setShowAdjust] = useState(false);
  const [busy, setBusy] = useState(null); // 'gen' | 'adjust' | 'eval'

  const load = async () => {
    setLoading(true); setError(null);
    try { setWeek(await api.currentWeek()); setNoPlan(false); }
    catch (e) { e.status === 404 ? setNoPlan(true) : setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <Loading label="불러오는 중…" />;

  // 로컬(KST) 기준 — toISOString()은 UTC라 자정 전후 하루 밀림
  const now = new Date();
  const todayStr = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const wp = week?.progress;

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 130, gap: 16 }}>
      <Text style={{ color: C.label, fontSize: 32, fontWeight: '800', letterSpacing: -0.8, paddingTop: 8 }}>이번 주</Text>
      {error && <Banner tone="error">{error}</Banner>}

      {noPlan && (
        <Card pad={18}>
          <Text style={{ color: C.label, fontSize: 20, fontWeight: '700', marginBottom: 6 }}>이번 주 계획 만들기</Text>
          <Text style={{ color: C.label2, fontSize: 14, lineHeight: 20, marginBottom: 12 }}>
            기본 훈련 시간표(설정 탭)를 기준으로, 이번 주에 다른 점만 알려주세요.</Text>
          <Text style={{ color: C.label2, fontSize: 13, fontWeight: '600', marginBottom: 6 }}>이번 주 특이 일정 (선택)</Text>
          <View style={{ backgroundColor: C.fill, borderRadius: 12, padding: 12, marginBottom: 14 }}>
            <TextInput value={schedule} onChangeText={setSchedule} multiline
              placeholder="기본 시간표와 다른 점만 — 예: 수요일 회식, 금요일 출장" placeholderTextColor={C.label3}
              style={{ color: C.label, fontSize: 15, minHeight: 44 }} />
          </View>
          <CTA busy={busy === 'gen'} onPress={async () => {
            setBusy('gen'); setError(null);
            try { await api.generateWeek({ schedule_note: schedule }); await load(); refreshToday?.(); }
            catch (e) { setError(e.message); }
            finally { setBusy(null); }
          }}>7일 계획 생성</CTA>
        </Card>
      )}

      {week && (
        <>
          {week.direction && (
            <Card style={{ backgroundColor: `${C.tint}14` }}>
              <Text style={{ color: C.label, fontSize: 15, fontWeight: '600', lineHeight: 22 }}>{week.direction}</Text>
            </Card>
          )}
          <Card pad={18}>
            <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 6 }}>
              <Text style={{ color: C.label, fontSize: 30, fontWeight: '700' }}>{wp.week_km}</Text>
              <Text style={{ color: C.label2, fontSize: 15, fontWeight: '600' }}>/ {wp.goal_km ?? '—'} km</Text>
              <Text style={{ color: C.label2, fontSize: 13.5, marginLeft: 'auto' }}>
                완료 {wp.done}/{wp.total} · {wp.completion_rate}%</Text>
            </View>
            <View style={{ height: 8, borderRadius: 4, backgroundColor: C.fill, marginTop: 12, overflow: 'hidden' }}>
              <View style={{ width: `${Math.min(100, wp.goal_km ? (wp.week_km / wp.goal_km) * 100 : 0)}%`,
                height: 8, borderRadius: 4, backgroundColor: C.tint }} />
            </View>
          </Card>

          <View>
            <SectionLabel>일정</SectionLabel>
            <Card pad={0}>
              {week.sessions.map((s, i) => {
                const w = wmeta(s.kind);
                const isToday = s.session_date === todayStr;
                return (
                  <View key={s.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12,
                    padding: 13, paddingHorizontal: 16,
                    backgroundColor: isToday ? `${C.tint}12` : 'transparent',
                    borderBottomWidth: i < week.sessions.length - 1 ? 0.5 : 0, borderBottomColor: C.sep }}>
                    <View style={{ width: 30, alignItems: 'center' }}>
                      <Text style={{ color: C.label3, fontSize: 11, fontWeight: '600' }}>{s.weekday}</Text>
                      <Text style={{ color: isToday ? C.tint : C.label, fontSize: 15, fontWeight: '700' }}>
                        {parseInt(s.session_date.slice(8), 10)}</Text>
                    </View>
                    <View style={{ width: 36, height: 36, borderRadius: 11, backgroundColor: w.color,
                      alignItems: 'center', justifyContent: 'center' }}>
                      <Text style={{ fontSize: 16 }}>{w.emoji}</Text></View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: C.label, fontSize: 15, fontWeight: '600' }} numberOfLines={1}>
                        {s.title || w.label}</Text>
                      <Text style={{ color: C.label2, fontSize: 13 }}>{sessionSubtitle(s)}</Text>
                    </View>
                    <Text style={{ fontSize: 15 }}>{STATUS[s.status] || '○'}</Text>
                  </View>
                );
              })}
            </Card>
          </View>

          {week.evaluation?.coach_message && (
            <Card style={{ backgroundColor: `${C.indigo}14` }}>
              <Text style={{ color: C.indigo, fontSize: 13, fontWeight: '700', marginBottom: 6 }}>
                성장 리포트{week.evaluation.is_partial ? ' (중간)' : ''}</Text>
              <Text style={{ color: C.label, fontSize: 15, lineHeight: 23 }}>{week.evaluation.coach_message}</Text>
            </Card>
          )}

          {showAdjust ? (
            <Card pad={16}>
              <Text style={{ color: C.label, fontSize: 16, fontWeight: '700', marginBottom: 10 }}>계획 조정</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                {['피로 누적', '무릎 통증', '발목 통증', '일정 변경'].map((c) => (
                  <Chip key={c} label={c} on={adjustReason === c} onPress={() => setAdjustReason(c)} />
                ))}
              </View>
              <View style={{ backgroundColor: C.fill, borderRadius: 12, padding: 12, marginBottom: 12 }}>
                <TextInput value={adjustReason} onChangeText={setAdjustReason} multiline
                  placeholder="상황을 적어주세요" placeholderTextColor={C.label3}
                  style={{ color: C.label, fontSize: 15, minHeight: 40 }} />
              </View>
              <CTA busy={busy === 'adjust'} disabled={!adjustReason.trim()} onPress={async () => {
                setBusy('adjust');
                try { const r = await api.adjustWeek(adjustReason); setWeek(r); setShowAdjust(false); refreshToday?.(); }
                catch (e) { setError(e.message); }
                finally { setBusy(null); }
              }}>조정 받기</CTA>
            </Card>
          ) : (
            <View style={{ gap: 10 }}>
              <CTA variant="tinted" busy={busy === 'eval'} onPress={async () => {
                setBusy('eval');
                try { setWeek(await api.evaluateWeek()); }
                catch (e) { setError(e.message); }
                finally { setBusy(null); }
              }}>성장 리포트 만들기</CTA>
              <CTA variant="gray" onPress={() => setShowAdjust(true)}>계획 조정이 필요해요</CTA>
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
}
