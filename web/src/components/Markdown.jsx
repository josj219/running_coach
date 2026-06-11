// 마크다운 라이트 렌더러 — AI 응답(당일 카드 detail, 성장 리포트 detail_md) 전용.
// 외부 라이브러리 없이 헤딩/불릿/표/**볼드**/단락만 지원한다.
import React from 'react';

function Inline({ text }) {
  const parts = String(text).split(/\*\*(.+?)\*\*/g);
  return parts.map((p, i) => (i % 2 ? <b key={i} style={{ color: 'var(--label-primary)' }}>{p}</b> : p));
}

function Table({ rows }) {
  const cells = rows
    .map((r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()))
    .filter((cols) => !cols.every((c) => /^:?-{2,}:?$/.test(c)));
  if (!cells.length) return null;
  const [head, ...body] = cells;
  const cellStyle = { padding: '7px 10px', fontSize: 13.5, textAlign: 'left', lineHeight: 1.4 };
  return (
    <table style={{ borderCollapse: 'collapse', width: '100%', margin: '8px 0' }}>
      <thead><tr>
        {head.map((c, i) => <th key={i} style={{ ...cellStyle, fontWeight: 700,
          color: 'var(--label-secondary)', borderBottom: '1px solid var(--separator-non-opaque)' }}>
          <Inline text={c} /></th>)}
      </tr></thead>
      <tbody>
        {body.map((row, i) => (
          <tr key={i}>
            {row.map((c, j) => <td key={j} style={{ ...cellStyle, color: 'var(--label-primary)',
              borderBottom: i < body.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
              <Inline text={c} /></td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Markdown({ text, style }) {
  if (!text) return null;
  const lines = String(text).split('\n');
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) { i += 1; continue; }
    if (line.startsWith('|')) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(lines[i].trim()); i += 1; }
      blocks.push({ t: 'table', rows });
      continue;
    }
    if (/^#{1,6}\s/.test(line)) {
      blocks.push({ t: 'h', text: line.replace(/^#{1,6}\s*/, '') });
    } else if (/^[-•*]\s/.test(line)) {
      blocks.push({ t: 'li', text: line.replace(/^[-•*]\s*/, '') });
    } else {
      blocks.push({ t: 'p', text: line });
    }
    i += 1;
  }
  return (
    <div style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--label-secondary)', ...style }}>
      {blocks.map((b, k) => {
        if (b.t === 'table') return <Table key={k} rows={b.rows} />;
        if (b.t === 'h') return (
          <div key={k} style={{ fontSize: 13, fontWeight: 700, color: 'var(--label-primary)',
            margin: '14px 0 4px', letterSpacing: '0.2px' }}><Inline text={b.text} /></div>
        );
        if (b.t === 'li') return (
          <div key={k} style={{ display: 'flex', gap: 8, margin: '3px 0' }}>
            <span style={{ flex: 'none', width: 4, height: 4, borderRadius: '50%',
              background: 'var(--label-tertiary)', marginTop: 8 }} />
            <span style={{ flex: 1 }}><Inline text={b.text} /></span>
          </div>
        );
        return <div key={k} style={{ margin: '4px 0' }}><Inline text={b.text} /></div>;
      })}
    </div>
  );
}
