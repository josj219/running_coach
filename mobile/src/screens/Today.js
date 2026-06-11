// 오늘 화면 — 상태머신 (웹 Today.jsx와 동일 로직)
import React from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { C, sessionSubtitle, wmeta } from '../theme';
import { Banner, Card, CTA, Hero, Loading, Metric, RecoveryBadge, SectionLabel } from '../ui';

function Tomorrow({ tomorrow }) {
  if (!tomorrow) return null;
  const w = wmeta(tomorrow.kind);
  return (
    <View>
      <SectionLabel>내일 예고</SectionLabel>
      <Card>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <View style={{ width: 46, height: 46, borderRadius: 13, backgroundColor: w.color,
            alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ fontSize: 20 }}>{w.emoji}</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: C.label, fontSize: 17, fontWeight: '600' }}>{tomorrow.title || w.label}</Text>
            <Text style={{ color: C.label2, fontSize: 14, marginTop: 2 }}>{sessionSubtitle(tomorrow)}</Text>
          </View>
        </View>
      </Card>
    </View>
  );
}

export default function Today({ data, loading, error, refresh, onRecord, goWeek }) {
  if (loading) return <Loading label="불러오는 중…" />;
  if (error) return <View style={{ padding: 16 }}><Banner tone="error">{error}</Banner>
    <View style={{ marginTop: 12 }}><CTA variant="gray" onPress={refresh}>재시도</CTA></View></View>;

  const { state, session, tomorrow, log, week_progress: wp, dday } = data;
  const w = session ? wmeta(session.kind) : null;

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 130, gap: 16 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: 8 }}>
        <Text style={{ color: C.label, fontSize: 32, fontWeight: '800', letterSpacing: -0.8 }}>오늘</Text>
        {dday != null && <Text style={{ color: C.tint, fontSize: 13, fontWeight: '700' }}>D-{dday}</Text>}
      </View>

      {state === 'NO_PLAN' && (
        <>
          <Card pad={22}>
            <Text style={{ color: C.label, fontSize: 26, fontWeight: '700', lineHeight: 33 }}>
              이번 주 계획이{'\n'}아직 없어요</Text>
            <Text style={{ color: C.label2, fontSize: 15, marginTop: 8 }}>
              AI 코치가 최근 부하와 회복 상태를 분석해 7일 훈련을 구성해요.</Text>
          </Card>
          <CTA onPress={goWeek}>이번 주 계획 세우기</CTA>
        </>
      )}

      {(state === 'REST_DAY') && (
        <>
          <Hero color="#3a3a3c">
            <Text style={{ fontSize: 28 }}>🛏️</Text>
            <Text style={{ color: '#fff', fontSize: 28, fontWeight: '700', marginTop: 12 }}>오늘은 쉬는 날이에요</Text>
            <Text style={{ color: 'rgba(255,255,255,0.92)', fontSize: 15, marginTop: 6 }}>
              {session?.focus || '회복도 훈련의 일부예요.'}</Text>
          </Hero>
          <Tomorrow tomorrow={tomorrow} />
          <CTA variant="gray" onPress={goWeek}>주간 계획 보기</CTA>
        </>
      )}

      {(state === 'REVIEWED' || state === 'POST_WORKOUT' || state === 'WEEK_END') && state !== 'REST_DAY' && (
        <>
          <Hero color={w?.color || C.tint}>
            <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600', opacity: 0.95 }}>✓ 오늘 완료 · {w?.label}</Text>
            <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8, marginTop: 14 }}>
              <Text style={{ color: '#fff', fontSize: 50, fontWeight: '700', letterSpacing: -1.5 }}>
                {(log?.distance_km ?? 0).toFixed(2)}</Text>
              <Text style={{ color: 'rgba(255,255,255,0.92)', fontSize: 20, fontWeight: '600' }}>km</Text>
            </View>
            {log?.avg_pace && <Text style={{ color: 'rgba(255,255,255,0.92)', fontSize: 15, marginTop: 6 }}>
              {log.avg_pace} /km</Text>}
          </Hero>
          {log?.review ? (
            <Card style={{ backgroundColor: `${w?.color || C.tint}14` }}>
              <Text style={{ color: w?.color, fontSize: 13, fontWeight: '700', marginBottom: 6 }}>코치 분석</Text>
              <Text style={{ color: C.label, fontSize: 15, lineHeight: 23 }}>{log.review.coach_comment}</Text>
              <View style={{ marginTop: 12 }}><RecoveryBadge level={log.review.recovery} /></View>
            </Card>
          ) : (
            <Banner tone="info">기록은 저장됐어요 — 기록 입력에서 AI 리뷰를 받아보세요.</Banner>
          )}
          <Tomorrow tomorrow={tomorrow} />
        </>
      )}

      {state === 'PRE_WORKOUT' && (
        <>
          <Hero color={w.color}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600', opacity: 0.92 }}>
                오늘 · {data.weekday}요일</Text>
              <Text style={{ fontSize: 22 }}>{w.emoji}</Text>
            </View>
            <Text style={{ color: '#fff', fontSize: 32, fontWeight: '700', letterSpacing: -0.8, marginTop: 12 }}>
              {session.title || w.label}</Text>
            <View style={{ flexDirection: 'row', gap: 22, marginTop: 18 }}>
              {session.duration_min > 0 && <View>
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12, fontWeight: '600' }}>예상 시간</Text>
                <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 3 }}>{session.duration_min}분</Text></View>}
              {session.distance_km > 0 && <View>
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12, fontWeight: '600' }}>목표 거리</Text>
                <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 3 }}>{session.distance_km}km</Text></View>}
              {session.target_pace && <View>
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12, fontWeight: '600' }}>목표 페이스</Text>
                <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 3 }}>
                  {session.target_pace.split('~')[0].trim()}</Text></View>}
            </View>
          </Hero>
          {session.focus && (
            <Card>
              <Text style={{ color: C.label2, fontSize: 14.5, lineHeight: 21 }}>{session.focus}</Text>
            </Card>
          )}
          <View style={{ gap: 10 }}>
            <CTA onPress={onRecord}>다녀왔어요 · 기록 입력</CTA>
            <CTA variant="gray" onPress={goWeek}>계획 조정이 필요해요</CTA>
          </View>
        </>
      )}

      {wp && wp.total > 0 && state !== 'NO_PLAN' && (
        <Card>
          <View style={{ flexDirection: 'row' }}>
            <Metric value={`${wp.week_km}`} unit="km" label="이번 주" size={22} />
            <Metric value={`${wp.done}/${wp.total}`} label="완료 세션" size={22} />
            <Metric value={`${wp.completion_rate}%`} label="수행률" size={22} />
          </View>
        </Card>
      )}
    </ScrollView>
  );
}
