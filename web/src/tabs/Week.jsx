// 이번 주 탭 — 진행률 + 세션 리스트 + 계획 생성/조정/성장 리포트
import React, { useEffect, useState } from 'react';
import { api, genResult } from '../api.js';
import { pendingGen, pollUntil, reconcileOnce } from '../recover.js';
import { fmtDuration, localISO, sessionSubtitle, wmeta } from '../workouts.js';
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

// 기록된 세션의 실측 요약 (거리·페이스). 없으면 '완료'/'직접 기록'.
function loggedSubtitle(s) {
  const parts = [
    s.log.distance_km ? `${s.log.distance_km}km` : null,
    s.log.avg_pace ? `${s.log.avg_pace}/km` : null,
  ].filter(Boolean);
  return `기록됨 · ${parts.join(' · ') || (s.is_rest ? '직접 기록' : '완료')}`;
}

// 계획 소요시간 표기 — "30분" / "30~35분"
function planDuration(s) {
  if (!s.duration_min) return null;
  return `${s.duration_min}${s.duration_min_max ? `~${s.duration_min_max}` : ''}분`;
}

// 'YYYY-MM-DD' + 한글 요일 → "6월 18일 (수)"
function sessionDateLabel(s) {
  const [, m, d] = s.session_date.split('-').map(Number);
  return `${m}월 ${d}일 (${s.weekday})`;
}

// 펼침 내부 한 줄 — 라벨 + 값
function DetailRow({ label, children, strong }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, padding: '3px 0', fontSize: 13.5 }}>
      <span style={{ width: 60, flex: 'none', color: 'var(--label-tertiary)', fontWeight: 600 }}>{label}</span>
      <span style={{ flex: 1, color: strong ? 'var(--label-primary)' : 'var(--label-secondary)', lineHeight: 1.4 }}>
        {children}</span>
    </div>
  );
}

// 제목 탭 시 펼쳐지는 '예정했던 훈련 내용' — 미기록은 계획만, 기록됨은 계획→실제 비교
function PlanDetail({ s }) {
  const dur = planDuration(s);
  const body = (() => {
    if (s.is_rest) return <div style={{ fontSize: 13.5, color: 'var(--label-secondary)' }}>{s.focus || '완전 휴식'}</div>;

    if (!s.log) {
      const rows = [
        ['목표 거리', s.distance_km ? `${s.distance_km} km` : null],
        ['목표 시간', dur],
        ['목표 페이스', s.target_pace],
        ['포커스', s.focus],
        ['메모', s.note],
      ].filter(([, v]) => v);
      if (!rows.length) return <div style={{ fontSize: 13.5, color: 'var(--label-tertiary)' }}>예정 상세 정보가 없어요.</div>;
      return rows.map(([k, v]) => (
        <DetailRow key={k} label={k} strong={k === '목표 거리' || k === '목표 페이스'}>{v}</DetailRow>
      ));
    }

    // 기록됨 → 계획 → 실제 비교
    const l = s.log;
    const cmp = [
      ['거리', s.distance_km ? `${s.distance_km}km` : '—', l.distance_km ? `${l.distance_km}km` : '—'],
      ['페이스', s.target_pace || '—', l.avg_pace ? `${l.avg_pace}/km` : '—'],
    ];
    if (dur || l.duration_sec) cmp.push(['시간', dur || '—', fmtDuration(l.duration_sec) || '—']);
    return (
      <>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--label-tertiary)', textAlign: 'right',
          paddingRight: 2, marginBottom: 4 }}>계획 → 실제</div>
        {cmp.map(([k, plan, act]) => (
          <DetailRow key={k} label={k} strong>
            <span style={{ color: 'var(--label-tertiary)' }}>{plan}</span>
            <span style={{ color: 'var(--label-tertiary)', margin: '0 6px' }}>→</span>
            <span style={{ fontWeight: 600 }}>{act}</span>
          </DetailRow>
        ))}
        {s.focus && <DetailRow label="포커스">{s.focus}</DetailRow>}
      </>
    );
  })();

  return (
    <div className="anim-in" style={{ padding: '0 16px 13px 62px' }}>
      <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '10px 13px' }}>{body}</div>
    </div>
  );
}

// ＋ 가 들어간 빈 원 — "여기 눌러 기록"
const plusCircleStyle = (c) => ({ width: 22, height: 22, borderRadius: 999, border: `2px solid ${c}`,
  display: 'grid', placeItems: 'center', flex: 'none' });

// 한 세션 행 — 제목 영역 탭=계획 펼침, 동그라미 탭=기록.
// recordable: 오늘·과거만 기록 진입 가능(미래는 아직 달릴 수 없음).
function SessionRow({ s, isToday, recordable, onCircle }) {
  const [open, setOpen] = useState(false);
  const w = wmeta(s.kind);
  const st = STATUS_META[s.status] || STATUS_META.planned;
  const logged = !!s.log;
  const isPast = s.session_date < localISO();
  // 지난(또는 오늘) 계획인데 기록이 없으면 '기록 필요' — 깜빡한 기록을 눈에 띄게
  const needsLog = recordable && !logged && !s.is_rest && s.status === 'planned';
  const dim = isPast && !logged && !needsLog;  // 지난 휴식일 등은 흐리게

  // 동그라미: 기록됨→상태 아이콘 / 미기록·기록가능→＋원 / 미래→정적 점
  let circle;
  if (logged) {
    circle = <Icon name={st.icon} size={22} color={st.color} style={{ flex: 'none' }} />;
  } else if (recordable) {
    const c = needsLog ? 'var(--tint)' : 'var(--label-tertiary)';
    circle = <span style={plusCircleStyle(c)}><Icon name="Plus" size={13} color={c} strokeWidth={3} /></span>;
  } else {
    circle = <Icon name={st.icon} size={20} color={st.color} style={{ flex: 'none', opacity: 0.7 }} />;
  }

  // 미래(기록 불가)는 정적, 그 외엔 탭하면 기록 흐름
  const circleEl = recordable ? (
    <button onClick={() => onCircle(s)} aria-label="훈련 기록"
      style={{ border: 'none', background: 'none', cursor: 'pointer', flex: 'none', display: 'grid',
        placeItems: 'center', padding: '12px 10px', margin: '-12px 0', WebkitTapHighlightColor: 'transparent' }}>
      {circle}</button>
  ) : (
    <span style={{ flex: 'none', display: 'grid', placeItems: 'center', padding: '0 10px' }}>{circle}</span>
  );

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', paddingRight: 6,
        background: isToday ? 'color-mix(in srgb, var(--tint) 7%, transparent)' : 'none' }}>
        <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
          style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 12, border: 'none',
            background: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit',
            padding: '13px 6px 13px 16px', WebkitTapHighlightColor: 'transparent' }}>
          <div style={{ width: 34, textAlign: 'center', flex: 'none' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--label-tertiary)' }}>{s.weekday}</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: isToday ? 'var(--tint)' : 'var(--label-primary)' }}>
              {parseInt(s.session_date.slice(8), 10)}</div>
          </div>
          <span style={{ width: 36, height: 36, borderRadius: 11, background: w.color, display: 'grid',
            placeItems: 'center', flex: 'none', opacity: dim ? 0.45 : 1 }}>
            <Icon name={w.icon} size={18} color="#fff" strokeWidth={2.1} /></span>
          <div style={{ flex: 1, minWidth: 0, opacity: dim ? 0.55 : 1 }}>
            <div style={{ fontSize: 15.5, fontWeight: 600, color: 'var(--label-primary)', whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'left' }}>{s.title || w.label}</div>
            <div style={{ fontSize: 13, marginTop: 1, textAlign: 'left',
              color: needsLog ? 'var(--tint)' : 'var(--label-secondary)', fontWeight: needsLog ? 600 : 400 }}>
              {logged ? loggedSubtitle(s) : sessionSubtitle(s)}</div>
          </div>
          <Icon name={open ? 'ChevronUp' : 'ChevronDown'} size={16} color="var(--label-tertiary)"
            strokeWidth={2.2} style={{ flex: 'none' }} />
        </button>
        {circleEl}
      </div>
      {open && <PlanDetail s={s} />}
    </>
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
          pendingGen.set({ type: 'adjust' });  // 끊겨도 재진입 시 복구
          try {
            const r = await api.adjustWeek(reason);
            pendingGen.clear(); onDone(r);
          } catch (e) {
            if (e.code === 'NETWORK') {
              // 연결만 끊겼다 — 서버는 조정을 끝냈을 수 있으니 현재 주를 다시 불러와 보여준다.
              const res = await reconcileOnce(() => pollUntil(() => genResult({ type: 'adjust' })));
              if (res === 'found') {
                pendingGen.clear();
                try { onDone(await api.currentWeek()); } catch { setBusy(false); }
                return;
              }
              if (res === 'busy') { setBusy(false); return; }  // App 복구 핸들러가 처리
            }
            pendingGen.clear();
            setError(e.message); setBusy(false);
          }
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

export default function Week({ refreshToday, onPlan, onRecord, reloadKey = 0 }) {
  const [week, setWeek] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noPlan, setNoPlan] = useState(false);
  const [error, setError] = useState(null);
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjustNote, setAdjustNote] = useState(null);
  const [evalBusy, setEvalBusy] = useState(false);
  const [confirmRec, setConfirmRec] = useState(null);  // 동그라미 탭 → 기록 확인 대상

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
  // 최초 진입 + 기록 저장(reloadKey 증가) 시 재로딩 → 방금 기록한 일자 즉시 반영
  useEffect(() => { load(); }, [reloadKey]);

  const reload = () => { load(); refreshToday?.(); };

  // 동그라미 탭 — 이미 기록됨은 바로 수정, 미기록은 확인 후 기록
  const handleCircle = (s) => {
    if (s.log) onRecord?.(s);
    else setConfirmRec(s);
  };

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
              <SectionLabel trailing={<span style={{ fontSize: 12, fontWeight: 500, color: 'var(--label-tertiary)' }}>
                제목=계획 · ⊕=기록</span>}>일정</SectionLabel>
              <Card pad={0}>
                {week.sessions.map((s, i) => (
                  <div key={s.id} style={{ borderBottom: i < week.sessions.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                    <SessionRow s={s} isToday={s.session_date === todayStr}
                      recordable={s.session_date <= todayStr}
                      onCircle={handleCircle} />
                  </div>
                ))}
              </Card>
            </div>

            {week.evaluation?.coach_message && <GrowthReport ev={week.evaluation} />}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 8 }}>
              <CTA variant="tinted" icon="Sparkles" busy={evalBusy} onClick={async () => {
                setEvalBusy(true); setError(null);
                pendingGen.set({ type: 'evaluate' });  // 끊겨도 재진입 시 복구
                try {
                  const r = await api.evaluateWeek();
                  pendingGen.clear(); setWeek(r);
                } catch (e) {
                  if (e.code === 'NETWORK') {
                    // 연결만 끊겼다 — 서버가 리포트를 저장했는지 폴링해 복구.
                    const res = await reconcileOnce(() => pollUntil(() => genResult({ type: 'evaluate' })));
                    if (res === 'found') { pendingGen.clear(); try { setWeek(await api.currentWeek()); } catch { /* keep */ } return; }
                    if (res === 'busy') return;  // App 복구 핸들러가 처리
                  }
                  pendingGen.clear();
                  setError(e.message);
                } finally { setEvalBusy(false); }
              }}>성장 리포트 만들기</CTA>
              <CTA variant="gray" icon={null} onClick={() => setShowAdjust(true)}>계획 조정이 필요해요</CTA>
            </div>
          </>
        )}
      </div>

      {confirmRec && (
        <Modal title="훈련 기록"
          subtitle={`${sessionDateLabel(confirmRec)} · ${confirmRec.title || wmeta(confirmRec.kind).label}`}
          onClose={() => setConfirmRec(null)}>
          <div style={{ padding: '18px 20px 22px' }}>
            <div style={{ fontSize: 15.5, lineHeight: 1.5, color: 'var(--label-primary)', marginBottom: 18 }}>
              이 날 훈련을 지금 기록할까요? 거리·시간·소감을 입력하면 코치가 분석해 줘요.</div>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1 }}>
                <CTA variant="gray" icon={null} onClick={() => setConfirmRec(null)}>취소</CTA></div>
              <div style={{ flex: 1 }}>
                <CTA icon="Pencil" onClick={() => { const s = confirmRec; setConfirmRec(null); onRecord?.(s); }}>
                  기록하기</CTA></div>
            </div>
          </div>
        </Modal>
      )}

      {showAdjust && (
        <AdjustSheet onClose={() => setShowAdjust(false)}
          onDone={(r) => {
            setShowAdjust(false);
            setWeek(r);
            if (r.adjustment) {
              const n = r.adjustment.changed?.length || 0;
              setAdjustNote(n ? `${n}개 세션이 조정됐어요 — ${r.adjustment.reason}`
                : `조정 불필요 — ${r.adjustment.reason || '현재 계획 유지를 권장해요.'}`);
            } else {
              // 복구 경로 — 조정 요약은 잃었지만 계획은 최신. 변경 여부를 직접 확인하게 안내.
              setAdjustNote('계획을 다시 불러왔어요 — 변경 사항을 확인해 주세요.');
            }
            refreshToday?.();
          }} />
      )}
    </div>
  );
}
