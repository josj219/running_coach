// week.jsx — 이번 주 탭: 주간 훈련표, 계획 생성, 성장 리포트
const { useState: useStateWeek } = React;

function DayRow({ session, idx, onSelect, isToday }) {
  const w = WORKOUT_TYPES[session.type];
  const [pressed, setPressed] = useStateWeek(false);
  return (
    <div onClick={() => onSelect(idx)}
      onPointerDown={() => setPressed(true)} onPointerUp={() => setPressed(false)} onPointerLeave={() => setPressed(false)}
      style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', cursor: 'pointer',
        background: pressed ? 'var(--fill-quaternary)' : 'transparent',
        borderLeft: isToday ? `3px solid ${w.color}` : '3px solid transparent' }}>
      {/* Day dot */}
      <div style={{ width: 36, height: 36, borderRadius: '50%', flex: 'none', display: 'grid', placeItems: 'center',
        background: session.done ? w.color : (isToday ? `rgba(${w.rgb},0.14)` : 'var(--fill-tertiary)'),
        boxShadow: session.done ? `0 3px 10px rgba(${w.rgb},0.30)` : 'none' }}>
        {session.done
          ? <Icon name="check" size={18} color="#fff" strokeWidth={2.6} />
          : <Icon name={w.icon} size={18} color={isToday ? w.color : 'var(--label-tertiary)'} strokeWidth={2} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-text)', fontWeight: 600, fontSize: 16,
            color: isToday ? 'var(--label-primary)' : (session.done ? 'var(--label-secondary)' : 'var(--label-primary)') }}>
            {WEEK_DAYS[idx]}요일</span>
          {isToday && <span style={{ fontFamily: 'var(--font-text)', fontSize: 11, fontWeight: 700, background: w.color,
            color: '#fff', borderRadius: 999, padding: '2px 8px', letterSpacing: '0.2px' }}>오늘</span>}
        </div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>
          {session.title}{session.distance > 0 ? ` · ${session.distance}km` : ''}</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
        {session.done && session.result
          ? <span style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 700, color: w.color, fontVariantNumeric: 'tabular-nums' }}>{session.result.distance.toFixed(1)}km</span>
          : session.estMin > 0 && <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-tertiary)' }}>{session.estMin}분</span>}
        <Icon name="chevron-right" size={16} color="var(--label-quaternary)" strokeWidth={2.4} />
      </div>
    </div>
  );
}

function WeekSummaryBar({ plan }) {
  const done = plan.filter(s => s.done);
  const pct = Math.round(done.length / plan.length * 100);
  const km = done.reduce((s, d) => s + (d.result ? d.result.distance : 0), 0).toFixed(1);
  const target = plan.reduce((s, d) => s + d.distance, 0);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <Ring pct={pct} size={64} stroke={6}>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, color: 'var(--tint)' }}>{pct}%</span>
      </Ring>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <Metric value={km} unit="km" label="완료 거리" size={22} />
          <Metric value={`${done.length}/${plan.length}`} label="완료 세션" size={22} />
        </div>
        <div style={{ marginTop: 10, height: 5, background: 'var(--fill-tertiary)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--tint)', borderRadius: 3,
            transition: 'width .5s cubic-bezier(.32,.72,0,1)' }} />
        </div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 12, color: 'var(--label-tertiary)', marginTop: 5 }}>
          목표 {target}km 중 {km}km 완료</div>
      </div>
    </div>
  );
}

// Session detail sheet
function SessionSheet({ session, idx, coach, onClose, onRecord }) {
  const w = WORKOUT_TYPES[session.type];
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 40, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
      background: 'var(--overlay-default)' }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-grouped-primary)', borderRadius: '26px 26px 0 0', maxHeight: '85%',
        overflowY: 'auto', padding: '0 0 40px', boxShadow: '0 -8px 30px rgba(0,0,0,0.16)' }}>
        {/* Drag handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: 'var(--fill-secondary)' }} />
        </div>
        {/* Header */}
        <div style={{ padding: '12px 20px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <TypeBadge type={session.type} />
          <button onClick={onClose} style={{ background: 'var(--fill-tertiary)', border: 'none', width: 30, height: 30,
            borderRadius: '50%', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
            <Icon name="x" size={16} color="var(--label-secondary)" strokeWidth={2.4} />
          </button>
        </div>
        <div style={{ padding: '0 20px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700, color: 'var(--label-primary)', letterSpacing: '-0.5px' }}>{session.title}</div>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-secondary)', marginTop: 4 }}>{WEEK_DAYS[idx]}요일 · {session.estMin > 0 ? session.estMin + '분' : '완전 휴식'}</div>

          {/* Metrics */}
          {(session.distance > 0 || session.target) && (
            <div style={{ display: 'flex', gap: 14, marginTop: 18 }}>
              {session.distance > 0 && <Card style={{ flex: 1, boxShadow: 'none' }} pad={14}><Metric value={session.distance} unit="km" label="목표 거리" size={22} /></Card>}
              {session.target && <Card style={{ flex: 1, boxShadow: 'none' }} pad={14}><Metric value={session.target.split(' ')[0]} label="목표 페이스" size={22} /></Card>}
            </div>
          )}

          {/* Zone */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 16, padding: '10px 14px',
            background: `rgba(${w.rgb},0.10)`, borderRadius: 12 }}>
            <Icon name="activity" size={16} color={w.color} />
            <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, fontWeight: 600, color: w.color }}>{w.zone}</span>
            {session.focus && <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginLeft: 4 }}>· {session.focus}</span>}
          </div>

          {/* Detail blocks */}
          {session.detail && (
            <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 0, borderRadius: 16, overflow: 'hidden', background: 'var(--bg-grouped-secondary)' }}>
              {[
                { k: '워밍업', t: session.detail.warmup, ic: 'wind', c: 'var(--accent-cyan)' },
                { k: '메인 세트', t: session.detail.main, ic: w.icon, c: w.color },
                { k: '쿨다운', t: session.detail.cooldown, ic: 'droplet', c: 'var(--accent-blue)' },
              ].map((s, i, arr) => (
                <div key={i} style={{ display: 'flex', gap: 12, padding: '14px 16px', borderBottom: i < arr.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                  <span style={{ width: 28, height: 28, borderRadius: 8, background: s.c, flex: 'none', display: 'grid', placeItems: 'center' }}><Icon name={s.ic} size={14} color="#fff" strokeWidth={2.2} /></span>
                  <div><div style={{ fontFamily: 'var(--font-text)', fontSize: 12, fontWeight: 600, color: 'var(--label-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{s.k}</div>
                    <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-primary)', marginTop: 3, lineHeight: 1.4 }}>{s.t}</div></div>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, padding: '12px 16px', background: `rgba(${w.rgb},0.07)` }}>
                <Icon name="info" size={15} color={w.color} style={{ flex: 'none', marginTop: 1 }} />
                <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', lineHeight: 1.4 }}>{session.detail.note}</span>
              </div>
            </div>
          )}

          {/* Done result */}
          {session.done && session.result && (
            <div style={{ marginTop: 18 }}>
              <SectionLabel>훈련 결과</SectionLabel>
              <Card pad={16}>
                <MetricRow items={[
                  { value: session.result.distance.toFixed(2), unit: 'km', label: '거리' },
                  { value: session.result.pace, label: '페이스' },
                  { value: session.result.avgHr, label: '심박' },
                ]} size={22} />
                <div style={{ marginTop: 12, fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', lineHeight: 1.5,
                  borderTop: '0.5px solid var(--separator-non-opaque)', paddingTop: 12 }}>{session.result.note}</div>
              </Card>
            </div>
          )}

          {/* CTA if today and not done */}
          {idx === TODAY_INDEX && !session.done && session.type !== 'rest' && (
            <div style={{ marginTop: 20 }}><CTA onClick={onRecord} icon="check">다녀왔어요 · 기록 입력</CTA></div>
          )}
        </div>
      </div>
    </div>
  );
}

// Plan generation loading animation screen
function PlanGenerating({ onDone }) {
  const [step, setStep] = useStateWeek(0);
  const steps = ['지난 주 훈련 부하 분석 중…', '회복 상태 평가 중…', '페이스 구간 조정 중…', '7일 훈련 일정 구성 중…'];
  React.useEffect(() => {
    const t = setInterval(() => setStep(s => { if (s >= steps.length - 1) { clearInterval(t); setTimeout(onDone, 700); return s; } return s + 1; }), 900);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 32px', gap: 24 }}>
      <div style={{ width: 64, height: 64, borderRadius: 20, background: 'var(--tint)', display: 'grid', placeItems: 'center',
        boxShadow: '0 6px 20px rgba(0,136,255,0.30)', animation: 'spin 2s linear infinite' }}>
        <Icon name="sparkles" size={30} color="#fff" />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--label-primary)', marginBottom: 8 }}>AI 코치가 분석 중이에요</div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-secondary)', minHeight: 22, transition: 'opacity .3s' }}>{steps[step]}</div>
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        {steps.map((_, i) => <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: i <= step ? 'var(--tint)' : 'var(--fill-tertiary)', transition: 'background .3s' }} />)}
      </div>
    </div>
  );
}

// Growth report card
function GrowthReport({ onClose }) {
  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <span style={{ width: 36, height: 36, borderRadius: 11, background: 'var(--accent-indigo)', display: 'grid', placeItems: 'center' }}>
          <Icon name="award" size={19} color="#fff" />
        </span>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700, color: 'var(--label-primary)' }}>이번 주 성장 리포트</div>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)' }}>6월 1일 — 7일</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <Card style={{ flex: 1 }} pad={14}><Metric value="41.2" unit="km" label="총 거리" size={24} /></Card>
        <Card style={{ flex: 1 }} pad={14}><Metric value="5/6" label="완료 세션" size={24} /></Card>
        <Card style={{ flex: 1 }} pad={14}><Metric value="83" unit="%" label="수행률" size={24} /></Card>
      </div>
      <Card style={{ background: 'rgba(97,85,245,0.07)', boxShadow: 'none', marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <Icon name="trending-up" size={18} color="var(--accent-indigo)" style={{ flex: 'none', marginTop: 2 }} />
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-primary)', lineHeight: 1.55 }}>
            <strong>템포 런 평균 페이스가 5:12 → 5:08로 4초 개선</strong>됐어요. 심박 효율도 높아지고 있습니다. 다음 주 임계 구간을 5분 연장하는 것을 권장해요.</div>
        </div>
      </Card>
      <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-primary)', lineHeight: 1.6, marginBottom: 16, padding: '14px 16px', background: 'var(--bg-grouped-secondary)', borderRadius: 14 }}>
        <strong>다음 주 조정 사항</strong><br />
        · 총 거리 43km (+2km)<br />
        · 인터벌 400m × 6개 → 8개로 증가<br />
        · 롱런 18km → 20km (최장 거리 갱신)
      </div>
      <CTA variant="gray" icon={null} onClick={onClose}>닫기</CTA>
    </div>
  );
}

function WeekTab({ hasPlan, generating, onGenerate, onRecord, coach }) {
  const [selectedIdx, setSelectedIdx] = useStateWeek(null);
  const [showReport, setShowReport] = useStateWeek(false);

  if (generating) {
    return (
      <div>
        <NavBarLarge title="이번 주" />
        <div style={{ padding: '4px 16px 0' }}><PlanGenerating onDone={onGenerate} /></div>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <NavBarLarge title="이번 주" trailing={
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--tint)', fontFamily: 'var(--font-text)', fontSize: 17 }}>편집</button>
      } />
      <div style={{ padding: '4px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {!hasPlan ? (
          <div>
            <Card>
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <Icon name="calendar" size={40} color="var(--label-quaternary)" />
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600, color: 'var(--label-primary)', marginTop: 14 }}>아직 이번 주 계획이 없어요</div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-secondary)', marginTop: 6 }}>지난 주 데이터를 반영해 AI가 만들어 드려요</div>
              </div>
            </Card>
            <div style={{ marginTop: 14 }}><CTA onClick={onGenerate}>이번 주 계획 세우기</CTA></div>
          </div>
        ) : (
          <>
            <Card><WeekSummaryBar plan={WEEK_PLAN} /></Card>
            <div>
              <SectionLabel>7일 훈련 일정</SectionLabel>
              <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 20, overflow: 'hidden' }}>
                {WEEK_PLAN.map((s, i) => (
                  <div key={i}>
                    <DayRow session={s} idx={i} onSelect={setSelectedIdx} isToday={i === TODAY_INDEX} />
                    {i < WEEK_PLAN.length - 1 && <div style={{ height: 0.5, background: 'var(--separator-non-opaque)', marginLeft: 64 }} />}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <CTA onClick={() => setShowReport(true)}>이번 주 성장 리포트 만들기</CTA>
              <CTA variant="ghost" icon={null} onClick={() => {}}>계획 조정 요청</CTA>
            </div>

            {showReport && (
              <Card style={{ marginTop: 4 }}><GrowthReport onClose={() => setShowReport(false)} /></Card>
            )}
          </>
        )}
      </div>

      {selectedIdx !== null && (
        <SessionSheet
          session={WEEK_PLAN[selectedIdx]}
          idx={selectedIdx}
          coach={coach}
          onClose={() => setSelectedIdx(null)}
          onRecord={() => { setSelectedIdx(null); onRecord(); }}
        />
      )}
    </div>
  );
}

Object.assign(window, { WeekTab });
