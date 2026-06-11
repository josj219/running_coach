// 설정 화면 — 프로필/목표 조회 + Strava 연동
import React, { useEffect, useState } from 'react';
import { Linking, Pressable, ScrollView, Text, View } from 'react-native';
import { api } from '../api';
import { C, fmtDays } from '../theme';
import { Banner, Card, Loading, SectionLabel } from '../ui';

export default function Settings() {
  const [profile, setProfile] = useState(null);
  const [goal, setGoal] = useState(null);
  const [integ, setInteg] = useState(null);
  const [slots, setSlots] = useState([]);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const [p, g, i, a] = await Promise.all([
        api.profile(), api.goal(), api.integrations(), api.availability(),
      ]);
      setProfile(p); setGoal(g); setInteg(i); setSlots(a.slots);
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  if (error) return <View style={{ padding: 16 }}><Banner tone="error">{error}</Banner></View>;
  if (!profile) return <Loading />;

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 130, gap: 18 }}>
      <Text style={{ color: C.label, fontSize: 32, fontWeight: '800', letterSpacing: -0.8, paddingTop: 8 }}>설정</Text>

      <View>
        <SectionLabel>프로필</SectionLabel>
        <Card pad={0}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, padding: 16, paddingBottom: 12 }}>
            <View style={{ width: 54, height: 54, borderRadius: 27, backgroundColor: C.tint,
              alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: '#fff', fontSize: 22, fontWeight: '800' }}>{(profile.nickname || '러')[0]}</Text>
            </View>
            <View>
              <Text style={{ color: C.label, fontSize: 20, fontWeight: '700' }}>{profile.nickname}</Text>
              <Text style={{ color: C.label2, fontSize: 13.5 }}>
                러닝 {profile.career_years ?? '-'}년차 · {profile.age ?? '-'}세</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', borderTopWidth: 0.5, borderTopColor: C.sep, paddingVertical: 12 }}>
            {[['10K', profile.pb_10k], ['하프', profile.pb_half], ['풀', profile.pb_full]].map(([k, v], i) => (
              <View key={k} style={{ flex: 1, alignItems: 'center',
                borderLeftWidth: i ? 0.5 : 0, borderLeftColor: C.sep }}>
                <Text style={{ color: C.label3, fontSize: 11.5, fontWeight: '600' }}>{k} PB</Text>
                <Text style={{ color: C.label, fontSize: 17, fontWeight: '700', marginTop: 3 }}>
                  {v ? v.replace(/^00:/, '') : '—'}</Text>
              </View>
            ))}
          </View>
        </Card>
      </View>

      <View>
        <SectionLabel>목표</SectionLabel>
        <Card>
          <Text style={{ color: C.label, fontSize: 16.5, fontWeight: '700' }}>
            🏆 {goal?.race_type || '목표 미설정'} {goal?.target_time ? `sub ${goal.target_time.slice(1, 5)}` : ''}</Text>
          <Text style={{ color: C.label2, fontSize: 13.5, marginTop: 4 }}>
            {goal?.target_date || '날짜 미정'}{goal?.dday != null ? ` · D-${goal.dday}` : ''}</Text>
        </Card>
      </View>

      <View>
        <SectionLabel>훈련 가능 시간</SectionLabel>
        <Card pad={0}>
          {slots.map((s, i) => (
            <View key={s.id ?? i} style={{ flexDirection: 'row', alignItems: 'center', gap: 12,
              padding: 13, paddingHorizontal: 16,
              borderBottomWidth: i < slots.length - 1 ? 0.5 : 0, borderBottomColor: C.sep }}>
              <View style={{ minWidth: 44, alignItems: 'center', backgroundColor: `${C.tint}1F`,
                borderRadius: 8, paddingVertical: 5, paddingHorizontal: 7 }}>
                <Text style={{ color: C.tint, fontSize: 12.5, fontWeight: '700' }}>{fmtDays(s.days)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.label, fontSize: 15.5, fontWeight: '600' }}>{s.title}</Text>
                <Text style={{ color: C.label2, fontSize: 13 }}>
                  {s.duration_min ? `${s.duration_min}분` : ''}{s.place ? ` · ${s.place}` : ''}</Text>
              </View>
            </View>
          ))}
          <View style={{ padding: 13, paddingHorizontal: 16, borderTopWidth: slots.length ? 0.5 : 0, borderTopColor: C.sep }}>
            <Text style={{ color: C.label3, fontSize: 13 }}>주간 계획의 기준이 돼요 · 편집은 웹앱에서</Text>
          </View>
        </Card>
      </View>

      <View>
        <SectionLabel>데이터 연동</SectionLabel>
        <Card pad={0}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, paddingHorizontal: 16 }}>
            <View style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: C.strava,
              alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontSize: 16 }}>⚡</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.label, fontSize: 16, fontWeight: '600' }}>Strava</Text>
              <Text style={{ color: C.label2, fontSize: 13 }}>
                {integ?.strava.connected
                  ? `연결됨${integ.strava.athlete_name ? ` · ${integ.strava.athlete_name}` : ''}`
                  : integ?.strava.available ? '거리·페이스·심박 자동 입력' : '서버에 API 키 설정 필요'}</Text>
            </View>
            {integ?.strava.connected ? (
              <Pressable onPress={async () => { await api.stravaDisconnect(); load(); }}
                style={{ backgroundColor: C.fill, borderRadius: 999, paddingVertical: 7, paddingHorizontal: 13 }}>
                <Text style={{ color: C.red, fontWeight: '600', fontSize: 13.5 }}>해제</Text></Pressable>
            ) : (
              <Pressable disabled={!integ?.strava.available}
                onPress={async () => {
                  const r = await api.stravaAuthUrl();
                  await Linking.openURL(r.url); // 브라우저에서 승인 → 서버에 토큰 저장됨
                  setTimeout(load, 4000);
                }}
                style={{ backgroundColor: integ?.strava.available ? C.strava : C.fill,
                  borderRadius: 999, paddingVertical: 7, paddingHorizontal: 14 }}>
                <Text style={{ color: integ?.strava.available ? '#fff' : C.label3,
                  fontWeight: '700', fontSize: 13.5 }}>연결</Text></Pressable>
            )}
          </View>
          <View style={{ borderTopWidth: 0.5, borderTopColor: C.sep, flexDirection: 'row', gap: 12,
            padding: 14, paddingHorizontal: 16 }}>
            <View style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: '#11A9ED',
              alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontSize: 16 }}>⌚</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.label, fontSize: 16, fontWeight: '600' }}>Garmin</Text>
              <Text style={{ color: C.label2, fontSize: 13, lineHeight: 19, marginTop: 2 }}>
                Garmin Connect 앱에서 Strava 자동 업로드를 켜면 Strava 연동 하나로 가민 기록이 들어와요.</Text>
            </View>
          </View>
        </Card>
      </View>

      <Card>
        <Text style={{ color: C.label2, fontSize: 13.5 }}>러닝 코치 v2.0.0 · 프로필·목표 편집은 웹앱에서</Text>
      </Card>
    </ScrollView>
  );
}
