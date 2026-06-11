// ui.jsx — sporty visual layer on top of the iOS 26 primitives
// Big tabular numbers, workout-type badges, glass hero, mini charts.
const { useState: useStateUI } = React;

// Section title used inside scroll views (sentence-ish, bold)
function SectionLabel({ children, trailing }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '0 4px 10px' }}>
      <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, letterSpacing: '0.2px',
        textTransform: 'uppercase', color: 'var(--label-secondary)' }}>{children}</span>
      {trailing}
    </div>
  );
}

// White content card
function Card({ children, style, onClick, pad = 16 }) {
  const [p, setP] = useStateUI(false);
  return (
    <div onClick={onClick}
      onPointerDown={() => onClick && setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 20, padding: pad,
        boxShadow: '0 1px 2px rgba(0,0,0,0.05), 0 6px 18px rgba(0,0,0,0.05)',
        cursor: onClick ? 'pointer' : 'default', transition: 'transform .08s', transform: p ? 'scale(0.985)' : 'none', ...style }}>
      {children}
    </div>
  );
}

// Workout-type pill badge (icon tile + label)
function TypeBadge({ type, size = 'md' }) {
  const w = WORKOUT_TYPES[type];
  const tile = size === 'sm' ? 26 : 32;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: tile, height: tile, borderRadius: size === 'sm' ? 8 : 10, flex: 'none',
        background: w.color, display: 'grid', placeItems: 'center',
        boxShadow: `0 2px 8px rgba(${w.rgb},0.35)` }}>
        <Icon name={w.icon} size={tile * 0.58} color="#fff" strokeWidth={2.2} />
      </span>
      <span style={{ fontFamily: 'var(--font-text)', fontWeight: 600, fontSize: size === 'sm' ? 15 : 17,
        letterSpacing: '-0.3px', color: 'var(--label-primary)' }}>{w.label}</span>
    </div>
  );
}

// Big tabular metric: value + unit + caption
function Metric({ value, unit, label, color = 'var(--label-primary)', size = 34, align = 'flex-start' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: align, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: size, lineHeight: 1,
          letterSpacing: '-0.5px', color, fontVariantNumeric: 'tabular-nums' }}>{value}</span>
        {unit && <span style={{ fontFamily: 'var(--font-text)', fontWeight: 600, fontSize: size * 0.42,
          color: 'var(--label-secondary)' }}>{unit}</span>}
      </div>
      {label && <span style={{ fontFamily: 'var(--font-text)', fontSize: 12, fontWeight: 500,
        color: 'var(--label-tertiary)', marginTop: 5, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</span>}
    </div>
  );
}

// Row of metrics separated by hairlines
function MetricRow({ items, size = 26 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      {items.map((m, i) => (
        <React.Fragment key={i}>
          {i > 0 && <div style={{ width: 0.5, alignSelf: 'stretch', background: 'var(--separator-non-opaque)', margin: '4px 0' }} />}
          <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: '0 4px' }}>
            <Metric value={m.value} unit={m.unit} label={m.label} size={size} align="center" color={m.color} />
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

// Recovery / readiness badge dot
function RecoveryBadge({ level }) {
  const map = {
    high:   { color: 'var(--accent-red)',    bg: 'rgba(255,56,60,0.12)',  label: '회복 필요' },
    medium: { color: 'var(--accent-orange)', bg: 'rgba(255,141,40,0.14)', label: '주의' },
    low:    { color: 'var(--accent-green)',  bg: 'rgba(52,199,89,0.14)',  label: '양호' },
  };
  const m = map[level] || map.low;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: m.bg, color: m.color,
      borderRadius: 999, padding: '5px 11px 5px 9px', fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: m.color }} />{m.label}
    </span>
  );
}

// Vertical bar chart of weekly distance (data-density aware via showHr unused)
function WeekBars({ days, today = -1, accent = 'var(--tint)' }) {
  const max = Math.max(...days, 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 88 }}>
      {days.map((d, i) => {
        const h = d === 0 ? 4 : Math.max(8, (d / max) * 84);
        const isToday = i === today;
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <div style={{ width: '100%', maxWidth: 26, height: h, borderRadius: 7,
              background: d === 0 ? 'var(--fill-tertiary)' : (isToday ? accent : `color-mix(in srgb, ${accent} 30%, transparent)`),
              transition: 'height .4s cubic-bezier(.32,.72,0,1)' }} />
            <span style={{ fontFamily: 'var(--font-text)', fontSize: 11, fontWeight: isToday ? 700 : 500,
              color: isToday ? 'var(--label-primary)' : 'var(--label-tertiary)' }}>{WEEK_DAYS[i]}</span>
          </div>
        );
      })}
    </div>
  );
}

// Progress ring (completion %)
function Ring({ pct, size = 56, stroke = 6, color = 'var(--tint)', children }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: size, height: size, flex: 'none' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--fill-tertiary)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)}
          style={{ transition: 'stroke-dashoffset .6s cubic-bezier(.32,.72,0,1)' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}>{children}</div>
    </div>
  );
}

// Collapsible expander
function Expander({ title, icon, iconColor, defaultOpen = false, children }) {
  const [open, setOpen] = useStateUI(defaultOpen);
  return (
    <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 16, overflow: 'hidden' }}>
      <button onClick={() => setOpen(!open)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10,
        padding: '13px 15px', border: 'none', background: 'none', cursor: 'pointer' }}>
        {icon && <span style={{ width: 26, height: 26, borderRadius: 8, background: iconColor || 'var(--fill-secondary)',
          display: 'grid', placeItems: 'center', flex: 'none' }}><Icon name={icon} size={15} color="#fff" strokeWidth={2.2} /></span>}
        <span style={{ flex: 1, textAlign: 'left', fontFamily: 'var(--font-text)', fontSize: 15, fontWeight: 600,
          color: 'var(--label-primary)' }}>{title}</span>
        <Icon name={open ? 'chevron-up' : 'chevron-down'} size={18} color="var(--label-tertiary)" strokeWidth={2.4} />
      </button>
      {open && <div style={{ padding: '0 15px 15px' }}>{children}</div>}
    </div>
  );
}

// Big primary CTA with arrow
function CTA({ children, onClick, variant = 'filled', icon = 'arrow-right', full = true }) {
  const [p, setP] = useStateUI(false);
  const styles = {
    filled: { background: 'var(--tint)', color: '#fff', boxShadow: '0 6px 18px color-mix(in srgb, var(--tint) 38%, transparent)' },
    tinted: { background: 'var(--btn-tinted-fill)', color: 'var(--tint)' },
    gray: { background: 'var(--fill-secondary)', color: 'var(--label-primary)' },
    ghost: { background: 'transparent', color: 'var(--tint)' },
  };
  return (
    <button onClick={onClick}
      onPointerDown={() => setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      style={{ width: full ? '100%' : 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
        border: 'none', cursor: 'pointer', borderRadius: 16, padding: '15px 20px', fontFamily: 'var(--font-text)',
        fontSize: 17, fontWeight: 600, letterSpacing: '-0.3px', transition: 'transform .08s, filter .12s',
        transform: p ? 'scale(0.98)' : 'none', ...styles[variant] }}>
      {children}
      {icon && variant !== 'ghost' && <Icon name={icon} size={18} color="currentColor" strokeWidth={2.4} />}
    </button>
  );
}

Object.assign(window, { SectionLabel, Card, TypeBadge, Metric, MetricRow, RecoveryBadge, WeekBars, Ring, Expander, CTA });
