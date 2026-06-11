// 기록 탭 — 주별 추세 + 최근 러닝 리스트
import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtDuration, wmeta } from '../workouts.js';
import {
  Banner, Card, Icon, NavBarLarge, RecoveryBadge, SectionLabel, Spinner,
} from '../components/Ui.jsx';

function WeekTrend({ weeks }) {
  const max = Math.max(...weeks.map((w) => w.week_km), 1);
  return (
    <Card pad={18}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 120 }}>
        {[...weeks].reverse().map((w) => {
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
            {log.pain_part && <div style={{ color: 'var(--accent-red)' }}>통증 {log.pain_part} {log.pain_level}/10</div>}
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

export default function History() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState(null);

  const load = async () => {
    setError(null);
    try {
      const [s, l] = await Promise.all([api.weeklyStats(6), api.logs(30)]);
      setStats(s.weeks); setLogs(l.items);
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  if (error) return <div><NavBarLarge title="기록" />
    <div style={{ padding: '8px 16px' }}><Banner tone="error" action="재시도" onAction={load}>{error}</Banner></div></div>;
  if (!stats || !logs) return <div><NavBarLarge title="기록" /><Spinner label="불러오는 중…" /></div>;

  const totalKm = stats.reduce((a, w) => a + w.week_km, 0);

  return (
    <div className="anim-in">
      <NavBarLarge title="기록" trailing={
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)' }}>최근 6주 {Math.round(totalKm * 10) / 10}km</span>} />
      <div style={{ padding: '4px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <SectionLabel>주간 거리 추세</SectionLabel>
          <WeekTrend weeks={stats} />
        </div>
        <div>
          <SectionLabel>최근 훈련</SectionLabel>
          {logs.length === 0 ? (
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
                </div>
              ))}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
