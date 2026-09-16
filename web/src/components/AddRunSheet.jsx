import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Banner, CTA, inputStyle, Modal, Spinner } from './Ui.jsx';
import { localISO } from '../workouts.js';

export default function AddRunSheet({ onClose, onPick, onImported }) {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState([]);
  const [date, setDate] = useState(localISO());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const load = async () => {
    try { setData(await api.pendingActivities()); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);
  const sync = async (provider) => {
    setBusy(true); setError(null);
    try { await api.sync(provider); } catch (e) { setError(e.message); }
    await load(); setBusy(false);
  };
  const importSelected = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api.importActivities(selected);
      setNotice(`새 운동 ${r.created_count}건 반영 · 이미 반영된 운동 ${r.items.length - r.created_count}건`);
      setSelected([]); await load(); onImported?.();
    } catch (e) { setError(e.message); }
    setBusy(false);
  };
  return <Modal title="새 운동 추가 · 연동 반영" subtitle="같은 날의 운동도 각각 보존합니다" onClose={onClose} locked={busy}>
    <div style={{ padding: 20, display: 'grid', gap: 14 }}>
      {error && <Banner tone="error">{error}</Banner>}
      {notice && <Banner tone="info">{notice}</Banner>}
      {!data ? <Spinner label="활동 확인 중…" /> : <>
        <b>미반영 활동 {data.pending_count}건</b>
        {Object.entries(data.integrations).map(([provider, info]) => <div key={provider}>
          <b>{provider === 'garmin' ? 'Garmin' : 'Strava'}</b> · {info.connected ? '연결됨' : '연결 안 됨'}
          <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>최근 동기화: {info.last_sync_at ? new Date(info.last_sync_at).toLocaleString() : '아직 없음'}</div>
          {info.last_sync_error && <Banner tone="warn">{info.last_sync_error}</Banner>}
          {info.connected && <CTA variant="gray" busy={busy} onClick={() => sync(provider)}>최근 활동 동기화</CTA>}
        </div>)}
        <p style={{ fontSize: 13, color: 'var(--label-secondary)' }}>같은 운동이 두 공급자에서 들어오면 시작 시각·거리·시간을 함께 확인해 한 번 반영합니다. 시간이나 수치가 다른 중복 기록은 원본을 확인하고 하나만 선택하세요.</p>
        {data.items.map((a) => <label key={a.id} style={{ display: 'flex', gap: 12, padding: 12, background: 'var(--fill-tertiary)', borderRadius: 12 }}>
          <input type="checkbox" checked={selected.includes(a.id)} onChange={(e) => setSelected((s) => e.target.checked ? [...s, a.id] : s.filter((id) => id !== a.id))} />
          <span><b>{a.name || '러닝'}</b><br /><small>{a.start_date ? new Date(a.start_date).toLocaleString() : '시각 없음'} · {a.distance_km}km · {a.provider}</small></span>
        </label>)}
        {data.items.length > 0 && <CTA disabled={!selected.length} busy={busy} onClick={importSelected}>선택한 {selected.length}건 확인 후 반영</CTA>}
      </>}
      <b>날짜를 골라 새 운동 입력</b>
      <input type="date" aria-label="기록할 날짜" style={inputStyle} value={date} max={localISO()} onChange={(e) => setDate(e.target.value)} />
      <CTA disabled={!date} onClick={() => onPick(date, null, null)}>새 운동 입력</CTA>
      <small>기존 운동 수정은 홈의 해당 기록에서 ‘이 기록 수정’을 선택하세요.</small>
    </div>
  </Modal>;
}
