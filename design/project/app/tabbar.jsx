// tabbar.jsx — floating Liquid Glass tab bar (iOS 26)
function TabBar({ tabs, active, onChange, floating = true }) {
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, paddingBottom: 0,
      display: 'flex', justifyContent: 'center', pointerEvents: 'none', zIndex: 20 }}>
      <div style={{
        pointerEvents: 'auto',
        display: 'flex', gap: 2, margin: '0 0 30px', padding: floating ? '8px 8px' : '8px 14px',
        borderRadius: 999,
        background: 'var(--glass-tab, rgba(255,255,255,0.6))',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)', backdropFilter: 'blur(20px) saturate(180%)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 28px rgba(0,0,0,0.18)',
      }}>
        {tabs.map((t) => {
          const on = t.id === active;
          return (
            <button key={t.id} onClick={() => onChange(t.id)} style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, width: 64, padding: '5px 0',
              border: 'none', background: 'none', cursor: 'pointer',
              color: on ? 'var(--tint)' : 'var(--miscellaneous-floating-tab-text-unselected, rgba(9,9,9,0.5))' }}>
              <Icon name={t.icon} size={25} color="currentColor" strokeWidth={on ? 2.3 : 2} />
              <span style={{ fontFamily: 'var(--font-text)', fontSize: 10, fontWeight: on ? 600 : 500, letterSpacing: '-0.1px' }}>{t.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

Object.assign(window, { TabBar });
