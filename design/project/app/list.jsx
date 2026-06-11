// list.jsx — inset grouped table view (rows, groups, headers/footers)
function ListSection({ header, footer, children, style }) {
  const rows = React.Children.toArray(children).filter(Boolean);
  return (
    <div style={{ margin: '0 16px 22px', ...style }}>
      {header && (
        <div style={{ padding: '0 16px 7px', fontFamily: 'var(--font-text)', fontSize: 13,
          color: 'var(--label-secondary)', textTransform: 'uppercase', letterSpacing: '0.2px' }}>{header}</div>
      )}
      <div style={{ background: 'var(--bg-grouped-secondary)', borderRadius: 12, overflow: 'hidden' }}>
        {rows.map((r, i) => (
          <div key={i}>
            {r}
            {i < rows.length - 1 && <div style={{ height: 0.5, background: 'var(--separator-non-opaque)', marginLeft: r.props && r.props.icon ? 55 : 16 }} />}
          </div>
        ))}
      </div>
      {footer && (
        <div style={{ padding: '7px 16px 0', fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)' }}>{footer}</div>
      )}
    </div>
  );
}

function Row({ icon, iconColor, title, subtitle, value, accessory = 'none', onClick, control, titleColor, danger }) {
  const clickable = !!onClick;
  const [pressed, setPressed] = React.useState(false);
  return (
    <div onClick={onClick}
      onPointerDown={() => clickable && setPressed(true)}
      onPointerUp={() => setPressed(false)} onPointerLeave={() => setPressed(false)}
      style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0 14px', minHeight: 44,
        cursor: clickable ? 'pointer' : 'default', background: pressed ? 'var(--fill-quaternary)' : 'transparent' }}>
      {icon && <IconTile name={icon} color={iconColor || 'var(--accent-blue)'} />}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '8px 0', minWidth: 0 }}>
        <span style={{ fontFamily: 'var(--font-text)', fontSize: 17, letterSpacing: '-0.4px',
          color: danger ? 'var(--accent-red)' : (titleColor || 'var(--label-primary)'),
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span>
        {subtitle && <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)', marginTop: 1 }}>{subtitle}</span>}
      </div>
      {value && <span style={{ fontFamily: 'var(--font-text)', fontSize: 17, color: 'var(--label-secondary)', flex: 'none' }}>{value}</span>}
      {control}
      {accessory === 'disclosure' && <Icon name="chevron-right" size={17} color="var(--label-tertiary)" strokeWidth={2.6} />}
      {accessory === 'check' && <Icon name="check" size={20} color="var(--tint)" strokeWidth={2.6} />}
    </div>
  );
}

Object.assign(window, { ListSection, Row });
