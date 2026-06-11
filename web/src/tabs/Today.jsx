// 오늘 탭 — 상태머신: NO_PLAN / PRE_WORKOUT / POST_WORKOUT / REVIEWED / REST_DAY / WEEK_END
import React, { useState } from 'react';
import { api } from '../api.js';
import { sessionSubtitle, wmeta } from '../workouts.js';
import {
  Banner, Card, CTA, Expander, Hero, Icon, MetricRow, NavBarLarge,
  RecoveryBadge, SectionLabel, Spinner, WeekBars,
} from '../components/Ui.jsx';
import Markdown from '../components/Markdown.jsx';

function TomorrowCard({ tomorrow }) {
  if (!tomorrow) return null;
  const w = wmeta(tomorrow.kind);
  return (
    <div>
      <SectionLabel>내일 예고</SectionLabel>
      <Card pad={16}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ width: 46, height: 46, borderRadius: 13, background: w.color, display: 'grid',
            placeItems: 'center', flex: 'none' }}>
            <Icon name={w.icon} size={24} color="#fff" strokeWidth={2.1} /></span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--label-primary)' }}>{tomorrow.title || w.label}</div>
            <div style={{ fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>{sessionSubtitle(tomorrow)}</div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// 당일 AI 카드 (워밍업/메인/쿨다운) 또는 생성 CTA
function DailyCard({ data, session, onGenerated }) {
  const w = wmeta(session.kind);
  const [busy, setBusy] = useState(false);
  const [condition, setCondition] = useState('');
  const [error, setError] = useState(null);
  const [openDetail, setOpenDetail] = useState(false);

  if (!data) {
    const chips = ['컨디션 좋아요', '조금 피곤해요', '수면 부족', '약간 통증 있어요'];
    return (
      <Card pad={16}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Icon name="Sparkles" size={16} color={w.color} />
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--label-primary)' }}>오늘 컨디션에 맞게 상세 설계</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {chips.map((c) => (
            <button key={c} onClick={() => setCondition(c)}
              style={{ padding: '7px 13px', borderRadius: 999, border: 'none', cursor: 'pointer', fontSize: 14,
                fontWeight: 600, background: condition === c ? 'var(--tint)' : 'var(--fill-tertiary)',
                color: condition === c ? '#fff' : 'var(--label-secondary)' }}>{c}</button>
          ))}
        </div>
        {error && <div style={{ marginBottom: 10 }}><Banner tone="error">{error}</Banner></div>}
        <CTA variant="tinted" icon="Sparkles" busy={busy} onClick={async () => {
          setBusy(true); setError(null);
          try { await api.generateDaily({ condition_note: condition }); onGenerated(); }
          catch (e) { setError(e.message); }
          finally { setBusy(false); }
        }}>워밍업·메인·쿨다운 카드 만들기</CTA>
      </Card>
    );
  }

  const s = data.sections || {};
  const rows = [
    { k: '워밍업', t: s.warmup, ic: 'Wind', c: 'var(--accent-cyan)' },
    { k: '메인 세트', t: s.main, ic: w.icon, c: w.color },
    { k: '쿨다운', t: s.cooldown, ic: 'Droplet', c: 'var(--accent-blue)' },
  ].filter((r) => r.t);
  return (
    <div>
      <SectionLabel trailing={<span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12,
        color: w.color, fontWeight: 600 }}><Icon name="Sparkles" size={13} color={w.color} /> AI 설계{data.is_adjusted ? ' · 조정됨' : ''}</span>}>
        오늘 훈련 상세</SectionLabel>
      <Card pad={0}>
        {rows.map((r, i) => (
          <div key={i} onClick={s.detail ? () => setOpenDetail(!openDetail) : undefined}
            style={{ display: 'flex', gap: 13, padding: '15px 16px', cursor: s.detail ? 'pointer' : 'default',
              borderBottom: i < rows.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
            <span style={{ width: 30, height: 30, borderRadius: 9, background: r.c, flex: 'none',
              display: 'grid', placeItems: 'center', marginTop: 1 }}>
              <Icon name={r.ic} size={16} color="#fff" strokeWidth={2.2} /></span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-tertiary)', textTransform: 'uppercase',
                letterSpacing: '0.4px' }}>{r.k}</div>
              <div style={{ fontSize: 16, color: 'var(--label-primary)', marginTop: 3, lineHeight: 1.4 }}>{r.t}</div>
            </div>
          </div>
        ))}
        {s.detail && (
          <button onClick={() => setOpenDetail(!openDetail)}
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '11px 16px', border: 'none', cursor: 'pointer', background: `rgba(${w.rgb},0.07)`,
              color: w.color, fontSize: 13.5, fontWeight: 700 }}>
            <Icon name={openDetail ? 'ChevronUp' : 'ChevronDown'} size={15} strokeWidth={2.6} />
            단계별 수행 가이드 {openDetail ? '접기' : '보기'}
          </button>
        )}
        {openDetail && s.detail && (
          <div className="anim-in" style={{ padding: '4px 16px 14px' }}>
            <Markdown text={s.detail} />
          </div>
        )}
        {s.note && (
          <div style={{ display: 'flex', gap: 9, padding: '13px 16px', background: `rgba(${w.rgb},0.07)` }}>
            <Icon name="Info" size={16} color={w.color} style={{ flex: 'none', marginTop: 1 }} />
            <span style={{ fontSize: 14, color: 'var(--label-secondary)', lineHeight: 1.45 }}>{s.note}</span>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function Today({ data, loading, error, refresh, onRecord, goWeek, onPlan }) {
  if (loading) return <div><NavBarLarge title="오늘" /><Spinner label="불러오는 중…" /></div>;
  if (error) return (
    <div><NavBarLarge title="오늘" />
      <div style={{ padding: '8px 16px' }}>
        <Banner tone="error" action="재시도" onAction={refresh}>{error}</Banner></div></div>
  );

  const { state, session, tomorrow, log, daily_plan: daily, week_progress: wp, dday } = data;
  const ddayLabel = dday != null ? `D-${dday}` : null;
  const w = session ? wmeta(session.kind) : null;

  let body;
  if (state === 'NO_PLAN') {
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero flat>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <span style={{ width: 44, height: 44, borderRadius: 14, background: 'var(--fill-tertiary)',
              display: 'grid', placeItems: 'center' }}><Icon name="Calendar" size={24} color="var(--label-secondary)" /></span>
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 27, fontWeight: 700, letterSpacing: '-0.5px',
            lineHeight: 1.18 }}>이번 주 계획이<br />아직 없어요</div>
          <div style={{ fontSize: 15, color: 'var(--label-secondary)', marginTop: 8 }}>
            기본 훈련 시간표와 이번 주 특이 일정을 검토해 7일 훈련을 구성해요.</div>
        </Hero>
        <CTA onClick={onPlan}>이번 주 계획 세우기</CTA>
      </div>
    );
  } else if (state === 'REST_DAY' || (session?.is_rest && state !== 'REVIEWED')) {
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero rgb="142,142,147">
          <Icon name="Bed" size={30} color="#fff" />
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, letterSpacing: '-0.6px',
            marginTop: 14 }}>오늘은 쉬는 날이에요</div>
          <div style={{ fontSize: 15, opacity: 0.92, marginTop: 6 }}>{session?.focus || '회복도 훈련의 일부예요.'}</div>
        </Hero>
        <Card>
          <div style={{ fontSize: 15, color: 'var(--label-secondary)', lineHeight: 1.5 }}>
            잘 자고, 수분을 충분히 채우면 다음 훈련이 한결 가벼워집니다.</div>
        </Card>
        <TomorrowCard tomorrow={tomorrow} />
        <CTA variant="gray" icon={null} onClick={goWeek}>주간 계획 보기</CTA>
      </div>
    );
  } else if (state === 'REVIEWED' || state === 'POST_WORKOUT') {
    const review = log?.review;
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero rgb={w?.rgb || '0,136,255'}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, opacity: 0.95 }}>
              <Icon name="CircleCheck" size={18} color="#fff" strokeWidth={2.3} /> 오늘 완료</span>
            <span style={{ background: 'rgba(255,255,255,0.22)', borderRadius: 999, padding: '4px 10px',
              fontSize: 13, fontWeight: 600 }}>{w?.label}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 16 }}>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: 52, fontWeight: 700,
              letterSpacing: '-1.5px', lineHeight: 0.9 }}>{(log?.distance_km ?? 0).toFixed(2)}</span>
            <span style={{ fontSize: 20, fontWeight: 600, opacity: 0.92 }}>km</span>
          </div>
          {log?.avg_pace && <div style={{ fontSize: 15, opacity: 0.92, marginTop: 6 }}>{log.avg_pace} /km</div>}
        </Hero>
        {(log?.avg_hr || log?.cadence) && (
          <Card><MetricRow size={26} items={[
            log?.avg_pace && { value: log.avg_pace, label: '페이스 /km' },
            log?.avg_hr && { value: log.avg_hr, label: '평균 심박' },
            log?.cadence && { value: log.cadence, label: '케이던스' },
          ].filter(Boolean)} /></Card>
        )}
        {review ? (
          <Card style={{ background: `rgba(${w?.rgb || '0,136,255'},0.07)`, boxShadow: 'none' }} pad={16}>
            <div style={{ display: 'flex', gap: 11 }}>
              <span style={{ width: 30, height: 30, borderRadius: 9, background: w?.color || 'var(--tint)',
                flex: 'none', display: 'grid', placeItems: 'center' }}><Icon name="Sparkles" size={16} color="#fff" /></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: w?.color, marginBottom: 4 }}>코치 분석</div>
                {review.summary && <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--label-primary)',
                  marginBottom: 6 }}>{review.summary}</div>}
                <div style={{ fontSize: 15, lineHeight: 1.5, color: 'var(--label-primary)' }}>{review.coach_comment}</div>
                {review.improvements && <div style={{ marginTop: 8, fontSize: 14, color: 'var(--label-secondary)',
                  whiteSpace: 'pre-line' }}>{review.improvements}</div>}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, paddingTop: 13,
              borderTop: '0.5px solid var(--separator-non-opaque)' }}>
              <RecoveryBadge level={review.recovery} />
            </div>
          </Card>
        ) : (
          <Banner tone="info" action="리뷰 받기" onAction={onRecord}>기록은 저장됐어요 — AI 리뷰를 받아보세요.</Banner>
        )}
        <TomorrowCard tomorrow={tomorrow} />
        <CTA variant="ghost" icon={null} onClick={goWeek}>이번 주 진행 보기</CTA>
      </div>
    );
  } else if (state === 'WEEK_END') {
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero rgb="97,85,245">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon name="Trophy" size={20} color="#fff" />
            <span style={{ fontSize: 14, fontWeight: 600, opacity: 0.95 }}>이번 주 훈련 종료</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 14 }}>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: 56, fontWeight: 700,
              letterSpacing: '-1.5px', lineHeight: 0.9 }}>{wp.week_km}</span>
            <span style={{ fontSize: 20, fontWeight: 600, opacity: 0.92 }}>km</span>
          </div>
          <div style={{ display: 'flex', gap: 26, marginTop: 16 }}>
            <div><div style={{ fontSize: 12, opacity: 0.85, fontWeight: 600 }}>완료 세션</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, marginTop: 2 }}>{wp.done}/{wp.total}</div></div>
            <div><div style={{ fontSize: 12, opacity: 0.85, fontWeight: 600 }}>수행률</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, marginTop: 2 }}>{wp.completion_rate}%</div></div>
          </div>
        </Hero>
        <Card><WeekBars days={wp.days_km} accent="var(--accent-indigo)" /></Card>
        <CTA onClick={goWeek}>이번 주 성장 리포트 만들기</CTA>
      </div>
    );
  } else {
    // PRE_WORKOUT
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero rgb={w.rgb}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 14, fontWeight: 600, opacity: 0.92, letterSpacing: '0.3px' }}>
              오늘 · {data.weekday}요일</span>
            <Icon name={w.icon} size={26} color="#fff" strokeWidth={2.1} />
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 34, fontWeight: 700, letterSpacing: '-0.8px',
            marginTop: 12, lineHeight: 1.08 }}>{session.title || w.label}</div>
          <div style={{ display: 'flex', gap: 22, marginTop: 18 }}>
            {session.duration_min > 0 && <div>
              <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 600, letterSpacing: '0.3px' }}>예상 시간</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>
                {session.duration_min}{session.duration_min_max ? `~${session.duration_min_max}` : ''}분</div></div>}
            {session.distance_km > 0 && <div>
              <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 600, letterSpacing: '0.3px' }}>목표 거리</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>{session.distance_km}km</div></div>}
            {session.target_pace && <div>
              <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 600, letterSpacing: '0.3px' }}>목표 페이스</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>
                {session.target_pace.split('~')[0].trim()}</div></div>}
          </div>
        </Hero>

        <DailyCard data={daily} session={session} onGenerated={refresh} />

        {(session.focus || session.note) && (
          <Expander title="이 세션의 목적" icon="Target" iconColor={w.color}>
            {session.focus && (
              <div style={{ fontSize: 14.5, color: 'var(--label-primary)', fontWeight: 600, lineHeight: 1.5 }}>
                {session.focus}</div>
            )}
            {session.note && (
              <div style={{ fontSize: 14, color: 'var(--label-secondary)', lineHeight: 1.5,
                marginTop: session.focus ? 6 : 0, whiteSpace: 'pre-line' }}>{session.note}</div>
            )}
          </Expander>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 4 }}>
          <CTA onClick={onRecord} icon="Check">다녀왔어요 · 기록 입력</CTA>
          <CTA variant="ghost" icon={null} onClick={goWeek}>계획 조정이 필요해요</CTA>
        </div>
      </div>
    );
  }

  return (
    <div className="anim-in">
      <NavBarLarge title="오늘" trailing={ddayLabel &&
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--tint)' }}>{ddayLabel}</span>} />
      <div style={{ padding: '4px 16px 0' }}>{body}</div>
    </div>
  );
}
