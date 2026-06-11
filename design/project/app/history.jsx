// history.jsx — 기록 탭: 최근 러닝 + 주간 통계
const { useState: useStateHistory } = React;

const TYPE_COLORS = {
  easy: 'var(--accent-green)', interval: 'var(--accent-pink)',
  tempo: 'var(--accent-orange)', long: 'var(--accent-indigo)',
  rest: 'var(--gray)', strength: 'var(--accent-teal)',
};
const TYPE_RGB = {
  easy: '52,199,89', interval: '255,45,85',
  tempo: '255,141,40', long: '97,85,245',
  rest: '142,142,147', strength: '0,195,208',
};

function RunCard({ run }) {
  const w = WORKOUT_TYPES[run.type];
  const [p, setP] = useStateHistory(false);
  return (
    <div onPointerDown={() => setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      style={{ display: 'flex', gap: 14, padding: '14px 16px', cursor: 'pointer',
        background: p ? 'var(--fill-quaternary)' : 'transparent' }}>
      <span style={{ width: 44, height: 44, borderRadius: 13, background: w.color, flex: 'none',
        display: 'grid', placeItems: 'center', boxShadow: `0 3px 10px rgba(${w.rgb},0.30)` }}>
        <Icon name={w.icon} size={22} color="#fff" strokeWidth={2.1} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'var(--font-text)', fontWeight: 600, fontSize: 16,
            color: 'var(--label-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.label}</span>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17,
            color: 'var(--label-primary)', fontVariantNumeric: 'tabular-nums', flex: 'none', marginLeft: 8 }}>
            {run.distance.toFixed(1)} km</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 3 }}>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)' }}>{run.date}</span>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-tertiary)' }}>
            {run.pace}/km · {run.min}분
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
          <Icon name="activity" size={13} color="var(--label-tertiary)" />
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-tertiary)' }}>
            평균 심박 {run.avgHr} bpm
          </span>
        </div>
      </div>
      <Icon name="chevron-right" size={16} color="var(--label-quaternary)" strokeWidth={2.4} style={{ alignSelf: 'center', flex: 'none' }} />
    </div>
  );
}

function WeekHistoryRow({ week, onSelect }) {
  const [p, setP] = useStateHistory(false);
  const color = week.current ? 'var(--tint)' : 'var(--accent-green)';
  return (
    <div onPointerDown={() => setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      onClick={onSelect} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px', cursor: 'pointer',
        background: p ? 'var(--fill-quaternary)' : 'transparent' }}>
      <Ring pct={week.completion} size={44} stroke={4} color={color}>
        <span style={{ fontFamily: 'var(--font-text)', fontSize: 9, fontWeight: 700, color }}>{week.completion}%</span>
      </Ring>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-text)', fontWeight: 600, fontSize: 16, color: 'var(--label-primary)' }}>{week.label}</span>
          {week.current && <span style={{ fontFamily: 'var(--font-text)', fontSize: 11, fontWeight: 700, background: 'var(--tint)',
            color: '#fff', borderRadius: 999, padding: '2px 7px' }}>진행 중</span>}
        </div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>
          {week.sessions} 세션 완료 · {week.km} km
        </div>
      </div>
      <Icon name="chevron-right" size={16} color="var(--label-quaternary)" strokeWidth={2.4} />
    </div>
  );
}

// 4-week trend mini bars
function TrendBars({ data }) {
  const max = Math.max(...data, 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 48 }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{ width: '100%', maxWidth: 32, height: Math.max(4, (v / max) * 44), borderRadius: 6,
            background: i === data.length - 1 ? 'var(--tint)' : `color-mix(in srgb, var(--tint) 28%, transparent)` }} />
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 10, color: 'var(--label-tertiary)', fontWeight: i === data.length - 1 ? 700 : 400 }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function HistoryTab({ density }) {
  const [view, setView] = useStateHistory('runs'); // 'runs' | 'weeks'
  const weekKms = HISTORY_WEEKS.slice().reverse().map(w => w.km);

  return (
    <div>
      <NavBarLarge title="기록" trailing={
        <button style={{ background: 'none', border: 'none', color: 'var(--tint)', fontSize: 17,
          fontFamily: 'var(--font-text)', cursor: 'pointer', padding: '0 6px' }}>필터</button>
      } />
      <div style={{ padding: '4px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* 총 통계 */}
        <Card pad={18}>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)',
            textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 14 }}>최근 4주</div>
          <div style={{ display: 'flex', gap: 0, marginBottom: 16 }}>
            <div style={{ flex: 1 }}><Metric value="143.5" unit="km" label="누적 거리" size={26} /></div>
            <div style={{ flex: 1 }}><Metric value="18" label="세션 완료" size={26} /></div>
            {density !== 'core' && <div style={{ flex: 1 }}><Metric value="5:52" label="평균 페이스" size={26} /></div>}
          </div>
          <TrendBars data={weekKms} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
            {HISTORY_WEEKS.slice().reverse().map((w, i) => (
              <span key={i} style={{ flex: 1, textAlign: 'center', fontFamily: 'var(--font-text)', fontSize: 10,
                color: i === weekKms.length - 1 ? 'var(--label-secondary)' : 'var(--label-quaternary)' }}>{w.label.replace('주 전','주전').replace('이번 주','이번')}</span>
            ))}
          </div>
        </Card>

        {/* Segment toggle */}
        <SegmentedControl options={['러닝 기록', '주간 통계']}
          value={view === 'runs' ? '러닝 기록' : '주간 통계'}
          onChange={v => setView(v === '러닝 기록' ? 'runs' : 'weeks')} />

        {/* Content */}
        {view === 'runs' ? (
          <div>
            <SectionLabel>최근 러닝</SectionLabel>
            <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 20, overflow: 'hidden' }}>
              {RECENT_RUNS.map((r, i) => (
                <div key={i}>
                  <RunCard run={r} />
                  {i < RECENT_RUNS.length - 1 && <div style={{ height: 0.5, background: 'var(--separator-non-opaque)', marginLeft: 74 }} />}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div>
            <SectionLabel>주간 통계</SectionLabel>
            <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 20, overflow: 'hidden' }}>
              {HISTORY_WEEKS.map((w, i) => (
                <div key={i}>
                  <WeekHistoryRow week={w} onSelect={() => {}} />
                  {i < HISTORY_WEEKS.length - 1 && <div style={{ height: 0.5, background: 'var(--separator-non-opaque)', marginLeft: 72 }} />}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { HistoryTab });
