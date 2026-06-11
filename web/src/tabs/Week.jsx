// 이번 주 탭 — 진행률 + 세션 리스트 + 계획 생성/조정/성장 리포트
import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { localISO, sessionSubtitle, wmeta } from '../workouts.js';
import {
  Banner, Card, CTA, Icon, MetricRow, Modal, NavBarLarge, Ring, SectionLabel, Spinner,
} from '../components/Ui.jsx';
import Markdown from '../components/Markdown.jsx';

const STATUS_META = {
  done:    { icon: 'CircleCheck', color: 'var(--accent-green)', label: '완료' },
  partial: { icon: 'CircleAlert', color: 'var(--accent-orange)', label: '부분완료' },
  missed:  { icon: 'CircleX', color: 'var(--accent-red)', label: '미수행' },
  planned: { icon: 'Circle', color: 'var(--label-tertiary)', label: '예정' },
};

function SessionRow({ s, isToday }) {
  const w = wmeta(s.kind);
  const st = STATUS_META[s.status] || STATUS_META.planned;
  const past = s.status === 'planned' && s.session_date < localISO();
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px',
      background: isToday ? 'color-mix(in srgb, var(--tint) 7%, transparent)' : 'none' }}>
      <div style={{ width: 34, textAlign: 'center', flex: 'none' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--label-tertiary)' }}>{s.weekday}</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: isToday ? 'var(--tint)' : 'var(--label-primary)' }}>
          {parseInt(s.session_date.slice(8), 10)}</div>
      </div>
      <span style={{ width: 36, height: 36, borderRadius: 11, background: w.color, display: 'grid',
        placeItems: 'center', flex: 'none', opacity: past ? 0.45 : 1 }}>
        <Icon name={w.icon} size={18} color="#fff" strokeWidth={2.1} /></span>
      <div style={{ flex: 1, minWidth: 0, opacity: past ? 0.55 : 1 }}>
        <div style={{ fontSize: 15.5, fontWeight: 600, color: 'var(--label-primary)', whiteSpace: 'nowrap',
          overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title || w.label}</div>
        <div style={{ fontSize: 13, color: 'var(--label-secondary)', marginTop: 1 }}>{sessionSubtitle(s)}</div>
      </div>
      <Icon name={st.icon} size={20} color={st.color} style={{ flex: 'none' }} />
    </div>
  );
}

function NoPlanCard({ onPlan }) {
  return (
    <Card pad={18}>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
        이번 주 계획 만들기</div>
      <div style={{ fontSize: 14, color: 'var(--label-secondary)', marginBottom: 14, lineHeight: 1.45 }}>
        기본 훈련 시간표와 이번 주 특이 일정을 검토해 AI 코치가 7일을 설계해요.</div>
      <CTA icon="Sparkles" onClick={onPlan}>계획 만들기 시작</CTA>
    </Card>
  );
}

function AdjustSheet({ onClose, onDone }) {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const chips = ['피로 누적', '무릎 통증', '발목 통증', '일정 변경', '감기 기운'];
  return (
    <Modal title="계획 조정" subtitle="남은 세션만 보수적으로 조정해요. 이미 한 훈련은 바뀌지 않아요."
      locked={busy} onClose={onClose}>
      <div style={{ padding: '16px 20px 24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {chips.map((c) => (
            <button key={c} onClick={() => setReason(c)}
              style={{ padding: '7px 13px', borderRadius: 999, border: 'none', cursor: 'pointer', fontSize: 14,
                fontWeight: 600, background: reason === c ? 'var(--tint)' : 'var(--fill-tertiary)',
                color: reason === c ? '#fff' : 'var(--label-secondary)' }}>{c}</button>
          ))}
        </div>
        <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '10px 13px', marginBottom: 14 }}>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2}
            placeholder="상황을 적어주세요 (예: 무릎 통증 3/10, 내일 출장)"
            style={{ border: 'none', outline: 'none', background: 'none', width: '100%', resize: 'none',
              fontSize: 15, color: 'var(--label-primary)' }} />
        </div>
        {error && <div style={{ marginBottom: 12 }}><Banner tone="error">{error}</Banner></div>}
        <CTA busy={busy} disabled={!reason.trim()} onClick={async () => {
          setBusy(true); setError(null);
          try { const r = await api.adjustWeek(reason); onDone(r); }
          catch (e) { setError(e.message); setBusy(false); }
        }}>조정 받기</CTA>
      </div>
    </Modal>
  );
}

// 성장 리포트 — 합의 포맷: 카드 3숫자 + 코치 메시지 + 접힌 상세 (F08)
function GrowthReport({ ev }) {
  const [open, setOpen] = useState(false);
  return (
    <Card pad={0} style={{ background: 'rgba(97,85,245,0.08)', boxShadow: 'none' }}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 13 }}>
          <Icon name="Sparkles" size={17} color="var(--accent-indigo)" />
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-indigo)' }}>성장 리포트</span>
          {ev.is_partial && <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--accent-indigo)',
            background: 'rgba(97,85,245,0.14)', borderRadius: 999, padding: '2px 8px' }}>주중 중간</span>}
        </div>
        <MetricRow size={24} items={[
          { value: ev.total_km, unit: 'km', label: '주간 거리' },
          { value: `${ev.done_sessions}/${ev.total_sessions}`, label: '세션' },
          { value: `${ev.completion_rate}%`, label: '수행률' },
        ]} />
        {ev.coach_message && (
          <div style={{ fontSize: 14.5, lineHeight: 1.55, color: 'var(--label-primary)', marginTop: 14,
            paddingTop: 13, borderTop: '0.5px solid var(--separator-non-opaque)' }}>{ev.coach_message}</div>
        )}
      </div>
      {ev.detail_md && (
        <>
          <button onClick={() => setOpen(!open)}
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '11px 16px', border: 'none', cursor: 'pointer', background: 'rgba(97,85,245,0.07)',
              color: 'var(--accent-indigo)', fontSize: 13.5, fontWeight: 700 }}>
            <Icon name={open ? 'ChevronUp' : 'ChevronDown'} size={15} strokeWidth={2.6} />
            상세 분석 {open ? '접기' : '보기'}
          </button>
          {open && <div className="anim-in" style={{ padding: '4px 16px 16px' }}>
            <Markdown text={ev.detail_md} /></div>}
        </>
      )}
    </Card>
  );
}

export default function Week({ refreshToday, onPlan }) {
  const [week, setWeek] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noPlan, setNoPlan] = useState(false);
  const [error, setError] = useState(null);
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjustNote, setAdjustNote] = useState(null);
  const [evalBusy, setEvalBusy] = useState(false);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.currentWeek();
      setWeek(data); setNoPlan(false);
    } catch (e) {
      if (e.status === 404) setNoPlan(true);
      else setError(e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const reload = () => { load(); refreshToday?.(); };

  if (loading) return <div><NavBarLarge title="이번 주" /><Spinner label="불러오는 중…" /></div>;

  const todayStr = localISO();
  const wp = week?.progress;

  return (
    <div className="anim-in">
      <NavBarLarge title="이번 주" trailing={week &&
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)' }}>{week.iso_week}</span>} />
      <div style={{ padding: '4px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {error && <Banner tone="error" action="재시도" onAction={load}>{error}</Banner>}
        {noPlan && <NoPlanCard onPlan={onPlan} />}

        {week && (
          <>
            {week.direction && (
              <Card pad={16} style={{ background: 'color-mix(in srgb, var(--tint) 8%, var(--bg-grouped-secondary))', boxShadow: 'none' }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <Icon name="Compass" size={18} color="var(--tint)" style={{ flex: 'none', marginTop: 2 }} />
                  <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.45 }}>{week.direction}</div>
                </div>
              </Card>
            )}

            <Card pad={18}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
                <Ring pct={wp.completion_rate} size={74} stroke={8}>
                  <span style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 800 }}>{wp.completion_rate}%</span>
                </Ring>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
                    <span style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, letterSpacing: '-0.8px' }}>
                      {wp.week_km}</span>
                    <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--label-secondary)' }}>
                      / {wp.goal_km ?? '—'} km</span>
                  </div>
                  <div style={{ fontSize: 13.5, color: 'var(--label-secondary)', marginTop: 4 }}>
                    완료 {wp.done}/{wp.total} 세션</div>
                </div>
              </div>
            </Card>

            {adjustNote && <Banner tone="info">{adjustNote}</Banner>}

            <div>
              <SectionLabel>일정</SectionLabel>
              <Card pad={0}>
                {week.sessions.map((s, i) => (
                  <div key={s.id} style={{ borderBottom: i < week.sessions.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                    <SessionRow s={s} isToday={s.session_date === todayStr} />
                  </div>
                ))}
              </Card>
            </div>

            {week.evaluation?.coach_message && <GrowthReport ev={week.evaluation} />}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 8 }}>
              <CTA variant="tinted" icon="Sparkles" busy={evalBusy} onClick={async () => {
                setEvalBusy(true);
                try { const r = await api.evaluateWeek(); setWeek(r); }
                catch (e) { setError(e.message); }
                finally { setEvalBusy(false); }
              }}>성장 리포트 만들기</CTA>
              <CTA variant="gray" icon={null} onClick={() => setShowAdjust(true)}>계획 조정이 필요해요</CTA>
            </div>
          </>
        )}
      </div>

      {showAdjust && (
        <AdjustSheet onClose={() => setShowAdjust(false)}
          onDone={(r) => {
            setShowAdjust(false);
            setWeek(r);
            const n = r.adjustment?.changed?.length || 0;
            setAdjustNote(n ? `${n}개 세션이 조정됐어요 — ${r.adjustment.reason}`
              : `조정 불필요 — ${r.adjustment?.reason || '현재 계획 유지를 권장해요.'}`);
            refreshToday?.();
          }} />
      )}
    </div>
  );
}
