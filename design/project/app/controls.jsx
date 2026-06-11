// controls.jsx — interactive iOS controls
const { useState: useStateC } = React;

function Toggle({ value, onChange }) {
  return (
    <button onClick={() => onChange && onChange(!value)} style={{
      width: 51, height: 31, borderRadius: 999, border: 'none', cursor: 'pointer', padding: 0, flex: 'none',
      background: value ? 'var(--accent-green)' : 'var(--fill-secondary)', position: 'relative',
      transition: 'background .2s',
    }}>
      <span style={{ position: 'absolute', top: 2, left: value ? 22 : 2, width: 27, height: 27, borderRadius: '50%',
        background: '#fff', boxShadow: '0 3px 8px rgba(0,0,0,0.15), 0 1px 1px rgba(0,0,0,0.16)', transition: 'left .22s cubic-bezier(.4,0,.2,1)' }} />
    </button>
  );
}

function SegmentedControl({ options, value, onChange }) {
  return (
    <div style={{ display: 'flex', background: 'var(--fill-tertiary)', borderRadius: 9, padding: 2, position: 'relative' }}>
      {options.map((o) => {
        const on = o === value;
        return (
          <button key={o} onClick={() => onChange && onChange(o)} style={{
            flex: 1, border: 'none', cursor: 'pointer', padding: '6px 14px', borderRadius: 7,
            fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: on ? 600 : 500, whiteSpace: 'nowrap',
            color: 'var(--label-primary)', background: on ? 'var(--bg-primary)' : 'transparent',
            boxShadow: on ? '0 1px 3px rgba(0,0,0,0.12), 0 0 0 0.5px rgba(0,0,0,0.04)' : 'none', transition: 'all .15s',
          }}>{o}</button>
        );
      })}
    </div>
  );
}

function Slider({ value = 0.5, onChange, tint = 'var(--accent-blue)', leadingIcon, trailingIcon }) {
  const ref = React.useRef(null);
  const set = (clientX) => {
    const el = ref.current; if (!el) return;
    const r = el.getBoundingClientRect();
    const v = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    onChange && onChange(v);
  };
  const down = (e) => {
    set(e.clientX);
    const move = (ev) => set(ev.clientX);
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {leadingIcon && <Icon name={leadingIcon} size={18} color="var(--label-secondary)" />}
      <div ref={ref} onPointerDown={down} style={{ flex: 1, height: 28, display: 'flex', alignItems: 'center', cursor: 'pointer', touchAction: 'none' }}>
        <div style={{ position: 'relative', width: '100%', height: 4, borderRadius: 2, background: 'var(--fill-secondary)' }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: (value * 100) + '%', background: tint, borderRadius: 2 }} />
          <div style={{ position: 'absolute', left: 'calc(' + (value * 100) + '% )', top: '50%', transform: 'translate(-50%,-50%)',
            width: 27, height: 27, borderRadius: '50%', background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.28), 0 0 0 0.5px rgba(0,0,0,0.04)' }} />
        </div>
      </div>
      {trailingIcon && <Icon name={trailingIcon} size={22} color="var(--label-secondary)" />}
    </div>
  );
}

function Button({ children, variant = 'filled', size = 'md', onClick, full, style }) {
  const base = {
    fontFamily: 'var(--font-text)', fontWeight: 600, border: 'none', cursor: 'pointer',
    borderRadius: 999, letterSpacing: '-0.4px', WebkitAppearance: 'none', whiteSpace: 'nowrap',
    fontSize: size === 'sm' ? 15 : 17, padding: size === 'sm' ? '7px 14px' : '12px 20px',
    width: full ? '100%' : 'auto', transition: 'filter .12s, transform .06s',
  };
  const variants = {
    filled: { background: 'var(--tint)', color: '#fff' },
    tinted: { background: 'var(--btn-tinted-fill)', color: 'var(--tint)' },
    gray: { background: 'var(--fill-secondary)', color: 'var(--tint)' },
    plain: { background: 'none', color: 'var(--tint)', padding: size === 'sm' ? '7px 8px' : '12px 10px' },
    destructive: { background: 'var(--accent-red)', color: '#fff' },
  };
  return (
    <button onClick={onClick}
      onPointerDown={(e) => e.currentTarget.style.transform = 'scale(0.97)'}
      onPointerUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
      onPointerLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
      style={{ ...base, ...variants[variant], ...style }}>{children}</button>
  );
}

function SearchField({ value, onChange, placeholder = 'Search' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--fill-tertiary)',
      borderRadius: 10, padding: '8px 10px' }}>
      <Icon name="search" size={18} color="var(--label-tertiary)" strokeWidth={2.4} />
      <input value={value} onChange={(e) => onChange && onChange(e.target.value)} placeholder={placeholder}
        style={{ border: 'none', outline: 'none', background: 'none', flex: 1, fontFamily: 'var(--font-text)',
          fontSize: 17, color: 'var(--label-primary)' }} />
    </div>
  );
}

function IconTile({ name, color, size = 29 }) {
  return (
    <span style={{ width: size, height: size, borderRadius: 7, background: color, display: 'grid',
      placeItems: 'center', flex: 'none' }}>
      <Icon name={name} size={size * 0.62} color="#fff" strokeWidth={2.1} />
    </span>
  );
}

Object.assign(window, { Toggle, SegmentedControl, Slider, Button, SearchField, IconTile });
