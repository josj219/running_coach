// 첫 로그인 온보딩 — 프로필·목표·기본 시간표를 한 번에 입력한다.
import React, { useRef, useState } from 'react';
import { api } from './api.js';
import { Banner, Card, CTA, Icon, SectionLabel } from './components/Ui.jsx';
import { WEEK_DAYS } from './workouts.js';

const PLACES = ['실내 헬스장', '야외', '트레드밀', '기타'];
const inputS = {
  width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
  borderRadius: 11, padding: '11px 13px', fontSize: 16, color: 'var(--label-primary)',
};

function Field({ label, value, onChange, placeholder, type = 'text', mode = 'text', maxLength }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 5 }}>{label}</div>
      <input type={type} inputMode={mode} value={value} placeholder={placeholder}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)} style={inputS} />
    </div>
  );
}

// HH:MM:SS 세그먼트 입력 — 각 칸은 숫자 키보드, 2자리 입력 시 다음 칸으로 자동 이동
function TimeInput({ label, value, onChange }) {
  const parts = (value || '').split(':');
  const [h, setH] = useState(parts[0] || '');
  const [m, setM] = useState(parts[1] || '');
  const [s, setS] = useState(parts[2] || '');
  const mRef = useRef();
  const sRef = useRef();

  const emit = (nh, nm, ns) => {
    if (!nh && !nm && !ns) { onChange(''); return; }
    onChange(`${(nh || '0').padStart(2, '0')}:${(nm || '0').padStart(2, '0')}:${(ns || '0').padStart(2, '0')}`);
  };

  const segS = {
    width: 36, border: 'none', outline: 'none', background: 'none',
    fontSize: 18, fontWeight: 700, color: 'var(--label-primary)',
    textAlign: 'center', padding: 0,
  };
  const colonS = { fontSize: 18, fontWeight: 700, color: 'var(--label-secondary)', userSelect: 'none' };

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 5 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 2, background: 'var(--fill-tertiary)',
        borderRadius: 11, padding: '11px 13px' }}>
        <input inputMode="numeric" maxLength={2} value={h} placeholder="00" style={segS}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 2);
            setH(v); emit(v, m, s);
            if (v.length === 2) mRef.current?.focus();
          }} />
        <span style={colonS}>:</span>
        <input ref={mRef} inputMode="numeric" maxLength={2} value={m} placeholder="00" style={segS}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 2);
            setM(v); emit(h, v, s);
            if (v.length === 2) sRef.current?.focus();
          }} />
        <span style={colonS}>:</span>
        <input ref={sRef} inputMode="numeric" maxLength={2} value={s} placeholder="00" style={segS}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 2);
            setS(v); emit(h, m, v);
          }} />
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--label-tertiary)' }}>시간 : 분 : 초</span>
      </div>
    </div>
  );
}

const EMPTY_SLOT = { days: [], title: '', duration_min: '', place: '야외', note: '' };
// 보유 기구를 적어두면 코치가 그에 맞춰 훈련을 제안한다 (예: 무동력 트레드밀 인터벌).
const GEAR_PLACES = ['실내 헬스장'];
const CURRENT_YEAR = new Date().getFullYear();

export default function Onboarding({ user, onDone }) {
  const [f, setF] = useState({
    nickname: user?.nickname && user.nickname !== '러너' ? user.nickname : '',
    height_cm: '', weight_kg: '', birth_year: '', career_years: '',
    pb_10k: '', pb_half: '', pb_full: '',
    race_type: '', target_time: '', target_date: '', weekly_goal_km: '',
  });
  const [slots, setSlots] = useState([]);
  const [draft, setDraft] = useState(EMPTY_SLOT);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));

  const toggleDay = (d) => setDraft((s) => ({
    ...s, days: s.days.includes(d) ? s.days.filter((x) => x !== d) : [...s.days, d].sort(),
  }));
  const addSlot = () => {
    if (!draft.title.trim() || draft.days.length === 0) { setError('시간대는 요일과 이름이 필요해요.'); return; }
    setSlots((s) => [...s, draft]); setDraft(EMPTY_SLOT); setError(null);
  };

  const submit = async () => {
    if (!f.nickname.trim()) { setError('닉네임은 꼭 입력해주세요.'); return; }
    setBusy(true); setError(null);
    const num = (v) => (v === '' || v == null ? null : parseFloat(v));
    const age = f.birth_year ? CURRENT_YEAR - parseInt(f.birth_year, 10) : null;
    try {
      const me = await api.onboard({
        nickname: f.nickname.trim(),
        height_cm: num(f.height_cm), weight_kg: num(f.weight_kg),
        age, career_years: num(f.career_years),
        pb_10k: f.pb_10k || null, pb_half: f.pb_half || null, pb_full: f.pb_full || null,
        race_type: f.race_type || null, target_time: f.target_time || null,
        target_date: f.target_date || null, weekly_goal_km: num(f.weekly_goal_km),
        slots: slots.map((s) => ({
          days: s.days, title: s.title.trim(),
          duration_min: s.duration_min ? parseInt(s.duration_min, 10) : null, place: s.place,
          note: s.note?.trim() || null,
        })),
      });
      onDone(me);
    } catch (err) {
      setError(err.message || '저장에 실패했어요.');
      setBusy(false);
    }
  };

  return (
    <div className="app-frame">
      <div className="scroll-area anim-in" style={{ padding: '24px 16px 40px' }}>
        <div style={{ maxWidth: 480, margin: '0 auto' }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 800, margin: '0 0 4px' }}>
            프로필 설정</h1>
          <p style={{ fontSize: 14, color: 'var(--label-secondary)', margin: '0 0 20px' }}>
            코칭에 쓰일 기본 정보예요. 나중에 설정에서 바꿀 수 있어요.</p>

          <SectionLabel>기본 정보</SectionLabel>
          <Card pad={16} style={{ marginBottom: 16 }}>
            <Field label="닉네임 *" value={f.nickname} onChange={set('nickname')} placeholder="고고조" />
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1 }}><Field label="키 (cm)" value={f.height_cm} mode="decimal" onChange={set('height_cm')} placeholder="178" /></div>
              <div style={{ flex: 1 }}><Field label="체중 (kg)" value={f.weight_kg} mode="decimal" onChange={set('weight_kg')} placeholder="72" /></div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1 }}><Field label="출생 연도" value={f.birth_year} mode="numeric" maxLength={4} onChange={set('birth_year')} placeholder="1990" /></div>
              <div style={{ flex: 1 }}><Field label="러닝 경력 (년)" value={f.career_years} mode="decimal" onChange={set('career_years')} placeholder="2" /></div>
            </div>
          </Card>

          <SectionLabel>개인 기록 (PB · 선택)</SectionLabel>
          <Card pad={16} style={{ marginBottom: 16 }}>
            <TimeInput label="10K" value={f.pb_10k} onChange={set('pb_10k')} />
            <TimeInput label="하프" value={f.pb_half} onChange={set('pb_half')} />
            <TimeInput label="풀" value={f.pb_full} onChange={set('pb_full')} />
          </Card>

          <SectionLabel>목표 (선택)</SectionLabel>
          <Card pad={16} style={{ marginBottom: 16 }}>
            <Field label="대회 종류" value={f.race_type} onChange={set('race_type')} placeholder="풀마라톤" />
            <TimeInput label="목표 기록" value={f.target_time} onChange={set('target_time')} />
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 5 }}>대회 날짜</div>
              <input type="date" value={f.target_date} onChange={(e) => set('target_date')(e.target.value)}
                style={{ ...inputS, WebkitAppearance: 'none', appearance: 'none', colorScheme: 'light dark' }} />
            </div>
            <Field label="주간 목표 거리 (km)" value={f.weekly_goal_km} mode="decimal" onChange={set('weekly_goal_km')} placeholder="45" />
          </Card>

          <SectionLabel>훈련 가능 시간 (선택)</SectionLabel>
          <Card pad={16} style={{ marginBottom: 16 }}>
            {slots.map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--tint)', paddingTop: 1 }}>{s.days.map((d) => WEEK_DAYS[d]).join('·')}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14.5 }}>{s.title}{s.duration_min ? ` · ${s.duration_min}분` : ''}{s.place ? ` · ${s.place}` : ''}</div>
                  {s.note?.trim() && <div style={{ fontSize: 12.5, color: 'var(--label-tertiary)', marginTop: 2 }}>🏋️ {s.note.trim()}</div>}
                </div>
                <button onClick={() => setSlots(slots.filter((_, idx) => idx !== i))} aria-label="삭제"
                  style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 4 }}>
                  <Icon name="Trash2" size={15} color="var(--accent-red)" /></button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
              {WEEK_DAYS.map((d, i) => (
                <button key={d} onClick={() => toggleDay(i)}
                  style={{ flex: 1, padding: '8px 0', borderRadius: 9, border: 'none', cursor: 'pointer',
                    fontSize: 13.5, fontWeight: 700,
                    background: draft.days.includes(i) ? 'var(--tint)' : 'var(--fill-tertiary)',
                    color: draft.days.includes(i) ? '#fff' : 'var(--label-secondary)' }}>{d}</button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                placeholder="이름 (예: 점심 헬스장)" style={{ ...inputS, flex: 2 }} />
              <input value={draft.duration_min} inputMode="numeric"
                onChange={(e) => setDraft({ ...draft, duration_min: e.target.value })}
                placeholder="45분" style={{ ...inputS, flex: 1 }} />
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
              {PLACES.map((p) => (
                <button key={p} onClick={() => setDraft({ ...draft, place: p })}
                  style={{ padding: '6px 11px', borderRadius: 999, border: 'none', cursor: 'pointer', fontSize: 13,
                    fontWeight: 600, background: draft.place === p ? 'var(--tint)' : 'var(--fill-tertiary)',
                    color: draft.place === p ? '#fff' : 'var(--label-secondary)' }}>{p}</button>
              ))}
            </div>
            <button onClick={addSlot} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              justifyContent: 'center', padding: '10px', border: '1px dashed var(--separator-non-opaque)',
              borderRadius: 11, background: 'none', cursor: 'pointer', color: 'var(--tint)', fontSize: 14, fontWeight: 600 }}>
              <Icon name="Plus" size={16} strokeWidth={2.4} /> 시간대 추가
            </button>
          </Card>

          {error && <div style={{ marginBottom: 12 }}><Banner tone="error">{error}</Banner></div>}
          <CTA icon="Check" busy={busy} onClick={submit}>시작하기</CTA>
        </div>
      </div>
    </div>
  );
}
