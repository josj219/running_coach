// 공용 UI — design/project/app/ui.jsx 이식 (iOS 26 + 스포티 레이어)
import React, { useEffect, useState } from 'react';
import {
  Activity, ArrowRight, Bed, Calendar, CalendarClock, CalendarDays, Camera, Check,
  ChevronDown, ChevronRight, ChevronUp, Circle, CircleAlert, CircleCheck,
  CircleDot, CircleX, Compass, Droplet, Dumbbell, Flame, Footprints, Info,
  LoaderCircle, LogOut, Mountain, Pencil, Plus, Settings, Shield, Sparkles,
  StretchHorizontal, Target, Trash2, TrendingUp, Trophy, Watch, Wind, X, Zap,
} from 'lucide-react';
import { WEEK_DAYS, wmeta } from '../workouts.js';

const ICONS = {
  Activity, ArrowRight, Bed, Calendar, CalendarClock, CalendarDays, Camera, Check,
  ChevronDown, ChevronRight, ChevronUp, Circle, CircleAlert, CircleCheck,
  CircleDot, CircleX, Compass, Droplet, Dumbbell, Flame, Footprints, Info,
  LoaderCircle, LogOut, Mountain, Pencil, Plus, Settings, Shield, Sparkles,
  StretchHorizontal, Target, Trash2, TrendingUp, Trophy, Watch, Wind, X, Zap,
};

export function Icon({ name, size = 20, color = 'currentColor', strokeWidth = 2, style }) {
  const Cmp = ICONS[name] || CircleDot;
  return <Cmp size={size} color={color} strokeWidth={strokeWidth} style={style} />;
}

export function NavBarLarge({ title, trailing }) {
  return (
    <div className="navbar-large">
      <h1>{title}</h1>
      {trailing}
    </div>
  );
}

export function SectionLabel({ children, trailing }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '0 4px 10px' }}>
      <span style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.2px', textTransform: 'uppercase', color: 'var(--label-secondary)' }}>{children}</span>
      {trailing}
    </div>
  );
}

export function Card({ children, style, onClick, pad = 16, className }) {
  const [p, setP] = useState(false);
  return (
    <div onClick={onClick} className={className}
      onPointerDown={() => onClick && setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 20, padding: pad,
        boxShadow: 'var(--card-shadow)', cursor: onClick ? 'pointer' : 'default',
        transition: 'transform .08s', transform: p ? 'scale(0.985)' : 'none', ...style }}>
      {children}
    </div>
  );
}

// 워크아웃 타입 그라데이션 히어로
export function Hero({ rgb, children, flat }) {
  return (
    <div style={{ position: 'relative', borderRadius: 26, padding: '22px 22px 24px', overflow: 'hidden',
      color: flat ? 'var(--label-primary)' : '#fff',
      background: flat ? 'var(--bg-grouped-secondary)'
        : `linear-gradient(150deg, rgba(${rgb},1) 0%, rgba(${rgb},0.82) 60%, rgba(${rgb},0.92) 100%)`,
      boxShadow: flat ? 'var(--card-shadow)' : `0 10px 30px rgba(${rgb},0.30)` }}>
      {!flat && <div style={{ position: 'absolute', right: -40, top: -40, width: 180, height: 180, borderRadius: '50%',
        background: 'rgba(255,255,255,0.14)' }} />}
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
}

export function Metric({ value, unit, label, color = 'var(--label-primary)', size = 34, align = 'flex-start' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: align, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: size, lineHeight: 1,
          letterSpacing: '-0.5px', color, fontVariantNumeric: 'tabular-nums' }}>{value}</span>
        {unit && <span style={{ fontWeight: 600, fontSize: size * 0.42, color: 'var(--label-secondary)' }}>{unit}</span>}
      </div>
      {label && <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--label-tertiary)', marginTop: 5,
        textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</span>}
    </div>
  );
}

export function MetricRow({ items, size = 26 }) {
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

// 회복 필요도 뱃지 — 백엔드 enum(low/medium/high)과 동일 키
export function RecoveryBadge({ level }) {
  const map = {
    high:   { color: 'var(--accent-red)',    bg: 'rgba(255,56,60,0.12)',  label: '회복 필요' },
    medium: { color: 'var(--accent-orange)', bg: 'rgba(255,141,40,0.14)', label: '주의' },
    low:    { color: 'var(--accent-green)',  bg: 'rgba(52,199,89,0.14)',  label: '양호' },
  };
  const m = map[level] || map.low;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: m.bg, color: m.color,
      borderRadius: 999, padding: '5px 11px 5px 9px', fontSize: 13, fontWeight: 600 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: m.color }} />{m.label}
    </span>
  );
}

export function WeekBars({ days, today = -1, accent = 'var(--tint)' }) {
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
            <span style={{ fontSize: 11, fontWeight: isToday ? 700 : 500,
              color: isToday ? 'var(--label-primary)' : 'var(--label-tertiary)' }}>{WEEK_DAYS[i]}</span>
          </div>
        );
      })}
    </div>
  );
}

export function Ring({ pct, size = 56, stroke = 6, color = 'var(--tint)', children }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: size, height: size, flex: 'none' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--fill-tertiary)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(pct, 100) / 100)}
          style={{ transition: 'stroke-dashoffset .6s cubic-bezier(.32,.72,0,1)' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}>{children}</div>
    </div>
  );
}

export function Expander({ title, icon, iconColor, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 16, overflow: 'hidden', boxShadow: 'var(--card-shadow)' }}>
      <button onClick={() => setOpen(!open)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10,
        padding: '13px 15px', border: 'none', background: 'none', cursor: 'pointer', color: 'var(--label-primary)' }}>
        {icon && <span style={{ width: 26, height: 26, borderRadius: 8, background: iconColor || 'var(--fill-secondary)',
          display: 'grid', placeItems: 'center', flex: 'none' }}><Icon name={icon} size={15} color="#fff" strokeWidth={2.2} /></span>}
        <span style={{ flex: 1, textAlign: 'left', fontSize: 15, fontWeight: 600 }}>{title}</span>
        <Icon name={open ? 'ChevronUp' : 'ChevronDown'} size={18} color="var(--label-tertiary)" strokeWidth={2.4} />
      </button>
      {open && <div style={{ padding: '0 15px 15px' }}>{children}</div>}
    </div>
  );
}

export function CTA({ children, onClick, variant = 'filled', icon = 'ArrowRight', full = true, disabled, busy }) {
  const [p, setP] = useState(false);
  const styles = {
    filled: { background: 'var(--tint)', color: '#fff', boxShadow: '0 6px 18px color-mix(in srgb, var(--tint) 38%, transparent)' },
    tinted: { background: 'var(--btn-tinted-fill)', color: 'var(--tint)' },
    gray: { background: 'var(--fill-secondary)', color: 'var(--label-primary)' },
    ghost: { background: 'transparent', color: 'var(--tint)' },
  };
  return (
    <button onClick={onClick} disabled={disabled || busy}
      onPointerDown={() => setP(true)} onPointerUp={() => setP(false)} onPointerLeave={() => setP(false)}
      style={{ width: full ? '100%' : 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
        border: 'none', cursor: disabled ? 'default' : 'pointer', borderRadius: 16, padding: '15px 20px',
        fontSize: 17, fontWeight: 600, letterSpacing: '-0.3px', transition: 'transform .08s, opacity .12s',
        opacity: disabled || busy ? 0.55 : 1, transform: p ? 'scale(0.98)' : 'none', ...styles[variant] }}>
      {busy && <Icon name="LoaderCircle" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
      {children}
      {!busy && icon && variant !== 'ghost' && <Icon name={icon} size={18} strokeWidth={2.4} />}
    </button>
  );
}

export function TypeBadge({ kind, size = 'md' }) {
  const w = wmeta(kind);
  const tile = size === 'sm' ? 26 : 32;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: tile, height: tile, borderRadius: size === 'sm' ? 8 : 10, flex: 'none',
        background: w.color, display: 'grid', placeItems: 'center', boxShadow: `0 2px 8px rgba(${w.rgb},0.35)` }}>
        <Icon name={w.icon} size={tile * 0.58} color="#fff" strokeWidth={2.2} />
      </span>
      <span style={{ fontWeight: 600, fontSize: size === 'sm' ? 15 : 17, letterSpacing: '-0.3px',
        color: 'var(--label-primary)' }}>{w.label}</span>
    </div>
  );
}

// 인라인 에러/안내 배너
export function Banner({ tone = 'info', children, action, onAction }) {
  const colors = {
    info: ['var(--accent-blue)', 'rgba(0,136,255,0.10)'],
    warn: ['var(--accent-orange)', 'rgba(255,141,40,0.12)'],
    error: ['var(--accent-red)', 'rgba(255,56,60,0.10)'],
  }[tone];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: 14,
      background: colors[1], color: colors[0], fontSize: 14, fontWeight: 500 }}>
      <Icon name={tone === 'error' ? 'CircleAlert' : 'Info'} size={17} />
      <span style={{ flex: 1, color: 'var(--label-primary)' }}>{children}</span>
      {action && <button onClick={onAction} style={{ background: 'none', border: 'none', color: colors[0],
        fontWeight: 700, fontSize: 14, cursor: 'pointer', flex: 'none' }}>{action}</button>}
    </div>
  );
}

// 중앙 모달 — 백드롭 클릭 · X 버튼 · Esc 로 닫기. locked(저장 중 등)면 닫기 잠금.
export function Modal({ title, subtitle, onClose, locked = false, children, width = 560 }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !locked) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [locked, onClose]);
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 50, display: 'grid', placeItems: 'center',
      background: 'rgba(0,0,0,0.45)', padding: 16 }}
      onClick={(e) => e.target === e.currentTarget && !locked && onClose()}>
      <div className="modal-card" style={{ background: 'var(--bg-grouped-primary)', borderRadius: 24,
        width: `min(${width}px, 100%)`, maxHeight: '90%', display: 'flex', flexDirection: 'column',
        boxShadow: '0 16px 48px rgba(0,0,0,0.35)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px 13px', display: 'flex', alignItems: 'center', gap: 12,
          flex: 'none', borderBottom: '0.5px solid var(--separator-non-opaque)' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700,
              color: 'var(--label-primary)' }}>{title}</div>
            {subtitle && <div style={{ fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>{subtitle}</div>}
          </div>
          {!locked && (
            <button onClick={onClose} aria-label="닫기"
              style={{ background: 'var(--fill-tertiary)', border: 'none', width: 32, height: 32,
                borderRadius: '50%', cursor: 'pointer', display: 'grid', placeItems: 'center', flex: 'none' }}>
              <Icon name="X" size={17} color="var(--label-secondary)" strokeWidth={2.4} />
            </button>
          )}
        </div>
        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>{children}</div>
      </div>
    </div>
  );
}

export function Spinner({ label }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '48px 0' }}>
      <div style={{ width: 44, height: 44, borderRadius: 14, background: 'var(--tint)', display: 'grid',
        placeItems: 'center', animation: 'spin 1.2s linear infinite',
        boxShadow: '0 6px 20px color-mix(in srgb, var(--tint) 35%, transparent)' }}>
        <Icon name="Sparkles" size={22} color="#fff" />
      </div>
      {label && <div style={{ fontSize: 15, color: 'var(--label-secondary)' }}>{label}</div>}
    </div>
  );
}
