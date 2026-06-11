// 주간 계획 생성 모달 — 기본 시간표 확인 → 이번 주 특이 일정 입력 → AI 생성.
// 주의 첫 실행(계획 없음) 시 자동으로 열린다 (App.jsx).
import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtDays } from '../workouts.js';
import { Banner, Card, CTA, Icon, Modal } from './Ui.jsx';

export function AvailabilitySummary({ slots, onEdit }) {
  return (
    <Card pad={14} style={{ background: 'var(--fill-tertiary)', boxShadow: 'none' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: slots.length ? 10 : 0 }}>
        <Icon name="CalendarClock" size={15} color="var(--label-secondary)" />
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--label-secondary)' }}>훈련 가능 시간 (기본)</span>
        {onEdit && <button onClick={onEdit} style={{ marginLeft: 'auto', background: 'none', border: 'none',
          color: 'var(--tint)', fontSize: 13, fontWeight: 600, cursor: 'pointer', padding: 0 }}>설정에서 변경</button>}
      </div>
      {slots.length === 0 ? (
        <div style={{ fontSize: 13.5, color: 'var(--label-tertiary)' }}>등록된 시간표가 없어요 — 설정에서 추가해 주세요.</div>
      ) : slots.map((s) => (
        <div key={s.id ?? s.title} style={{ display: 'flex', alignItems: 'baseline', gap: 8, padding: '3px 0' }}>
          <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--tint)', flex: 'none', minWidth: 34 }}>
            {fmtDays(s.days)}</span>
          <span style={{ fontSize: 14, color: 'var(--label-primary)', fontWeight: 500 }}>{s.title}</span>
          <span style={{ fontSize: 12.5, color: 'var(--label-tertiary)' }}>
            {s.duration_min ? `${s.duration_min}분` : ''}{s.place ? ` · ${s.place}` : ''}</span>
        </div>
      ))}
    </Card>
  );
}

export default function PlanSheet({ onClose, onDone, goSettings }) {
  const [slots, setSlots] = useState(null);
  const [special, setSpecial] = useState('');
  const [condition, setCondition] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.availability().then((r) => setSlots(r.slots)).catch(() => setSlots([]));
  }, []);

  const generate = async () => {
    setBusy(true); setError(null);
    try {
      await api.generateWeek({ schedule_note: special, condition_note: condition });
      onDone();
    } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Modal title="이번 주 계획 만들기" subtitle="기본 시간표를 확인하고, 이번 주에 다른 점만 알려주세요."
      locked={busy} onClose={onClose}>
      <div style={{ padding: '4px 20px 24px' }}>
        <div style={{ margin: '12px 0' }}>
          {slots === null
            ? <div style={{ fontSize: 14, color: 'var(--label-secondary)', padding: 8 }}>시간표 불러오는 중…</div>
            : <AvailabilitySummary slots={slots} onEdit={goSettings} />}
        </div>

        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', margin: '14px 0 6px',
          textTransform: 'uppercase', letterSpacing: '0.3px' }}>이번 주 특이 일정 (선택)</div>
        <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '11px 13px' }}>
          <textarea value={special} onChange={(e) => setSpecial(e.target.value)} rows={2}
            placeholder="기본 시간표와 다른 점만 — 예: 수요일 회식, 금요일 출장"
            style={{ border: 'none', outline: 'none', background: 'none', width: '100%', resize: 'none',
              fontSize: 15, color: 'var(--label-primary)', lineHeight: 1.5 }} />
        </div>

        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', margin: '14px 0 6px',
          textTransform: 'uppercase', letterSpacing: '0.3px' }}>컨디션 (선택)</div>
        <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '11px 13px', marginBottom: 16 }}>
          <textarea value={condition} onChange={(e) => setCondition(e.target.value)} rows={2}
            placeholder="예: 발목 통증 없음, 수면 충분"
            style={{ border: 'none', outline: 'none', background: 'none', width: '100%', resize: 'none',
              fontSize: 15, color: 'var(--label-primary)', lineHeight: 1.5 }} />
        </div>

        {error && <div style={{ marginBottom: 12 }}><Banner tone="error">{error}</Banner></div>}
        <CTA busy={busy} icon="Sparkles" onClick={generate}>
          {busy ? 'AI 코치가 가능 시간을 검토 중…' : '훈련 가능 시간 검토하고 7일 계획 생성'}</CTA>
        <button onClick={onClose} disabled={busy} style={{ display: 'block', margin: '12px auto 0', background: 'none',
          border: 'none', color: 'var(--label-tertiary)', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
          나중에 할게요</button>
      </div>
    </Modal>
  );
}
