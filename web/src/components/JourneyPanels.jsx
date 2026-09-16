import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtHMS, localISO, wmeta } from '../workouts.js';
import { Banner, Card, CTA, Expander, inputStyle, Modal, SectionLabel, Spinner } from './Ui.jsx';
import Markdown from './Markdown.jsx';

const STATUS = { insufficient: '데이터 부족', pb_reference: 'PB 참고 추정', recent: '최근 기록 기반' };
export const fulfillmentLabel = (status) => ({ planned: '예정', done: '계획대로 수행', partial: '부분 수행', substituted: '대체 훈련', missed: '미수행' }[status] || '계획 연결 없음');

export function DataState({ dash, reloadKey, onImport, goSettings }) {
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let alive = true;
    api.pendingActivities().then((d) => { if (alive) { setPending(d); setError(null); } }).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [reloadKey, dash.assessment_id]);
  const s = dash.current.data_status;
  return <Card pad={18}>
    <b style={{ color: 'var(--tint)' }}>{STATUS[s.state]}</b>
    <p style={{ fontSize: 14 }}>최근 적합한 러닝 {s.record_count}건 · 관측 {s.observation_days}일<br />마지막 기록: {s.last_date || '없음'}<br />마지막 반영: {s.last_reflected_at ? new Date(s.last_reflected_at).toLocaleString() : '없음'}</p>
    <small style={{ color: 'var(--label-secondary)' }}>{s.criteria}</small>
    {error && <Banner tone="warn">연동 상태 확인 실패: {error}</Banner>}
    <div style={{ marginTop: 12 }}><CTA variant="tinted" onClick={onImport}>{pending ? `미반영 활동 ${pending.pending_count}건 · 확인 및 기록 추가` : '연동 상태 확인 · 기록 추가'}</CTA></div>
    {pending && Object.entries(pending.integrations).filter(([, i]) => i.connected || i.last_sync_error).map(([p, i]) => <p key={p} style={{ fontSize: 12 }}>
      {p} · 최근 동기화 {i.last_sync_at ? new Date(i.last_sync_at).toLocaleString() : '없음'}{i.last_sync_error ? ` · ${i.last_sync_error}` : ''}</p>)}
    {!s.sufficient && <CTA variant="ghost" onClick={goSettings}>PB와 달성일 확인</CTA>}
  </Card>;
}

function TrainingSummary({ value }) {
  if (!value) return <span>없음</span>;
  const s = value.session || value;
  return <span>{s.title || wmeta(s.kind).label} {s.distance_km != null ? `${s.distance_km}km` : ''} {s.duration_min ? `${s.duration_min}분` : ''}{s.is_rest ? ' · 휴식' : ''}</span>;
}

export function ConditionChange({ onApplied }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [proposal, setProposal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  return <><CTA variant="gray" onClick={() => { setOpen(true); setProposal(null); setError(null); }}>컨디션 변경</CTA>
    {open && <Modal title="오늘 컨디션 변경" subtitle="변경 전후를 확인하고 적용하세요" onClose={() => setOpen(false)} locked={busy}>
      <div style={{ padding: 20, display: 'grid', gap: 14 }}>
        <textarea aria-label="컨디션 변경 사유" value={reason} onChange={(e) => { setReason(e.target.value); setProposal(null); }} rows={3} style={inputStyle} placeholder="수면, 피로, 통증과 변경 사유" />
        {error && <Banner tone="error">{error}</Banner>}
        {!proposal ? <CTA busy={busy} disabled={!reason.trim()} onClick={async () => {
          setBusy(true); setError(null);
          try { setProposal(await api.generateDaily({ condition_note: reason, preview: true })); }
          catch (e) { setError(e.message); } finally { setBusy(false); }
        }}>변경안 확인</CTA> : <>
          <small>입력 시각: {new Date(proposal.created_at).toLocaleString()}</small><p>{proposal.reason}</p>
          <Card><b>변경 전</b><p><TrainingSummary value={proposal.before} /></p><p>{proposal.before.sections?.main}</p></Card>
          <Card><b>변경 후</b><p><TrainingSummary value={proposal.after} /></p><p>{proposal.after.sections?.main}</p></Card>
          <CTA busy={busy} onClick={async () => { setBusy(true); setError(null); try { await api.applyDaily(proposal.proposal_id); setOpen(false); await onApplied(); } catch (e) { setError(e.message); } finally { setBusy(false); } }}>이 변경을 오늘·주간 계획에 적용</CTA>
        </>}
      </div>
    </Modal>}
  </>;
}

export function ChangeInsights({ dash, refresh, goToday }) {
  const [reviewDate, setReviewDate] = useState(dash.outlook?.suggested_checkpoint || localISO());
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const o = dash.outlook;
  if (!o) return null;
  return <>
    <Expander title="변화 원인과 입력 근거" icon="Info">
      {dash.changes.map((c) => <div key={c.cause} style={{ marginBottom: 12 }}>
        <b>{c.text}</b>
        {c.cause === 'volume_changed' && <p>주 평균 {c.before.vol_4wk_km} → {c.after.vol_4wk_km}km · 최장 {c.before.long_run_km} → {c.after.long_run_km}km</p>}
        {c.cause === 'reference_changed' && <p>기준 기록: {c.before?.date || 'PB 날짜 미상'} {c.before?.time || '없음'} → {c.after?.date || 'PB 날짜 미상'} {c.after?.time || '없음'}</p>}
      </div>)}
      {dash.events.filter((e) => ['plan_changed', 'condition_changed', 'record_corrected', 'goal_changed', 'profile_changed'].includes(e.type)).map((e) => <div key={e.id} style={{ margin: '12px 0', borderTop: '1px solid var(--separator-non-opaque)', paddingTop: 10 }}>
        <small>{new Date(e.date).toLocaleString()}</small><div>{e.reason}</div>
        {['plan_changed', 'condition_changed'].includes(e.type) && <p><TrainingSummary value={e.before} /> → <TrainingSummary value={e.after} /></p>}
        {e.type === 'record_corrected' && <p>거리 {e.before.distance_km} → {e.after.distance_km}km · 시간 {fmtHMS(e.before.duration_sec)} → {fmtHMS(e.after.duration_sec)}</p>}
        {e.type === 'goal_changed' && <p>{e.before?.race_type || '첫 목표'} {e.before?.target_time} → {e.after.race_type} {e.after.target_time} · {e.after.target_date}</p>}
        {e.type === 'profile_changed' && <p>PB 10K {e.before.pb_10k || '없음'} → {e.after.pb_10k || '없음'} · 하프 {e.before.pb_half || '없음'} → {e.after.pb_half || '없음'} · 풀 {e.before.pb_full || '없음'} → {e.after.pb_full || '없음'}</p>}
      </div>)}
    </Expander>
    <Expander title="목표일까지의 조건부 검토" icon="Flag">
      <b>{o.status}</b><p>{o.message}</p>
      <p>등록된 가용 시간: 주 {o.available_min_per_week}분 · 남은 기간 {o.weeks_left ?? '미정'}주<br />이번 주 남은 계획 {o.remaining_plan_sessions}회 · {o.remaining_plan_min_this_week}분</p>
      <p>목표까지 필요한 변화: {o.required_change_sec == null ? '산출 불가' : `${fmtHMS(Math.abs(o.required_change_sec))} ${o.required_change_sec > 0 ? '단축' : '목표 기록 이내 환산'}`}</p>
      <ol>{o.conditions.map((c) => <li key={c}>{c}</li>)}</ol>
      <CTA variant="gray" onClick={goToday}>현재 컨디션과 오늘 계획 확인</CTA>
      {dash.goal && <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
        <label>다음 목표 검토일<input aria-label="목표 검토일" type="date" style={inputStyle} value={reviewDate} onChange={(e) => setReviewDate(e.target.value)} /></label>
        <CTA variant="tinted" busy={busy} disabled={!reviewDate} onClick={async () => {
          setBusy(true); setError(null);
          try { await api.addCheckpoint({ goal_id: dash.goal.id, review_date: reviewDate, evidence_needed: '미반영 기록 확인 · 계획 수행 및 같은 조건 러닝 비교 · 목표 유지/수정 검토' }); await refresh(); }
          catch (e) { setError(e.message); } finally { setBusy(false); }
        }}>체크포인트 저장</CTA>
        {dash.checkpoints.map((c) => <Checkpoint key={c.id} checkpoint={c} refresh={refresh} />)}
      </div>}
      {error && <Banner tone="error">{error}</Banner>}
    </Expander>
  </>;
}

function Checkpoint({ checkpoint: c, refresh }) {
  const [decision, setDecision] = useState(c.decision || '');
  const [error, setError] = useState(null);
  return <Card><b>{c.review_date}</b><p>{c.evidence_needed}</p>
    <input aria-label={`${c.review_date} 검토 결론`} style={inputStyle} value={decision} onChange={(e) => setDecision(e.target.value)} placeholder="근거와 목표 유지·수정 결론" />
    <CTA variant="gray" disabled={!decision.trim()} onClick={async () => { try { await api.decideCheckpoint(c.id, decision); refresh(); } catch (e) { setError(e.message); } }}>검토 결론 저장</CTA>
    {error && <Banner tone="error">{error}</Banner>}
  </Card>;
}

export function CoachingTasks({ tasks = [], refresh }) {
  const [error, setError] = useState(null);
  if (!tasks.length) return null;
  return <Expander title="다음 계획 코칭 과제" icon="Target">
    {tasks.map((t) => <div key={t.id} style={{ padding: '12px 0' }}>
      <b>{t.proposal}</b><p>근거: {t.source_log_id ? `운동 #${t.source_log_id}` : '주간 평가'} · {t.status === 'resolved' ? '확인 완료' : '다음 평가에서 확인'}</p>
      <small>AI의 제안입니다. 실제 기록을 기준으로 다시 확인합니다.</small>
      {t.assignments.map((a) => <p key={a.plan_id}>{a.iso_week} · {a.status === 'applied' ? `반영: ${a.session_dates.join(', ')}` : '보류'} — {a.reason}</p>)}
      {t.evaluations.map((e) => <div key={e.plan_id}><p>{e.result}</p>{e.actual.map((l) => <small key={l.log_id}>운동 #{l.log_id} · {l.distance_km}km · {fmtHMS(l.duration_sec)} · 통증 {l.pain_level} / 10<br /></small>)}</div>)}
      <CTA variant="gray" onClick={async () => { try { await api.patchTask(t.id, t.status === 'resolved' ? 'open' : 'resolved'); refresh(); } catch (e) { setError(e.message); } }}>{t.status === 'resolved' ? '다시 확인할 과제로 열기' : '실제 수행 확인 후 과제 완료'}</CTA>
    </div>)}
    {error && <Banner tone="error">{error}</Banner>}
  </Expander>;
}

export function GrowthHistory({ onEdit, reloadKey }) {
  const [open, setOpen] = useState(false);
  return <><CTA variant="gray" onClick={() => setOpen(!open)}>{open ? '성장 기록실 접기' : '성장 기록실 · 주·월·목표 비교'}</CTA>
    {open && <GrowthContents onEdit={onEdit} reloadKey={reloadKey} />}</>;
}

function GrowthContents({ onEdit, reloadKey }) {
  const [period, setPeriod] = useState('week');
  const [end, setEnd] = useState(localISO());
  const [goals, setGoals] = useState([]);
  const [goalId, setGoalId] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [assessmentId, setAssessmentId] = useState('');
  useEffect(() => { api.goals().then((g) => setGoals(g.items)).catch((e) => setError(e.message)); }, []);
  const startDate = new Date(`${end}T12:00:00`);
  startDate.setDate(startDate.getDate() - (period === 'month' ? 27 : 6));
  const goal = goals.find((g) => String(g.id) === goalId);
  const start = period === 'goal' && goal ? goal.created_at.slice(0, 10) : localISO(startDate);
  useEffect(() => {
    let alive = true; setData(null); setError(null); setAssessmentId(''); setReport(null);
    api.growth({ start, end, ...(goalId ? { goal_id: goalId } : {}) }).then((d) => alive && setData(d)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [start, end, goalId, reloadKey]);
  const assessment = data?.assessments.find((a) => String(a.id) === assessmentId);
  return <Card pad={16}>
    <SectionLabel>성장 기록실</SectionLabel>
    <div style={{ display: 'grid', gap: 10 }}>
      <select aria-label="비교 기간" value={period} onChange={(e) => setPeriod(e.target.value)} style={inputStyle}>
        <option value="week">주 · 7일</option><option value="month">월 · 28일</option><option value="goal">목표 기간</option>
      </select>
      <select aria-label="목표 버전" value={goalId} onChange={(e) => setGoalId(e.target.value)} style={inputStyle}>
        <option value="">전체 목표</option>{goals.map((g) => <option key={g.id} value={g.id}>{g.is_active ? '현재' : '이전'} 목표 · {g.race_type} {g.target_time} · {g.target_date}</option>)}
      </select>
      <label>기간 마지막 날<input type="date" aria-label="기간 마지막 날" value={end} max={localISO()} onChange={(e) => e.target.value && setEnd(e.target.value)} style={inputStyle} /></label>
    </div>
    {error && <Banner tone="error">{error}</Banner>}
    {!data && !error && <Spinner label="성장 기록 비교 중…" />}
    {data && <>
      <p>{data.start}~{data.end}와 직전 같은 길이 기간 {data.previous_start}~{data.previous_end} 비교</p>
      <table style={{ width: '100%', fontSize: 14 }}><thead><tr><th>실제 관측값</th><th>이전</th><th>선택 기간</th></tr></thead>
        <tbody>{[['러닝 거리', 'distance_km', 'km'], ['러닝 횟수', 'running_records', '건'], ['지속 시간', 'duration_sec', '초'], ['시간 있는 기록', 'timed_records', '건']].map(([label, key, unit]) => <tr key={key}><td>{label}</td><td>{data.previous[key]}{unit}</td><td>{data.current[key]}{unit}</td></tr>)}</tbody>
      </table>
      <p>{data.comparison_message}</p><small>{data.comparison_rule}</small>
      {data.comparable.map((c, i) => <p key={i}>{c.condition} · {c.distance_km}km · 표본 {c.before_count}/{c.after_count}건<br />페이스 {fmtHMS(c.before_pace_sec)} → {fmtHMS(c.after_pace_sec)} /km<br />{c.heart_rate ? `평균 심박 ${c.heart_rate.before} → ${c.heart_rate.after}` : '심박 비교 불가'}</p>)}
      <p>{data.next_action}</p>
      <label>당시 평가 선택<select aria-label="당시 평가 선택" style={inputStyle} value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}>
        <option value="">평가를 선택하세요</option>{data.assessments.map((a) => <option key={a.id} value={a.id}>{a.as_of} · {a.current.predicted_time || '근거 부족'} · {a.reason}</option>)}
      </select></label>
      {assessment && data.assessments.length > 1 && <table style={{ width: '100%', fontSize: 13 }}><thead><tr><th>당시 평가 비교</th><th>기간 첫 평가</th><th>선택 평가</th></tr></thead><tbody>
        <tr><td>평가일</td><td>{data.assessments[0].as_of}</td><td>{assessment.as_of}</td></tr>
        <tr><td>당시 목표</td><td>{data.assessments[0].inputs.goal?.target_time || '미정'}</td><td>{assessment.inputs.goal?.target_time || '미정'}</td></tr>
        <tr><td>환산값</td><td>{data.assessments[0].current.predicted_time || '근거 부족'}</td><td>{assessment.current.predicted_time || '근거 부족'}</td></tr>
        <tr><td>최근 기록 수</td><td>{data.assessments[0].current.data_status.record_count}건</td><td>{assessment.current.data_status.record_count}건</td></tr>
      </tbody></table>}
      {assessment && data.assessments[0]?.goal_id !== assessment.goal_id && <p>목표 기준이 달라 환산값의 직접 비교가 제한됩니다.</p>}
      {assessment && <div><b>당시 평가 · {assessment.as_of}</b><p>당시 목표 {assessment.inputs.goal?.target_time || '없음'} · 환산값 {assessment.current.predicted_time || '산출 불가'}<br />{STATUS[assessment.current.data_status.state]} · {assessment.reason}</p><small>PB 10K {assessment.inputs.pbs.pb_10k || '없음'} · 4주 평균 {assessment.current.basis.vol_4wk_km}km/주</small></div>}
      {!data.assessments.length && <p>이 기간의 당시 평가는 없습니다. 스냅샷 도입 전 과거 값은 소급 추정만 가능합니다.</p>}
      <select aria-label="과거 주간 리포트" style={inputStyle} defaultValue="" onChange={async (e) => { if (!e.target.value) return; try { setReport(await api.week(e.target.value)); } catch (err) { setError(err.message); } }}>
        <option value="">주간 리포트 선택</option>{data.reports.map((r) => <option key={r.plan_id} value={r.iso_week}>{r.iso_week}</option>)}
      </select>
      {report && <div><b>{report.iso_week}</b>{report.evaluation ? <><p>{report.evaluation.coach_message}</p><Markdown text={report.evaluation.detail_md} /></> : <p>이 주의 저장된 평가가 없습니다.</p>}</div>}
      <Expander title={`선택 기간 원본 운동 ${data.logs.length}건`} icon="Footprints">
        {data.logs.map((l) => <p key={l.id}>{l.log_date} · {l.distance_km}km · {fmtHMS(l.duration_sec)} <button onClick={() => onEdit(l)}>이 기록 수정</button></p>)}
      </Expander>
    </>}
  </Card>;
}
