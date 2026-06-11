// 기록 화면 — 주별 추세 + 최근 훈련
import React, { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { api } from '../api';
import { C, wmeta } from '../theme';
import { Banner, Card, Loading, RecoveryBadge, SectionLabel } from '../ui';

export default function History() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, l] = await Promise.all([api.weeklyStats(6), api.logs(30)]);
        setStats(s.weeks); setLogs(l.items);
      } catch (e) { setError(e.message); }
    })();
  }, []);

  if (error) return <View style={{ padding: 16 }}><Banner tone="error">{error}</Banner></View>;
  if (!stats || !logs) return <Loading label="불러오는 중…" />;

  const max = Math.max(...stats.map((w) => w.week_km), 1);

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 130, gap: 16 }}>
      <Text style={{ color: C.label, fontSize: 32, fontWeight: '800', letterSpacing: -0.8, paddingTop: 8 }}>기록</Text>

      <View>
        <SectionLabel>주간 거리 추세</SectionLabel>
        <Card pad={18}>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 10, height: 120 }}>
            {[...stats].reverse().map((w) => (
              <View key={w.iso_week} style={{ flex: 1, alignItems: 'center', gap: 6 }}>
                <Text style={{ fontSize: 11, fontWeight: '700', color: w.current ? C.tint : C.label2 }}>
                  {w.week_km > 0 ? w.week_km : ''}</Text>
                <View style={{ width: '100%', maxWidth: 30, borderRadius: 8,
                  height: w.week_km === 0 ? 4 : Math.max(10, (w.week_km / max) * 90),
                  backgroundColor: w.current ? C.tint : `${C.tint}47` }} />
                <Text style={{ fontSize: 10.5, color: w.current ? C.label : C.label3,
                  fontWeight: w.current ? '700' : '500' }}>
                  {w.current ? '이번 주' : `W${w.iso_week.split('W')[1]}`}</Text>
              </View>
            ))}
          </View>
        </Card>
      </View>

      <View>
        <SectionLabel>최근 훈련</SectionLabel>
        {logs.length === 0 ? (
          <Card pad={24}><Text style={{ color: C.label2, fontSize: 15, textAlign: 'center' }}>
            아직 기록이 없어요. 오늘 탭에서 첫 훈련을 기록해 보세요.</Text></Card>
        ) : (
          <Card pad={0}>
            {logs.map((log, i) => {
              const w = wmeta(log.kind);
              return (
                <View key={log.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12,
                  padding: 13, paddingHorizontal: 16,
                  borderBottomWidth: i < logs.length - 1 ? 0.5 : 0, borderBottomColor: C.sep }}>
                  <View style={{ width: 38, height: 38, borderRadius: 11, backgroundColor: w.color,
                    alignItems: 'center', justifyContent: 'center' }}>
                    <Text style={{ fontSize: 17 }}>{w.emoji}</Text></View>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: C.label, fontSize: 15.5, fontWeight: '600' }}>
                      {log.distance_km > 0 ? `${log.distance_km}km` : w.label}
                      {log.avg_pace ? <Text style={{ color: C.label2, fontWeight: '400' }}> · {log.avg_pace}/km</Text> : null}
                    </Text>
                    <Text style={{ color: C.label2, fontSize: 13, marginTop: 1 }}>
                      {log.log_date.slice(5).replace('-', '/')} · {w.label}</Text>
                  </View>
                  {log.review && <RecoveryBadge level={log.review.recovery} />}
                </View>
              );
            })}
          </Card>
        )}
      </View>
    </ScrollView>
  );
}
