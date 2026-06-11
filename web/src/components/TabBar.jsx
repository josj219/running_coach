// 플로팅 글래스 탭바 — iOS 26 Liquid Glass 근사
import React from 'react';
import { Icon } from './Ui.jsx';

export default function TabBar({ tabs, active, onChange }) {
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, display: 'flex', justifyContent: 'center',
      padding: `0 16px calc(14px + env(safe-area-inset-bottom))`, pointerEvents: 'none', zIndex: 40 }}>
      <div style={{ display: 'flex', gap: 4, padding: 6, borderRadius: 999, pointerEvents: 'auto',
        background: 'var(--glass-tint)', backdropFilter: 'blur(14px) saturate(180%)',
        WebkitBackdropFilter: 'blur(14px) saturate(180%)',
        boxShadow: '0 6px 24px rgba(0,0,0,0.16), inset 0 1px 0 var(--glass-edge)' }}>
        {tabs.map((t) => {
          const on = t.id === active;
          return (
            <button key={t.id} onClick={() => onChange(t.id)}
              aria-label={t.label}
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                minWidth: 72, padding: '8px 10px', borderRadius: 999, border: 'none', cursor: 'pointer',
                background: on ? 'var(--tint)' : 'transparent', transition: 'background .18s',
                color: on ? '#fff' : 'var(--label-secondary)' }}>
              <Icon name={t.icon} size={21} strokeWidth={on ? 2.4 : 2} />
              <span style={{ fontSize: 11, fontWeight: on ? 700 : 500 }}>{t.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
