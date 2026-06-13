// 설정 탭 — 프로필/목표/훈련 가능 시간/연동(Strava·Garmin)/화면/앱
import React, { useEffect, useRef, useState } from 'react';
import { api, clearToken } from '../api.js';
import { fmtDays, WEEK_DAYS } from '../workouts.js';
import { Banner, Card, CTA, Icon, NavBarLarge, SectionLabel, Spinner } from '../components/Ui.jsx';

const CURRENT_YEAR = new Date().getFullYear();

// HH:MM:SS 세그먼트 입력
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

const PLACES = ['실내 헬스장', '야외', '트레드밀', '기타'];
const EMPTY_SLOT = { days: [], title: '', duration_min: '', place: '야외', note: '' };

// 훈련 가능 시간(기본 시간표) 편집 — 슬롯 리스트 + 추가/수정/삭제, 저장은 PUT 전체 교체
function AvailabilityEditor() {
  const [slots, setSlots] = useState(null);
  const [editIdx, setEditIdx] = useState(null); // 인덱스 | 'new' | null
  const [form, setForm] = useState(EMPTY_SLOT);
  const [error, setError] = useState(null);

  const load = () => api.availability().then((r) => setSlots(r.slots)).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  if (error) return <Banner tone="error">{error}</Banner>;
  if (slots === null) return <Card pad={16}><span style={{ fontSize: 14, color: 'var(--label-secondary)' }}>불러오는 중…</span></Card>;

  const saveAll = async (next) => {
    try {
      const r = await api.putAvailability(next.map((s) => ({
        days: s.days, title: s.title,
        duration_min: parseInt(s.duration_min, 10) || null,
        place: s.place || null, note: s.note || null,
      })));
      setSlots(r.slots);
      setEditIdx(null);
      setError(null);
    } catch (e) { setError(e.message); }
  };

  const startEdit = (i) => {
    setEditIdx(i);
    setForm(i === 'new' ? EMPTY_SLOT : { ...slots[i], duration_min: slots[i].duration_min ?? '' });
  };
  const submit = () => {
    if (!form.title.trim() || form.days.length === 0) {
      setError('요일과 이름은 꼭 필요해요.');
      return;
    }
    const next = editIdx === 'new'
      ? [...slots, form]
      : slots.map((s, i) => (i === editIdx ? form : s));
    saveAll(next);
  };
  const remove = (i) => saveAll(slots.filter((_, idx) => idx !== i));
  const toggleDay = (d) => setForm((f) => ({
    ...f, days: f.days.includes(d) ? f.days.filter((x) => x !== d) : [...f.days, d].sort(),
  }));

  return (
    <Card pad={0}>
      {slots.map((s, i) => (
        <div key={s.id ?? i} style={{ borderBottom: '0.5px solid var(--separator-non-opaque)' }}>
          {editIdx === i ? null : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px' }}>
              <span style={{ minWidth: 44, textAlign: 'center', fontSize: 12.5, fontWeight: 700, color: 'var(--tint)',
                background: 'color-mix(in srgb, var(--tint) 12%, transparent)', borderRadius: 8, padding: '5px 7px', flex: 'none' }}>
                {fmtDays(s.days)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15.5, fontWeight: 600, color: 'var(--label-primary)' }}>{s.title}</div>
                <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>
                  {s.duration_min ? `${s.duration_min}분` : ''}{s.place ? ` · ${s.place}` : ''}</div>
              </div>
              <button onClick={() => startEdit(i)} aria-label="편집" style={{ background: 'none', border: 'none',
                cursor: 'pointer', padding: 6 }}><Icon name="Pencil" size={16} color="var(--label-tertiary)" /></button>
              <button onClick={() => remove(i)} aria-label="삭제" style={{ background: 'none', border: 'none',
                cursor: 'pointer', padding: 6 }}><Icon name="Trash2" size={16} color="var(--accent-red)" /></button>
            </div>
          )}
        </div>
      ))}

      {editIdx !== null ? (
        <div className="anim-in" style={{ padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 8 }}>요일</div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
            {WEEK_DAYS.map((d, i) => (
              <button key={d} onClick={() => toggleDay(i)}
                style={{ flex: 1, padding: '9px 0', borderRadius: 10, border: 'none', cursor: 'pointer',
                  fontSize: 14, fontWeight: 700,
                  background: form.days.includes(i) ? 'var(--tint)' : 'var(--fill-tertiary)',
                  color: form.days.includes(i) ? '#fff' : 'var(--label-secondary)' }}>{d}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="이름 (예: 점심 헬스장)"
              style={{ flex: 2, border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
                borderRadius: 11, padding: '11px 13px', fontSize: 15, color: 'var(--label-primary)' }} />
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', background: 'var(--fill-tertiary)',
              borderRadius: 11, padding: '0 13px' }}>
              <input value={form.duration_min} inputMode="numeric"
                onChange={(e) => setForm({ ...form, duration_min: e.target.value })} placeholder="45"
                style={{ width: '100%', border: 'none', outline: 'none', background: 'none',
                  fontSize: 15, color: 'var(--label-primary)' }} />
              <span style={{ fontSize: 13, color: 'var(--label-tertiary)', fontWeight: 600 }}>분</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {PLACES.map((p) => (
              <button key={p} onClick={() => setForm({ ...form, place: p })}
                style={{ padding: '7px 12px', borderRadius: 999, border: 'none', cursor: 'pointer',
                  fontSize: 13.5, fontWeight: 600,
                  background: form.place === p ? 'var(--tint)' : 'var(--fill-tertiary)',
                  color: form.place === p ? '#fff' : 'var(--label-secondary)' }}>{p}</button>
            ))}
          </div>
          <input value={form.note || ''} onChange={(e) => setForm({ ...form, note: e.target.value })}
            placeholder="메모 (예: 17시경 회사→집 8km 한강변)"
            style={{ width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
              borderRadius: 11, padding: '11px 13px', fontSize: 15, color: 'var(--label-primary)', marginBottom: 14 }} />
          {error && <div style={{ marginBottom: 12 }}><Banner tone="error">{error}</Banner></div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1 }}><CTA variant="gray" icon={null} onClick={() => { setEditIdx(null); setError(null); }}>취소</CTA></div>
            <div style={{ flex: 1 }}><CTA icon="Check" onClick={submit}>저장</CTA></div>
          </div>
        </div>
      ) : (
        <button onClick={() => startEdit('new')} style={{ display: 'flex', alignItems: 'center', gap: 8,
          width: '100%', padding: '14px 16px', border: 'none', background: 'none', cursor: 'pointer',
          color: 'var(--tint)', fontSize: 15, fontWeight: 600 }}>
          <Icon name="Plus" size={17} strokeWidth={2.4} /> 시간대 추가
        </button>
      )}
    </Card>
  );
}

const ACCENTS = ['#0088ff', '#34c759', '#ff8d28', '#ff2d55', '#6155f5'];
const TONES = [
  { v: 'calm', label: '차분한 데이터형' },
  { v: 'warm', label: '따뜻한 격려형' },
  { v: 'strict', label: '엄격한 코치형' },
];

function Row({ icon, iconBg, label, value, onClick, danger }) {
  return (
    <button onClick={onClick} disabled={!onClick}
      style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', padding: '13px 16px',
        border: 'none', background: 'none', cursor: onClick ? 'pointer' : 'default', textAlign: 'left' }}>
      {icon && <span style={{ width: 30, height: 30, borderRadius: 9, background: iconBg || 'var(--fill-secondary)',
        display: 'grid', placeItems: 'center', flex: 'none' }}><Icon name={icon} size={16} color="#fff" /></span>}
      <span style={{ flex: 1, fontSize: 16, color: danger ? 'var(--accent-red)' : 'var(--label-primary)' }}>{label}</span>
      {value && <span style={{ fontSize: 15, color: 'var(--label-secondary)' }}>{value}</span>}
      {onClick && <Icon name="ChevronRight" size={17} color="var(--label-tertiary)" />}
    </button>
  );
}

function EditField({ label, value, onChange, placeholder, mode = 'text', maxLength }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 5 }}>{label}</div>
      <input type="text" inputMode={mode} value={value ?? ''} placeholder={placeholder}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
          borderRadius: 11, padding: '11px 13px', fontSize: 16, color: 'var(--label-primary)' }} />
    </div>
  );
}

export default function Settings({ theme, setTheme, accent, setAccent }) {
  const [profile, setProfile] = useState(null);
  const [goal, setGoal] = useState(null);
  const [settings, setSettings] = useState(null);
  const [integ, setInteg] = useState(null);
  const [editing, setEditing] = useState(null); // 'profile' | 'goal' | null
  const [form, setForm] = useState({});
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const [p, g, s, i] = await Promise.all([api.profile(), api.goal(), api.settings(), api.integrations()]);
      setProfile(p); setGoal(g); setSettings(s); setInteg(i);
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  // Strava OAuth 복귀 처리 (?strava=connected|denied)
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get('strava') === 'connected') setNotice('Strava가 연결됐어요. 이제 기록이 자동으로 채워집니다.');
    if (q.get('strava') === 'denied') setNotice('Strava 연결이 취소됐어요.');
    if (q.get('strava')) window.history.replaceState({}, '', '/');
  }, []);

  if (error) return <div><NavBarLarge title="설정" />
    <div style={{ padding: '8px 16px' }}><Banner tone="error" action="재시도" onAction={load}>{error}</Banner></div></div>;
  if (!profile || !settings) return <div><NavBarLarge title="설정" /><Spinner /></div>;

  const saveProfile = async () => {
    const age = form.birth_year ? CURRENT_YEAR - parseInt(form.birth_year, 10) : null;
    await api.patchProfile({
      nickname: form.nickname, age,
      career_years: parseFloat(form.career_years) || null,
      height_cm: parseFloat(form.height_cm) || null, weight_kg: parseFloat(form.weight_kg) || null,
      pb_10k: form.pb_10k || null, pb_half: form.pb_half || null, pb_full: form.pb_full || null,
    });
    setEditing(null); load();
  };
  const saveGoal = async () => {
    await api.putGoal({
      race_type: form.race_type || '풀마라톤', target_time: form.target_time || null,
      target_date: form.target_date || null, description: form.description || null,
    });
    setEditing(null); load();
  };

  const patchSetting = async (k, v) => {
    setSettings({ ...settings, [k]: v });
    await api.patchSettings({ [k]: v });
  };

  return (
    <div className="anim-in">
      <NavBarLarge title="설정" />
      <div style={{ padding: '4px 16px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        {notice && <Banner tone="info">{notice}</Banner>}

        {/* 프로필 */}
        <div>
          <SectionLabel trailing={
            <button onClick={() => { setForm({ ...profile, birth_year: profile.age ? String(CURRENT_YEAR - profile.age) : '' }); setEditing(editing === 'profile' ? null : 'profile'); }}
              style={{ background: 'none', border: 'none', color: 'var(--tint)', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              {editing === 'profile' ? '취소' : '편집'}</button>}>프로필</SectionLabel>
          <Card pad={editing === 'profile' ? 16 : 0}>
            {editing === 'profile' ? (
              <div className="anim-in">
                <EditField label="닉네임" value={form.nickname} onChange={(v) => setForm({ ...form, nickname: v })} />
                <div style={{ display: 'flex', gap: 10 }}>
                  <div style={{ flex: 1 }}><EditField label="키 (cm)" value={form.height_cm} mode="decimal" onChange={(v) => setForm({ ...form, height_cm: v })} /></div>
                  <div style={{ flex: 1 }}><EditField label="체중 (kg)" value={form.weight_kg} mode="decimal" onChange={(v) => setForm({ ...form, weight_kg: v })} /></div>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <div style={{ flex: 1 }}><EditField label="출생 연도" value={form.birth_year} mode="numeric" maxLength={4} onChange={(v) => setForm({ ...form, birth_year: v })} placeholder="1990" /></div>
                  <div style={{ flex: 1 }}><EditField label="러닝 경력 (년)" value={form.career_years} mode="decimal" onChange={(v) => setForm({ ...form, career_years: v })} /></div>
                </div>
                <TimeInput label="10K PB" value={form.pb_10k} onChange={(v) => setForm({ ...form, pb_10k: v })} />
                <TimeInput label="하프 PB" value={form.pb_half} onChange={(v) => setForm({ ...form, pb_half: v })} />
                <TimeInput label="풀 PB" value={form.pb_full} onChange={(v) => setForm({ ...form, pb_full: v })} />
                <CTA icon="Check" onClick={saveProfile}>저장</CTA>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 16px 12px' }}>
                  <span style={{ width: 54, height: 54, borderRadius: '50%', background: 'linear-gradient(135deg, var(--tint), var(--accent-indigo))',
                    display: 'grid', placeItems: 'center', fontSize: 22, fontWeight: 800, color: '#fff' }}>
                    {(profile.nickname || '러')[0]}</span>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700 }}>{profile.nickname}</div>
                    <div style={{ fontSize: 13.5, color: 'var(--label-secondary)' }}>
                      러닝 {profile.career_years ?? '-'}년차 · {profile.age ?? '-'}세</div>
                  </div>
                </div>
                <div style={{ display: 'flex', borderTop: '0.5px solid var(--separator-non-opaque)', padding: '12px 0' }}>
                  {[['10K', profile.pb_10k], ['하프', profile.pb_half], ['풀', profile.pb_full]].map(([k, v], i) => (
                    <div key={k} style={{ flex: 1, textAlign: 'center',
                      borderLeft: i ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                      <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--label-tertiary)', textTransform: 'uppercase' }}>{k} PB</div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 700, marginTop: 3 }}>
                        {v ? v.replace(/^00:/, '') : '—'}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>

        {/* 목표 */}
        <div>
          <SectionLabel trailing={
            <button onClick={() => { setForm(goal); setEditing(editing === 'goal' ? null : 'goal'); }}
              style={{ background: 'none', border: 'none', color: 'var(--tint)', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              {editing === 'goal' ? '취소' : '편집'}</button>}>목표</SectionLabel>
          <Card pad={16}>
            {editing === 'goal' ? (
              <div className="anim-in">
                <EditField label="대회 종류" value={form.race_type} placeholder="풀마라톤" onChange={(v) => setForm({ ...form, race_type: v })} />
                <TimeInput label="목표 기록" value={form.target_time} onChange={(v) => setForm({ ...form, target_time: v })} />
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 5 }}>대회 날짜</div>
                  <input type="date" value={form.target_date || ''} onChange={(e) => setForm({ ...form, target_date: e.target.value })}
                    style={{ width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
                      borderRadius: 11, padding: '11px 13px', fontSize: 16, color: 'var(--label-primary)',
                      WebkitAppearance: 'none', appearance: 'none', colorScheme: 'light dark' }} />
                </div>
                <CTA icon="Check" onClick={saveGoal}>저장</CTA>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--accent-indigo)',
                  display: 'grid', placeItems: 'center', flex: 'none' }}><Icon name="Trophy" size={20} color="#fff" /></span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 16.5, fontWeight: 700 }}>
                    {goal?.race_type || '목표 미설정'} {goal?.target_time ? `sub ${goal.target_time.replace(/^0/, '').slice(0, 4)}` : ''}</div>
                  <div style={{ fontSize: 13.5, color: 'var(--label-secondary)', marginTop: 2 }}>
                    {goal?.target_date || '날짜 미정'}{goal?.dday != null ? ` · D-${goal.dday}` : ''}</div>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* 훈련 가능 시간 */}
        <div>
          <SectionLabel>훈련 가능 시간</SectionLabel>
          <div style={{ fontSize: 13, color: 'var(--label-tertiary)', margin: '-6px 4px 10px' }}>
            요일별 기본 루틴 — 주간 계획의 기준이 돼요.</div>
          <AvailabilityEditor />
        </div>

        {/* 연동 */}
        <div>
          <SectionLabel>데이터 연동</SectionLabel>
          <Card pad={0}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px' }}>
              <span style={{ width: 34, height: 34, borderRadius: 10, background: '#FC4C02', display: 'grid',
                placeItems: 'center', flex: 'none' }}><Icon name="Zap" size={18} color="#fff" /></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 16, fontWeight: 600 }}>Strava</div>
                <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>
                  {integ?.strava.connected
                    ? `연결됨${integ.strava.athlete_name ? ` · ${integ.strava.athlete_name}` : ''}`
                    : integ?.strava.available ? '거리·페이스·심박 자동 입력' : '서버에 API 키 설정 필요'}</div>
              </div>
              {integ?.strava.connected ? (
                <button onClick={async () => { await api.stravaDisconnect(); load(); }}
                  style={{ border: 'none', background: 'var(--fill-tertiary)', color: 'var(--accent-red)',
                    fontWeight: 600, fontSize: 13.5, borderRadius: 999, padding: '7px 13px', cursor: 'pointer' }}>해제</button>
              ) : (
                <button disabled={!integ?.strava.available}
                  onClick={async () => { const r = await api.stravaAuthUrl(); window.location.href = r.url; }}
                  style={{ border: 'none', background: integ?.strava.available ? '#FC4C02' : 'var(--fill-tertiary)',
                    color: integ?.strava.available ? '#fff' : 'var(--label-tertiary)', fontWeight: 700, fontSize: 13.5,
                    borderRadius: 999, padding: '7px 14px', cursor: 'pointer' }}>연결</button>
              )}
            </div>
            <div style={{ borderTop: '0.5px solid var(--separator-non-opaque)', display: 'flex', gap: 12,
              padding: '14px 16px', alignItems: 'flex-start' }}>
              <span style={{ width: 34, height: 34, borderRadius: 10, background: '#11A9ED', display: 'grid',
                placeItems: 'center', flex: 'none' }}><Icon name="Watch" size={18} color="#fff" /></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 16, fontWeight: 600 }}>Garmin</div>
                <div style={{ fontSize: 13, color: 'var(--label-secondary)', lineHeight: 1.45, marginTop: 2 }}>
                  Garmin Connect 앱 → 설정 → 연결된 앱에서 <b>Strava 자동 업로드</b>를 켜면
                  Strava 연동 하나로 가민 기록이 자동으로 들어와요.</div>
              </div>
            </div>
          </Card>
        </div>

        {/* 화면 */}
        <div>
          <SectionLabel>화면 · 코치</SectionLabel>
          <Card pad={16}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 8 }}>테마</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {[['dark', '다크'], ['light', '라이트']].map(([v, l]) => (
                <button key={v} onClick={() => setTheme(v)}
                  style={{ flex: 1, padding: '10px 0', borderRadius: 12, border: 'none', cursor: 'pointer',
                    fontSize: 14.5, fontWeight: 600, background: theme === v ? 'var(--tint)' : 'var(--fill-tertiary)',
                    color: theme === v ? '#fff' : 'var(--label-secondary)' }}>{l}</button>
              ))}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 8 }}>강조 색상</div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              {ACCENTS.map((c) => (
                <button key={c} onClick={() => { setAccent(c); patchSetting('accent', c); }}
                  aria-label={c}
                  style={{ width: 34, height: 34, borderRadius: '50%', border: accent === c ? '3px solid var(--label-primary)' : '3px solid transparent',
                    background: c, cursor: 'pointer' }} />
              ))}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)', marginBottom: 8 }}>코치 톤</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {TONES.map((t) => (
                <button key={t.v} onClick={() => patchSetting('coach_tone', t.v)}
                  style={{ flex: 1, padding: '10px 4px', borderRadius: 12, border: 'none', cursor: 'pointer',
                    fontSize: 13, fontWeight: 600,
                    background: settings.coach_tone === t.v ? 'var(--tint)' : 'var(--fill-tertiary)',
                    color: settings.coach_tone === t.v ? '#fff' : 'var(--label-secondary)' }}>{t.label}</button>
              ))}
            </div>
          </Card>
        </div>

        {/* 앱 */}
        <div>
          <SectionLabel>앱</SectionLabel>
          <Card pad={0}>
            <Row icon="Target" iconBg="var(--accent-green)" label="주간 목표 거리" value={`${settings.weekly_goal_km} km`}
              onClick={() => {
                const v = window.prompt('주간 목표 거리 (km)', settings.weekly_goal_km);
                if (v && !Number.isNaN(parseFloat(v))) patchSetting('weekly_goal_km', parseFloat(v));
              }} />
            <div style={{ borderTop: '0.5px solid var(--separator-non-opaque)' }} />
            <Row icon="Info" iconBg="var(--gray)" label="버전" value="2.0.0" />
            <div style={{ borderTop: '0.5px solid var(--separator-non-opaque)' }} />
            <Row icon="LogOut" iconBg="var(--accent-red)" label="로그아웃" danger
              onClick={() => { clearToken(); window.dispatchEvent(new Event('auth:logout')); }} />
          </Card>
        </div>
      </div>
    </div>
  );
}
