// 비밀번호 재설정 — 1) 이메일로 6자리 인증 코드 받기 → 2) 코드 + 새 비밀번호 입력 → 바로 로그인.
import React, { useState } from 'react';
import { api, setToken } from './api.js';
import { Banner, CTA, Icon, inputStyle } from './components/Ui.jsx';

const RESEND_COOLDOWN_S = 60; // 서버 쿨다운과 동일

export default function ForgotPassword({ initialEmail = '', onBack, onLoggedIn }) {
  const [step, setStep] = useState('email');  // email | code
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const startCooldown = () => {
    setCooldown(RESEND_COOLDOWN_S);
    const t = setInterval(() => setCooldown((c) => { if (c <= 1) { clearInterval(t); return 0; } return c - 1; }), 1000);
  };

  const sendCode = async (e) => {
    e?.preventDefault();
    const em = email.trim();
    if (!em) { setError('이메일을 입력해주세요.'); return; }
    setBusy(true); setError(null); setNotice(null);
    try {
      await api.forgotPassword(em);
      setStep('code');
      setNotice('등록된 이메일이면 인증 코드를 보냈어요. 메일함(스팸함 포함)을 확인해주세요.');
      startCooldown();
    } catch (err) {
      setError(err.message || '코드를 보내지 못했어요.');
    } finally {
      setBusy(false);
    }
  };

  const reset = async (e) => {
    e?.preventDefault();
    if (code.trim().length !== 6) { setError('6자리 인증 코드를 입력해주세요.'); return; }
    if (pw.length < 8) { setError('새 비밀번호는 8자 이상이어야 해요.'); return; }
    if (pw !== pw2) { setError('비밀번호 확인이 일치하지 않아요.'); return; }
    setBusy(true); setError(null);
    try {
      const r = await api.resetPassword(email.trim(), code.trim(), pw);
      setToken(r.token);
      onLoggedIn(r.user);
    } catch (err) {
      setError(err.message || '비밀번호를 바꾸지 못했어요.');
      setBusy(false);
    }
  };

  return (
    <div className="app-frame">
      <div className="scroll-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '0 24px', minHeight: '100%' }}>
        <div className="anim-in" style={{ maxWidth: 420, width: '100%', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <span style={{ width: 64, height: 64, borderRadius: 18, display: 'inline-grid', placeItems: 'center',
              background: 'var(--fill-secondary)', marginBottom: 14 }}>
              <Icon name="KeyRound" size={30} color="var(--tint)" />
            </span>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 800, margin: 0 }}>비밀번호 재설정</h1>
            <p style={{ fontSize: 14.5, color: 'var(--label-secondary)', marginTop: 6, lineHeight: 1.5 }}>
              {step === 'email'
                ? '계정 이메일을 입력하면 인증 코드를 보내드려요.'
                : `${email.trim()} 으로 보낸 6자리 코드를 입력해주세요.`}
            </p>
          </div>

          {step === 'email' ? (
            <form onSubmit={sendCode} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input type="email" inputMode="email" autoComplete="username" placeholder="이메일" autoFocus
                value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
              {error && <Banner tone="error">{error}</Banner>}
              <div style={{ marginTop: 6 }}>
                <CTA icon={null} busy={busy} onClick={sendCode}>인증 코드 보내기</CTA>
              </div>
            </form>
          ) : (
            <form onSubmit={reset} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input type="text" inputMode="numeric" autoComplete="one-time-code" placeholder="인증 코드 6자리" autoFocus
                maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                style={{ ...inputStyle, letterSpacing: 6, textAlign: 'center', fontSize: 20, fontWeight: 700 }} />
              <input type="password" autoComplete="new-password" placeholder="새 비밀번호 (8자 이상)"
                value={pw} onChange={(e) => setPw(e.target.value)} style={inputStyle} />
              <input type="password" autoComplete="new-password" placeholder="새 비밀번호 확인"
                value={pw2} onChange={(e) => setPw2(e.target.value)} style={inputStyle} />
              {notice && !error && <Banner tone="info">{notice}</Banner>}
              {error && <Banner tone="error">{error}</Banner>}
              <div style={{ marginTop: 6 }}>
                <CTA icon={null} busy={busy} onClick={reset}>비밀번호 변경하고 로그인</CTA>
              </div>
              <button type="button" onClick={sendCode} disabled={busy || cooldown > 0}
                style={{ background: 'none', border: 'none', cursor: cooldown > 0 ? 'default' : 'pointer',
                  color: cooldown > 0 ? 'var(--label-tertiary)' : 'var(--tint)', fontSize: 14, fontWeight: 600, padding: 6 }}>
                {cooldown > 0 ? `코드 다시 보내기 (${cooldown}초)` : '코드 다시 보내기'}
              </button>
            </form>
          )}

          <button type="button" onClick={onBack}
            style={{ display: 'block', margin: '18px auto 0', background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--label-secondary)', fontSize: 14, padding: 6 }}>
            ← 로그인으로 돌아가기
          </button>
        </div>
      </div>
    </div>
  );
}
