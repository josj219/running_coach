// 로그인 화면 — 이메일+비밀번호. 계정은 서버에서 생성(셀프 회원가입 없음).
import React, { useState } from 'react';
import { api, setToken } from './api.js';
import { Banner, CTA, Icon } from './components/Ui.jsx';

const inputStyle = {
  width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
  borderRadius: 12, padding: '13px 15px', fontSize: 16, color: 'var(--label-primary)',
};

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e?.preventDefault();
    if (!email.trim() || !password) { setError('이메일과 비밀번호를 입력해주세요.'); return; }
    setBusy(true); setError(null);
    try {
      const r = await api.login(email.trim(), password);
      setToken(r.token);
      onLoggedIn(r.user);
    } catch (err) {
      setError(err.message || '로그인에 실패했어요.');
      setBusy(false);
    }
  };

  return (
    <div className="app-frame">
      <div className="scroll-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '0 24px', minHeight: '100%' }}>
        <div className="anim-in" style={{ maxWidth: 420, width: '100%', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <span style={{ width: 64, height: 64, borderRadius: 18, display: 'inline-grid', placeItems: 'center',
              background: 'linear-gradient(135deg, var(--tint), var(--accent-indigo))', marginBottom: 14 }}>
              <Icon name="Footprints" size={32} color="#fff" />
            </span>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 800, margin: 0 }}>러닝 코치</h1>
            <p style={{ fontSize: 14.5, color: 'var(--label-secondary)', marginTop: 6 }}>로그인하고 코칭을 시작하세요</p>
          </div>

          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input type="email" inputMode="email" autoComplete="username" placeholder="이메일"
              value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
            <input type="password" autoComplete="current-password" placeholder="비밀번호"
              value={password} onChange={(e) => setPassword(e.target.value)} style={inputStyle} />
            {error && <Banner tone="error">{error}</Banner>}
            <div style={{ marginTop: 6 }}>
              <CTA icon={null} busy={busy} onClick={submit}>로그인</CTA>
            </div>
          </form>

          <p style={{ fontSize: 12.5, color: 'var(--label-tertiary)', textAlign: 'center', marginTop: 18, lineHeight: 1.5 }}>
            계정이 없나요? 관리자에게 계정 생성을 요청하세요.
          </p>
        </div>
      </div>
    </div>
  );
}
