// 홈 탭(대시보드) — 희망 목표 vs 현재 기록 기준 추정 예상 기록, 주별 궤적, 준비도, 오늘 요약, 주간 거리, 최근 훈련
// 숫자는 전부 GET /api/dashboard 가 결정적으로 계산한다(AI 미개입) — 이 파일은 표시만 한다.
import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { DataState, ChangeInsights, GrowthHistory, fulfillmentLabel } from '../components/JourneyPanels.jsx';
import { fmtDelta, fmtDuration, fmtHM, fmtHMS, sessionSubtitle, wmeta } from '../workouts.js';
import {
  Banner, Card, CTA, Expander, Icon, NavBarLarge, RecoveryBadge, SectionLabel, Spinner,
} from '../components/Ui.jsx';

const RED = 'var(--accent-red)', GREEN = 'var(--accent-green)', ORANGE = 'var(--accent-orange)';

// 'YYYY-MM-DD' → "11월 1일"
const mdLabel = (iso) => { const [, m, d] = iso.split('-').map(Number); return `${m}월 ${d}일`; };

// ── 목표 격차 카드 ────────────────────────────────────────────────────────

function GoalGapCard({ dash, goSettings }) {
  const { goal, current: cur, message } = dash;
  if (!goal) {
    return (
      <Card pad={18}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ width: 44, height: 44, borderRadius: 14, background: 'var(--fill-tertiary)', display: 'grid',
            placeItems: 'center', flex: 'none' }}><Icon name="Target" size={22} color="var(--label-secondary)" /></span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--label-primary)' }}>목표가 아직 없어요</div>
            <div style={{ fontSize: 13.5, color: 'var(--label-secondary)', marginTop: 2 }}>{message}</div>
          </div>
        </div>
        <div style={{ marginTop: 14 }}><CTA variant="tinted" icon="Flag" onClick={goSettings}>목표 설정하기</CTA></div>
      </Card>
    );
  }

  const pred = cur.predicted_sec;
  const behind = cur.gap_sec != null && cur.gap_sec > 0;
  const predColor = pred == null ? 'var(--label-tertiary)' : !cur.data_status.sufficient ? 'var(--label-primary)' : (behind ? RED : GREEN);
  const delta = cur.delta_assessment_sec;
  const trend = delta == null ? null
    : delta > 0 ? { icon: 'TrendingDown', color: RED, text: `이전 평가보다 환산값 ${fmtDelta(delta)} 증가` }
    : delta < 0 ? { icon: 'TrendingUp', color: GREEN, text: `이전 평가보다 환산값 ${fmtDelta(delta)} 감소` }
    : { icon: 'Minus', color: 'var(--label-tertiary)', text: '이전 평가와 변화 없음' };
  const vsReq = null;
  const track = vsReq == null ? null
    : vsReq > 60 ? { color: ORANGE, text: `궤적보다 ${fmtDelta(vsReq)} 뒤처짐` }
    : vsReq < -60 ? { color: GREEN, text: `궤적보다 ${fmtDelta(vsReq)} 앞섬` }
    : { color: 'var(--label-secondary)', text: '목표까지 필요한 변화선 위에 있어요' };

  return (
    <Card pad={18}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, fontWeight: 600,
        color: 'var(--label-secondary)' }}>
        <Icon name="Flag" size={14} color="var(--tint)" strokeWidth={2.4} />
        <span>{goal.race_type}{goal.target_date ? ` · ${mdLabel(goal.target_date)}` : ''}</span>
        {goal.dday != null && <span style={{ marginLeft: 'auto', color: 'var(--tint)', fontWeight: 700 }}>D-{goal.dday}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 18, marginTop: 14 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--label-tertiary)', letterSpacing: '0.4px',
            textTransform: 'uppercase' }}>희망 목표</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, letterSpacing: '-0.8px',
            lineHeight: 1.05, marginTop: 4, color: 'var(--label-primary)', fontVariantNumeric: 'tabular-nums' }}>
            {fmtHMS(goal.target_sec) || '미정'}</div>
        </div>
        <Icon name="ChevronRight" size={18} color="var(--label-tertiary)" style={{ marginBottom: 8 }} />
        <div style={{ flex: 1.15 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--label-tertiary)', letterSpacing: '0.4px',
            textTransform: 'uppercase' }}>현재 기록 기준 추정</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, letterSpacing: '-0.8px',
            lineHeight: 1.05, marginTop: 4, color: predColor, fontVariantNumeric: 'tabular-nums' }}>
            {fmtHMS(pred) || '—'}</div>
        </div>
      </div>

      {pred != null && cur.gap_sec != null && (
        <div style={{ marginTop: 14, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px',
          borderRadius: 999, fontSize: 13.5, fontWeight: 700,
          background: `color-mix(in srgb, ${predColor} 14%, transparent)`, color: predColor }}>
          <Icon name={behind ? 'Timer' : 'CircleCheck'} size={14} strokeWidth={2.4} />
          {behind ? `목표와의 환산 차이 +${fmtDelta(cur.gap_sec)}` : '현재 환산값이 목표 기록 이내예요'}
        </div>
      )}

      {(trend || track) && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '0.5px solid var(--separator-non-opaque)',
          display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13.5 }}>
          {trend && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: trend.color, fontWeight: 600 }}>
              <Icon name={trend.icon} size={15} strokeWidth={2.4} />{trend.text}</div>
          )}
          {track && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: track.color, fontWeight: 600 }}>
              <Icon name="Gauge" size={15} strokeWidth={2.4} />{track.text}</div>
          )}
        </div>
      )}
      {message && <div style={{ marginTop: 12 }}><Banner tone="info">{message}</Banner></div>}
    </Card>
  );
}

// ── 궤적 그래프 (SVG, 라이브러리 없음) — 위로 갈수록 빠른 기록 ───────────

function TrajectoryChart({ series, targetSec }) {
  const pts = series.filter((s) => s.predicted_sec != null);
  if (pts.length < 2) {
    return (
      <Card pad={20} style={{ textAlign: 'center' }}>
        <Icon name="TrendingUp" size={26} color="var(--label-tertiary)" />
        <div style={{ fontSize: 14, color: 'var(--label-secondary)', marginTop: 8 }}>
          서로 다른 주에 근거가 충분한 평가가 저장되면 성장선이 그려져요.</div>
      </Card>
    );
  }
  const W = 340, H = 168, L = 46, R = 14, T = 16, B = 26;
  const plotW = W - L - R, plotH = H - T - B;
  const vals = series.flatMap((s) => [s.predicted_sec, s.required_sec]).filter((v) => v != null);
  if (targetSec) vals.push(targetSec);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = Math.max((hi - lo) * 0.08, 120);
  lo -= pad; hi += pad;
  const x = (i) => L + (i / (series.length - 1)) * plotW;
  const y = (sec) => T + ((sec - lo) / (hi - lo)) * plotH; // 작은(빠른) 값이 위
  const path = (key) => series.map((s, i) => (s[key] == null ? null : `${x(i).toFixed(1)},${y(s[key]).toFixed(1)}`))
    .reduce((acc, p) => (p == null ? acc : acc + (acc ? ' L' : 'M') + p), '');
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad];
  const last = series.length - 1;

  return (
    <Card pad={14}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', overflow: 'visible' }}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--separator-non-opaque)" strokeWidth="0.6" />
            <text x={L - 6} y={y(t) + 3.5} textAnchor="end" fontSize="10" fill="var(--label-tertiary)"
              fontFamily="var(--font-display)" fontWeight="600">{fmtHM(t)}</text>
          </g>
        ))}
        {targetSec && (
          <g>
            <line x1={L} x2={W - R} y1={y(targetSec)} y2={y(targetSec)} stroke={GREEN} strokeWidth="1.2"
              strokeDasharray="3 3" />
            <text x={W - R} y={y(targetSec) - 4} textAnchor="end" fontSize="10" fill={GREEN} fontWeight="700">
              목표 {fmtHM(targetSec)}</text>
          </g>
        )}
        {path('required_sec') && (
          <path d={path('required_sec')} fill="none" stroke="var(--label-tertiary)" strokeWidth="1.4"
            strokeDasharray="5 4" strokeLinecap="round" />
        )}
        <path d={path('predicted_sec')} fill="none" stroke="var(--tint)" strokeWidth="2.4" strokeLinecap="round"
          strokeLinejoin="round" />
        {series.map((s, i) => s.predicted_sec == null ? null : (
          <circle key={i} cx={x(i)} cy={y(s.predicted_sec)} r={i === last ? 5 : 2.6} fill={i === last ? 'var(--tint)' : 'var(--bg-grouped-secondary)'}
            stroke="var(--tint)" strokeWidth={i === last ? 2.5 : 1.6} />
        ))}
        {series.map((s, i) => (i === last || (last - i) % 3 === 0) && (
          <text key={`x${i}`} x={x(i)} y={H - 8} textAnchor={i === last ? 'end' : 'middle'} fontSize="10"
            fill={i === last ? 'var(--label-primary)' : 'var(--label-tertiary)'} fontWeight={i === last ? 700 : 500}>
            {i === last ? '이번 주' : `W${s.iso_week.split('W')[1]}`}</text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 14, justifyContent: 'center', marginTop: 8, fontSize: 11.5,
        color: 'var(--label-secondary)', fontWeight: 600 }}>
        <span><span style={{ display: 'inline-block', width: 14, height: 2.4, background: 'var(--tint)', borderRadius: 2,
          verticalAlign: 'middle', marginRight: 5 }} />현재 기록 기준 추정</span>
        <span><span style={{ display: 'inline-block', width: 14, borderTop: '2px dashed var(--label-tertiary)',
          verticalAlign: 'middle', marginRight: 5 }} />목표까지 필요한 변화선</span>
        <span><span style={{ display: 'inline-block', width: 14, borderTop: `2px dashed ${GREEN}`,
          verticalAlign: 'middle', marginRight: 5 }} />목표</span>
      </div>
    </Card>
  );
}

// ── 준비도 3축 ───────────────────────────────────────────────────────────

function ReadinessBars({ readiness }) {
  const rows = [
    { k: '스피드', v: readiness.speed, c: ORANGE, hint: '최근 최고 수행의 순수 환산이 목표 대비 얼마나 빠른가' },
    { k: '지구력', v: readiness.endurance, c: 'var(--accent-indigo)', hint: '4주 평균 거리·최장 롱런이 요구치 대비 얼마나 되나' },
    { k: '꾸준함', v: readiness.consistency, c: GREEN, hint: '4주 계획 이행률' },
  ];
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {rows.map((r) => (
          <div key={r.k}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 5 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--label-primary)' }}>{r.k}</span>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 700,
                color: r.v == null ? 'var(--label-tertiary)' : r.c }}>{r.v == null ? '기록 필요' : r.v}</span>
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'var(--fill-tertiary)', overflow: 'hidden' }}>
              <div style={{ width: `${r.v ?? 0}%`, height: '100%', borderRadius: 999, background: r.c,
                transition: 'width .5s cubic-bezier(.32,.72,0,1)' }} />
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--label-tertiary)', marginTop: 4 }}>{r.hint}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── 근거 보기 ────────────────────────────────────────────────────────────

function Row({ label, children }) {
  return (
    <div style={{ display: 'flex', gap: 10, padding: '4px 0', fontSize: 13.5, alignItems: 'baseline' }}>
      <span style={{ width: 88, flex: 'none', color: 'var(--label-tertiary)', fontWeight: 600 }}>{label}</span>
      <span style={{ flex: 1, color: 'var(--label-primary)', lineHeight: 1.45 }}>{children}</span>
    </div>
  );
}

function BasisDetail({ dash }) {
  const { basis: b } = dash.current;
  const ref = b.reference;
  const refText = !ref ? '없음'
    : ref.source === 'pb' ? `프로필 PB ${ref.distance_km}km ${ref.time} (+5% 페널티 · 10K 환산 스피드로만 사용)`
    : `${mdLabel(ref.date)} ${wmeta(ref.kind).label} ${ref.distance_km}km ${ref.time} (${ref.pace}/km)`;
  const c = b.completion_4wk;
  return (
    <Expander title="근거 보기" icon="Info" iconColor="var(--gray)">
      <Row label="기준 기록">{refText}</Row>
      {ref && <Row label="순수 환산">{fmtHMS(ref.equiv_pure_sec)} <span style={{ color: 'var(--label-tertiary)' }}>
        (지구력 완비 가정)</span></Row>}
      <Row label="4주 평균">{b.vol_4wk_km}km/주 <span style={{ color: 'var(--label-tertiary)' }}>· 요구 {b.req_vol_km}km</span></Row>
      <Row label="최장 롱런">{b.long_run_km}km <span style={{ color: 'var(--label-tertiary)' }}>· 요구 {b.req_long_km}km</span></Row>
      <Row label="4주 계획 이행">{c ? `${c.done}/${c.total} 세션` : '계획 없음'}</Row>
      {b.exponent != null && <Row label="환산 지수">{b.exponent} <span style={{ color: 'var(--label-tertiary)' }}>
        (완비 1.06 · 지구력 0이면 1.31)</span></Row>}
      <div style={{ marginTop: 8, padding: '9px 11px', borderRadius: 10, background: 'var(--fill-tertiary)',
        fontSize: 12.5, color: 'var(--label-secondary)', lineHeight: 1.5 }}>
        예상 기록 = 기준 기록 × (목표 거리 ÷ 기준 거리)<sup>지수</sup>, 지수 = 1.06 + (1 − 지구력) × 0.25.
        스피드 기준점은 최근 {b.speed_window_days}일 중 가장 빠른 예측을 내는 수행(프로필 PB 포함),
        지구력은 최근 {b.volume_window_days}일 거리와 롱런으로 계산해요.
      </div>
    </Expander>
  );
}

// ── 오늘 한 줄 ───────────────────────────────────────────────────────────

function TodayGlance({ today, goToday, onPlan }) {
  if (!today) return null;
  if (today.state === 'NO_PLAN') {
    return (
      <Card pad={16}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--label-primary)' }}>이번 주 계획이 아직 없어요</div>
        <div style={{ fontSize: 13.5, color: 'var(--label-secondary)', marginTop: 3 }}>
          기본 시간표와 이번 주 특이 일정으로 7일 훈련을 구성해요.</div>
        <div style={{ marginTop: 12 }}><CTA variant="tinted" onClick={onPlan}>이번 주 계획 세우기</CTA></div>
      </Card>
    );
  }
  const s = today.session;
  const w = wmeta(s?.kind || 'rest');
  const status = today.state === 'REVIEWED' || today.state === 'POST_WORKOUT' ? { t: fulfillmentLabel(s?.status), c: s?.status === 'done' ? GREEN : ORANGE }
    : today.state === 'WEEK_END' ? { t: '주간 종료', c: 'var(--accent-indigo)' }
    : s?.is_rest || today.state === 'REST_DAY' ? { t: '휴식', c: 'var(--label-tertiary)' }
    : { t: '예정', c: 'var(--tint)' };
  const title = today.state === 'REST_DAY' && !s ? '오늘은 쉬는 날' : (s?.title || w.label);
  const sub = today.log ? `${today.day_km ?? today.log.distance_km ?? 0}km${today.log.avg_pace ? ` · ${today.log.avg_pace}/km` : ''} 기록됨`
    : sessionSubtitle(s);
  return (
    <Card pad={0} onClick={goToday}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px' }}>
        <span style={{ width: 42, height: 42, borderRadius: 12, background: w.color, display: 'grid',
          placeItems: 'center', flex: 'none' }}><Icon name={w.icon} size={21} color="#fff" strokeWidth={2.1} /></span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15.5, fontWeight: 700, color: 'var(--label-primary)', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</div>
          {sub && <div style={{ fontSize: 13, color: 'var(--label-secondary)', marginTop: 2 }}>{sub}</div>}
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, color: status.c, padding: '4px 9px', borderRadius: 999,
          background: `color-mix(in srgb, ${status.c} 14%, transparent)`, flex: 'none' }}>{status.t}</span>
        <Icon name="ChevronRight" size={17} color="var(--label-tertiary)" style={{ flex: 'none' }} />
      </div>
    </Card>
  );
}

// ── 주간 거리 추세 (오래된 주 → 이번 주) ─────────────────────────────────

function WeekTrend({ weeks }) {
  const max = Math.max(...weeks.map((w) => w.week_km), 1);
  return (
    <Card pad={18}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120 }}>
        {weeks.map((w) => {
          const h = w.week_km === 0 ? 4 : Math.max(10, (w.week_km / max) * 100);
          return (
            <div key={w.iso_week} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: w.current ? 'var(--tint)' : 'var(--label-secondary)' }}>
                {w.week_km > 0 ? w.week_km : ''}</span>
              <div style={{ width: '100%', maxWidth: 30, height: h, borderRadius: 8,
                background: w.current ? 'var(--tint)' : 'color-mix(in srgb, var(--tint) 28%, transparent)',
                transition: 'height .4s cubic-bezier(.32,.72,0,1)' }} />
              <span style={{ fontSize: 10.5, fontWeight: w.current ? 700 : 500,
                color: w.current ? 'var(--label-primary)' : 'var(--label-tertiary)' }}>
                {w.current ? '이번 주' : `W${w.iso_week.split('W')[1]}`}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ── 최근 훈련 한 줄 (펼치면 상세 + 코치 코멘트) ─────────────────────────

function RunRow({ log }) {
  const w = wmeta(log.kind);
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%',
        padding: '13px 16px', border: 'none', background: 'none', cursor: 'pointer', textAlign: 'left' }}>
        <span style={{ width: 38, height: 38, borderRadius: 11, background: w.color, display: 'grid',
          placeItems: 'center', flex: 'none' }}><Icon name={w.icon} size={19} color="#fff" strokeWidth={2.1} /></span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15.5, fontWeight: 600, color: 'var(--label-primary)' }}>
            {log.distance_km > 0 ? `${log.distance_km}km` : w.label}
            {log.avg_pace && <span style={{ color: 'var(--label-secondary)', fontWeight: 500 }}> · {log.avg_pace}/km</span>}
          </div>
          <div style={{ fontSize: 13, color: 'var(--label-secondary)', marginTop: 1 }}>
            {log.log_date.slice(5).replace('-', '/')} · {w.label}
            {log.source === 'strava' && <span style={{ color: '#FC4C02', fontWeight: 700 }}> · Strava</span>}
          </div>
        </div>
        {log.review && <RecoveryBadge level={log.review.recovery} />}
        <Icon name={open ? 'ChevronUp' : 'ChevronDown'} size={16} color="var(--label-tertiary)" style={{ flex: 'none' }} />
      </button>
      {open && (
        <div className="anim-in" style={{ padding: '0 16px 14px 66px' }}>
          <div style={{ fontSize: 13.5, color: 'var(--label-secondary)', lineHeight: 1.6 }}>
            {log.duration_sec && <div>시간 {fmtDuration(log.duration_sec)}</div>}
            {log.avg_hr && <div>평균 심박 {log.avg_hr} bpm{log.cadence ? ` · 케이던스 ${log.cadence} spm` : ''}</div>}
            {log.pain_part && <div style={{ color: RED }}>통증 {log.pain_part} {log.pain_level}/10</div>}
            {log.user_comment && <div style={{ marginTop: 4 }}>"{log.user_comment}"</div>}
            {log.review?.coach_comment && (
              <div style={{ marginTop: 8, padding: '10px 12px', borderRadius: 12, background: 'var(--fill-tertiary)',
                color: 'var(--label-primary)' }}>
                <span style={{ fontWeight: 700, fontSize: 12.5, color: 'var(--tint)' }}>코치</span><br />
                {log.review.coach_comment}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 탭 본체 ──────────────────────────────────────────────────────────────

export default function Home({ dash, dashError, loading, refresh, today, reloadKey, goToday, onPlan, goSettings, onAddRun, onEdit }) {
  const [logs, setLogs] = useState(null);
  const [logsError, setLogsError] = useState(null);

  useEffect(() => {
    let alive = true;
    setLogsError(null);
    api.logs(20).then((r) => alive && setLogs(r.items)).catch((e) => alive && setLogsError(e.message));
    return () => { alive = false; };
  }, [reloadKey]);

  const nav = <NavBarLarge title="홈" />;  // D-day 는 목표 카드에 있어 중복 표기하지 않는다

  if (loading && !dash) return <div>{nav}<Spinner label="불러오는 중…" /></div>;
  if (!dash) return (
    <div>{nav}<div style={{ padding: '8px 16px' }}>
      <Banner tone="error" action="재시도" onAction={refresh}>{dashError || '대시보드를 불러오지 못했어요.'}</Banner></div></div>
  );

  const weeks = dash.series.slice(-8);
  return (
    <div className="anim-in">
      {nav}
      <div style={{ padding: '4px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <DataState dash={dash} reloadKey={reloadKey} onImport={onAddRun} goSettings={goSettings} />
        <GoalGapCard dash={dash} goSettings={goSettings} />

        <ChangeInsights dash={dash} refresh={refresh} goToday={goToday} />
        <GrowthHistory onEdit={onEdit} reloadKey={reloadKey} />
        {dash.goal && (
          <div>
            <SectionLabel trailing={<span style={{ fontSize: 12, color: 'var(--label-tertiary)', fontWeight: 600 }}>
              최근 12주 · 위로 갈수록 빠름</span>}>저장된 당시 평가</SectionLabel>
            <TrajectoryChart series={dash.series} targetSec={dash.goal.target_sec} />
            <p style={{ fontSize: 12, color: 'var(--label-secondary)' }}>{dash.history_note}</p>
            <Expander title="현재 데이터로 재계산 · 소급 추정" icon="History">
              <p>당시 평가는 위 그래프에 보존됩니다. 아래 값은 정정된 현재 입력으로 다시 계산한 소급 추정입니다.</p>
              {dash.recalculated_series?.filter((p) => p.predicted_sec != null).map((p) => <p key={p.iso_week}>{p.iso_week} · {fmtHMS(p.predicted_sec)} · 소급 추정</p>)}
            </Expander>
          </div>
        )}

        <div>
          <SectionLabel>준비도</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <ReadinessBars readiness={dash.current.readiness} />
            <BasisDetail dash={dash} />
          </div>
        </div>

        <div>
          <SectionLabel>오늘</SectionLabel>
          <TodayGlance today={today} goToday={goToday} onPlan={onPlan} />
        </div>

        <div>
          <SectionLabel>주간 거리</SectionLabel>
          <WeekTrend weeks={weeks} />
        </div>

        <div>
          {/* 계획 세션 행에서만 기록할 수 있어 계획 밖 러닝은 들어갈 길이 없었다 — 여기서 그 길을 연다 (AddRunSheet) */}
          <SectionLabel trailing={
            <button onClick={onAddRun} aria-label="계획에 없던 훈련 추가"
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 11px 6px 8px', borderRadius: 999,
                border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
                background: 'color-mix(in srgb, var(--tint) 14%, transparent)', color: 'var(--tint)' }}>
              <Icon name="Plus" size={14} strokeWidth={2.6} />추가</button>
          }>최근 훈련</SectionLabel>
          {logsError ? <Banner tone="error">{logsError}</Banner>
            : logs === null ? <Card pad={16}><span style={{ fontSize: 14, color: 'var(--label-secondary)' }}>불러오는 중…</span></Card>
            : logs.length === 0 ? (
              <Card pad={24} style={{ textAlign: 'center' }}>
                <Icon name="Footprints" size={28} color="var(--label-tertiary)" />
                <div style={{ fontSize: 15, color: 'var(--label-secondary)', marginTop: 10 }}>
                  아직 기록이 없어요. 오늘 탭에서 첫 훈련을 기록해 보세요.</div>
              </Card>
            ) : (
              <Card pad={0}>
                {logs.map((log, i) => (
                  <div key={log.id} style={{ borderBottom: i < logs.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                    <RunRow log={log} />
                    {log.quality?.reason && <Banner tone="warn">추정 제외: {log.quality.reason}</Banner>}
                    {log.review?.is_stale && <Banner tone="warn">기록 수정 후 리뷰 갱신 필요</Banner>}
                    <CTA variant="ghost" onClick={() => onEdit(log)}>이 기록 수정</CTA>
                  </div>
                ))}
              </Card>
            )}
        </div>
      </div>
    </div>
  );
}
