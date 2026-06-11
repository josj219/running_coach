// chrome.jsx — iPhone frame, status bar, navigation bars, home indicator
const { useState } = React;

// ---- Status Bar (iPhone, Dynamic Island notch) ----
function StatusBar({ dark = false, time = '9:41' }) {
  const fg = dark ? '#fff' : '#000';
  return (
    <div style={{
      height: 54, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
      padding: '0 0 0 0', position: 'relative', flex: 'none', userSelect: 'none',
    }}>
      <div style={{ width: 120, paddingLeft: 32, paddingBottom: 10 }}>
        <span style={{ color: fg, fontFamily: 'var(--font-text)', fontSize: 17, fontWeight: 600, letterSpacing: '-0.2px' }}>{time}</span>
      </div>
      {/* Dynamic Island */}
      <div style={{ position: 'absolute', left: '50%', top: 12, transform: 'translateX(-50%)',
        width: 126, height: 37, borderRadius: 20, background: '#000' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, paddingRight: 30, paddingBottom: 11 }}>
        <Icon name="cellular" size={18} color={fg} strokeWidth={2.4} />
        <Icon name="wifi" size={18} color={fg} strokeWidth={2.2} />
        <div style={{ position: 'relative', width: 26, height: 13 }}>
          <div style={{ position: 'absolute', inset: 0, border: `1.2px solid ${fg}`, opacity: 0.4, borderRadius: 4 }} />
          <div style={{ position: 'absolute', left: 2, top: 2, bottom: 2, width: 16, background: fg, borderRadius: 2 }} />
          <div style={{ position: 'absolute', right: -2.5, top: 4.5, width: 1.6, height: 4, background: fg, opacity: 0.4, borderRadius: 2 }} />
        </div>
      </div>
    </div>
  );
}

// ---- Home Indicator ----
function HomeIndicator({ dark = false }) {
  return (
    <div style={{ height: 34, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', flex: 'none' }}>
      <div style={{ width: 140, height: 5, borderRadius: 3, marginBottom: 8,
        background: dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.85)' }} />
    </div>
  );
}

// ---- iPhone hardware frame ----
function IPhoneFrame({ children, dark = false }) {
  return (
    <div style={{
      width: 393, height: 852, borderRadius: 56, padding: 0, position: 'relative',
      background: 'var(--bg-primary)', boxShadow: '0 2px 6px rgba(0,0,0,0.18), 0 30px 70px rgba(0,0,0,0.30)',
      outline: '11px solid #1b1b1d', outlineOffset: 0, overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }} className={dark ? 'dark' : ''}>
      {children}
    </div>
  );
}

// ---- Large-title navigation bar (scrolls into inline) ----
function NavBarLarge({ title, trailing, leading, collapsed = false }) {
  return (
    <div style={{ flex: 'none', background: 'transparent', paddingBottom: collapsed ? 0 : 4 }}>
      <div style={{ height: 44, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 8px' }}>
        <div style={{ minWidth: 70, display: 'flex', justifyContent: 'flex-start' }}>{leading}</div>
        <span style={{ fontFamily: 'var(--font-text)', fontSize: 17, fontWeight: 600, color: 'var(--label-primary)',
          opacity: collapsed ? 1 : 0, transition: 'opacity .2s' }}>{title}</span>
        <div style={{ minWidth: 70, display: 'flex', justifyContent: 'flex-end' }}>{trailing}</div>
      </div>
      {!collapsed && (
        <div style={{ padding: '0 16px 6px' }}>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: 34, lineHeight: '41px',
            fontWeight: 700, letterSpacing: '0.37px', color: 'var(--label-primary)' }}>{title}</h1>
        </div>
      )}
    </div>
  );
}

// ---- Inline navigation bar (with back button) ----
function NavBarInline({ title, backTitle = 'Back', onBack, trailing }) {
  return (
    <div style={{ height: 44, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 6px' }}>
      <button onClick={onBack} style={{ display: 'flex', alignItems: 'center', gap: 1, background: 'none', border: 'none',
        color: 'var(--tint)', cursor: 'pointer', fontFamily: 'var(--font-text)', fontSize: 17, padding: '4px 4px' }}>
        <Icon name="chevron-left" size={24} color="var(--tint)" strokeWidth={2.6} />
        <span style={{ marginLeft: -2 }}>{backTitle}</span>
      </button>
      <span style={{ fontFamily: 'var(--font-text)', fontSize: 17, fontWeight: 600, color: 'var(--label-primary)' }}>{title}</span>
      <div style={{ minWidth: 60, display: 'flex', justifyContent: 'flex-end', paddingRight: 6 }}>{trailing}</div>
    </div>
  );
}

Object.assign(window, { StatusBar, HomeIndicator, IPhoneFrame, NavBarLarge, NavBarInline });
