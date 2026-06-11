// record.jsx — 훈련 기록 입력 폼 (bottom sheet) + AI 코치 리뷰
const { useState: useStateRecord, useRef: useRefRecord } = React;

function FormField({ label, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)',
        textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  );
}

function NumInput({ value, onChange, placeholder, unit, flex = 1 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: 'var(--fill-tertiary)', borderRadius: 12, padding: '11px 14px', flex }}>
      <input type="number" inputMode="decimal" value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ border: 'none', outline: 'none', background: 'none', flex: 1, fontFamily: 'var(--font-display)',
          fontSize: 22, fontWeight: 700, color: 'var(--label-primary)', letterSpacing: '-0.5px', width: '100%', minWidth: 0 }} />
      {unit && <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-tertiary)', fontWeight: 600, marginLeft: 4 }}>{unit}</span>}
    </div>
  );
}

function FeelPicker({ value, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 10 }}>
      {FEEL_OPTIONS.map(f => (
        <button key={f.v} onClick={() => onChange(f.v)}
          style={{ flex: 1, padding: '12px 6px', borderRadius: 14, border: 'none', cursor: 'pointer', transition: 'all .15s',
            background: value === f.v ? 'var(--tint)' : 'var(--fill-tertiary)',
            transform: value === f.v ? 'scale(1.05)' : 'none' }}>
          <div style={{ fontSize: 24, lineHeight: 1 }}>{f.emoji}</div>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 11, fontWeight: 600, marginTop: 5,
            color: value === f.v ? '#fff' : 'var(--label-tertiary)' }}>{f.label}</div>
        </button>
      ))}
    </div>
  );
}

function PainChips({ selected, onToggle, sliders, onSlide }) {
  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {BODY_PARTS.map(p => {
          const on = selected.includes(p);
          return (
            <button key={p} onClick={() => onToggle(p)}
              style={{ padding: '7px 14px', borderRadius: 999, border: 'none', cursor: 'pointer', fontFamily: 'var(--font-text)',
                fontSize: 14, fontWeight: 600, transition: 'all .12s',
                background: on ? 'rgba(255,56,60,0.14)' : 'var(--fill-tertiary)',
                color: on ? 'var(--accent-red)' : 'var(--label-secondary)' }}>
              {p}
            </button>
          );
        })}
      </div>
      {selected.map(p => (
        <div key={p} style={{ marginBottom: 12 }}>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-primary)', fontWeight: 600, marginBottom: 8 }}>
            {p} · {Math.round((sliders[p] || 0.3) * 10)}/10</div>
          <Slider value={sliders[p] || 0.3} onChange={v => onSlide(p, v)} tint="var(--accent-red)" />
        </div>
      ))}
    </div>
  );
}

// AI Review screen shown after save
function AIReview({ form, workout, coach, onDone }) {
  const w = WORKOUT_TYPES[workout.type];
  const [expanded, setExpanded] = useStateRecord(false);
  const km = parseFloat(form.distance) || 0;
  const pace = form.pace || '5:12';
  return (
    <div style={{ padding: '0 0 32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', gap: 12, padding: '4px 0 20px', alignItems: 'center' }}>
        <span style={{ width: 44, height: 44, borderRadius: 14, background: w.color, display: 'grid', placeItems: 'center', flex: 'none',
          boxShadow: `0 4px 14px rgba(${w.rgb},0.35)` }}><Icon name="sparkles" size={22} color="#fff" /></span>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--label-primary)' }}>AI 코치 분석</div>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)' }}>{workout.title}</div>
        </div>
      </div>

      {/* Metric summary */}
      <Card style={{ marginBottom: 14 }}>
        <MetricRow items={[
          { value: km.toFixed(1), unit: 'km', label: '거리' },
          { value: pace, label: '페이스' },
          { value: form.avgHr || '--', label: '평균 심박' },
        ]} size={24} />
      </Card>

      {/* Coach narrative */}
      <Card style={{ background: `rgba(${w.rgb},0.08)`, boxShadow: 'none', marginBottom: 14 }}>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 16, color: 'var(--label-primary)', lineHeight: 1.6 }}>
          {coach.reviewIntro(km.toFixed(1), pace)}&nbsp;
          {workout.type === 'tempo' ? coach.tempo : coach.interval({ feel: parseInt(form.feel) || 3 })}
        </div>
        <div style={{ marginTop: 14, paddingTop: 12, borderTop: '0.5px solid var(--separator-non-opaque)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <RecoveryBadge level={parseInt(form.feel) <= 2 ? 'medium' : 'low'} />
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)', marginLeft: 4 }}>
            {FEEL_OPTIONS.find(f => f.v === parseInt(form.feel))?.label || '양호'}</span>
        </div>
      </Card>

      {/* Next session preview */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <Icon name="calendar" size={16} color="var(--label-tertiary)" />
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>다음 훈련 예고</span>
        </div>
        {(() => {
          const next = WEEK_PLAN.slice(TODAY_INDEX + 1).find(s => s.type !== 'rest');
          if (!next) return <div style={{ color: 'var(--label-tertiary)', fontSize: 14, fontFamily: 'var(--font-text)' }}>이번 주 남은 훈련 없음</div>;
          const nw = WORKOUT_TYPES[next.type];
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 40, height: 40, borderRadius: 12, background: nw.color, display: 'grid', placeItems: 'center', flex: 'none' }}>
                <Icon name={nw.icon} size={20} color="#fff" strokeWidth={2.1} /></span>
              <div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 16, fontWeight: 600, color: 'var(--label-primary)' }}>{next.title}</div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)' }}>{next.distance > 0 ? next.distance + 'km · ' : ''}{next.estMin > 0 ? next.estMin + '분' : '완전 휴식'}</div>
              </div>
            </div>
          );
        })()}
      </Card>

      <CTA onClick={onDone}>확인</CTA>
    </div>
  );
}

function RecordSheet({ workout, coach, onSave, onClose }) {
  const [form, setF] = useStateRecord({ distance: '', minutes: '', seconds: '', pace: '', avgHr: '', maxHr: '', cadence: '', feel: 3, note: '' });
  const [pain, setPain] = useStateRecord([]);
  const [painSliders, setPainSliders] = useStateRecord({});
  const [phase, setPhase] = useStateRecord('form'); // 'form' | 'saving' | 'review'
  const set = (k, v) => setF(p => ({ ...p, [k]: v }));

  const togglePain = (p) => setPain(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  const slidePain = (p, v) => setPainSliders(prev => ({ ...prev, [p]: v }));

  const handleSave = () => {
    setPhase('saving');
    setTimeout(() => setPhase('review'), 1600);
  };

  const w = WORKOUT_TYPES[workout.type];

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 50, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
      background: 'rgba(0,0,0,0.32)' }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-grouped-primary)', borderRadius: '26px 26px 0 0', maxHeight: '92%',
        display: 'flex', flexDirection: 'column', boxShadow: '0 -8px 30px rgba(0,0,0,0.18)' }}>
        {/* Drag handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 0', flex: 'none' }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: 'var(--fill-secondary)' }} />
        </div>
        {/* Header */}
        <div style={{ padding: '10px 20px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flex: 'none',
          borderBottom: '0.5px solid var(--separator-non-opaque)' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--label-primary)' }}>
              {phase === 'review' ? 'AI 코치 분석' : phase === 'saving' ? '저장 중…' : '훈련 기록'}</div>
            <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>{workout.title}</div>
          </div>
          {phase === 'form' && (
            <button onClick={onClose} style={{ background: 'var(--fill-tertiary)', border: 'none', width: 30, height: 30,
              borderRadius: '50%', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
              <Icon name="x" size={16} color="var(--label-secondary)" strokeWidth={2.4} />
            </button>
          )}
        </div>

        {/* Saving spinner */}
        {phase === 'saving' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
            <div style={{ width: 52, height: 52, borderRadius: 16, background: w.color, display: 'grid', placeItems: 'center',
              boxShadow: `0 6px 20px rgba(${w.rgb},0.35)`, animation: 'spin 1.2s linear infinite' }}>
              <Icon name="sparkles" size={26} color="#fff" />
            </div>
            <div style={{ fontFamily: 'var(--font-text)', fontSize: 16, color: 'var(--label-secondary)' }}>AI 코치가 분석 중이에요…</div>
          </div>
        )}

        {/* Review */}
        {phase === 'review' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px' }}>
            <AIReview form={form} workout={workout} coach={coach} onDone={() => { onSave(form); onClose(); }} />
          </div>
        )}

        {/* Form */}
        {phase === 'form' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 0' }}>
            <FormField label="기본 기록">
              <div style={{ display: 'flex', gap: 10 }}>
                <NumInput value={form.distance} onChange={v => set('distance', v)} placeholder="0.0" unit="km" />
                <NumInput value={form.minutes} onChange={v => set('minutes', v)} placeholder="분" />
                <NumInput value={form.seconds} onChange={v => set('seconds', v)} placeholder="초" />
              </div>
            </FormField>

            <FormField label="페이스 · 심박">
              <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
                <NumInput value={form.pace} onChange={v => set('pace', v)} placeholder="5:10" unit="/km" />
                <NumInput value={form.avgHr} onChange={v => set('avgHr', v)} placeholder="평균" unit="bpm" />
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <NumInput value={form.maxHr} onChange={v => set('maxHr', v)} placeholder="최대" unit="bpm" />
                <NumInput value={form.cadence} onChange={v => set('cadence', v)} placeholder="케이던스" unit="spm" />
              </div>
            </FormField>

            {/* Photo upload placeholder */}
            <FormField label="가민 · 스트라바 캡처">
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 18px',
                background: 'var(--fill-tertiary)', borderRadius: 16, cursor: 'pointer' }}>
                <span style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--fill-secondary)', display: 'grid', placeItems: 'center' }}>
                  <Icon name="camera" size={22} color="var(--label-tertiary)" /></span>
                <div>
                  <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, fontWeight: 600, color: 'var(--label-primary)' }}>사진 추가</div>
                  <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)' }}>가민 / 스트라바 캡처 (API 연동 예정)</div>
                </div>
              </div>
            </FormField>

            <FormField label="오늘 몸 상태">
              <FeelPicker value={form.feel} onChange={v => set('feel', v)} />
            </FormField>

            <FormField label="불편한 곳 (선택)">
              <PainChips selected={pain} onToggle={togglePain} sliders={painSliders} onSlide={slidePain} />
            </FormField>

            <FormField label="한 줄 소감">
              <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '12px 14px' }}>
                <textarea value={form.note} onChange={e => set('note', e.target.value)} placeholder="오늘 훈련 어땠나요?"
                  rows={3} style={{ border: 'none', outline: 'none', background: 'none', width: '100%', resize: 'none',
                    fontFamily: 'var(--font-text)', fontSize: 16, color: 'var(--label-primary)', lineHeight: 1.5 }} />
              </div>
            </FormField>

            <div style={{ paddingBottom: 40 }}>
              <CTA onClick={handleSave}>기록 저장하기</CTA>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { RecordSheet });
