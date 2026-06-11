// 훈련 종류 메타 — design/project/app/data.jsx 이식 + 백엔드 enum 정렬
export const WORKOUT_TYPES = {
  easy:     { label: '이지 런',   icon: 'Footprints', color: 'var(--accent-green)',  rgb: '52,199,89',   zone: 'Zone 2 · 회복' },
  interval: { label: '인터벌',    icon: 'Zap',        color: 'var(--accent-pink)',   rgb: '255,45,85',   zone: 'Zone 5 · 스피드' },
  tempo:    { label: '템포 런',   icon: 'Flame',      color: 'var(--accent-orange)', rgb: '255,141,40',  zone: 'Zone 4 · 임계' },
  long:     { label: '롱런',      icon: 'Mountain',   color: 'var(--accent-indigo)', rgb: '97,85,245',   zone: 'Zone 2–3 · 지구력' },
  race:     { label: '대회',      icon: 'Trophy',     color: 'var(--accent-pink)',   rgb: '255,45,85',   zone: '레이스' },
  rest:     { label: '휴식',      icon: 'Bed',        color: 'var(--gray)',          rgb: '142,142,147', zone: '완전 휴식' },
  strength: { label: '근력 · 보강', icon: 'Dumbbell',  color: 'var(--accent-teal)',   rgb: '0,195,208',   zone: '코어 · 안정성' },
  drill:    { label: '폼 드릴',   icon: 'Activity',   color: 'var(--accent-cyan)',   rgb: '0,192,232',   zone: '폼 · 신경계' },
  core:     { label: '코어',      icon: 'Shield',     color: 'var(--accent-teal)',   rgb: '0,195,208',   zone: '코어' },
  mobility: { label: '가동성',    icon: 'StretchHorizontal', color: 'var(--accent-cyan)', rgb: '0,192,232', zone: '회복 · 가동성' },
  other:    { label: '기타',      icon: 'CircleDot',  color: 'var(--gray)',          rgb: '142,142,147', zone: '' },
};

export const wmeta = (kind) => WORKOUT_TYPES[kind] || WORKOUT_TYPES.other;

export const WEEK_DAYS = ['월', '화', '수', '목', '금', '토', '일'];

export const FEEL_OPTIONS = [
  { v: 1, emoji: '😰', label: '매우 힘듦' },
  { v: 2, emoji: '😐', label: '힘듦' },
  { v: 3, emoji: '🙂', label: '좋음' },
  { v: 4, emoji: '💪', label: '아주 좋음' },
];

export const BODY_PARTS = ['무릎', '발목', '정강이', '햄스트링', '종아리', '발바닥', '고관절', '허리'];

// 로컬(KST) 기준 YYYY-MM-DD — toISOString()은 UTC라 자정 전후 하루 밀림
export function localISO(d = new Date()) {
  const off = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - off).toISOString().slice(0, 10);
}

// ISO 8601 주차 키 (예: "2026-W24") — 주 1회 계획 프롬프트 기록용
export function isoWeekKey(d = new Date()) {
  const t = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  t.setDate(t.getDate() + 3 - ((t.getDay() + 6) % 7)); // 해당 주 목요일
  const year = t.getFullYear();
  const jan4 = new Date(year, 0, 4);
  const week = 1 + Math.round(((t - jan4) / 86400000 - 3 + ((jan4.getDay() + 6) % 7)) / 7);
  return `${year}-W${String(week).padStart(2, '0')}`;
}

// 요일 배열 [0..6] → "월·화·수" (평일/주말/매일 축약)
export function fmtDays(days) {
  const sorted = [...days].sort();
  if (sorted.join() === '0,1,2,3,4') return '평일';
  if (sorted.join() === '5,6') return '주말';
  if (sorted.length === 7) return '매일';
  return sorted.map((d) => WEEK_DAYS[d]).join('·');
}

export function fmtDuration(sec) {
  if (!sec) return null;
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}분${s ? ` ${s}초` : ''}`;
}

// "32:12" 또는 "1:02:12" → 초
export function parseTimeToSec(min, sec) {
  const m = parseInt(min, 10) || 0;
  const s = parseInt(sec, 10) || 0;
  return m * 60 + s || null;
}

// 거리+시간 → "M:SS" 페이스 자동 계산
export function autoPace(distanceKm, durationSec) {
  const d = parseFloat(distanceKm), t = durationSec;
  if (!d || !t || d <= 0) return '';
  const spk = t / d;
  return `${Math.floor(spk / 60)}:${String(Math.round(spk % 60)).padStart(2, '0')}`;
}

export function sessionSubtitle(s) {
  if (!s) return '';
  if (s.is_rest) return s.focus || '완전 휴식';
  const parts = [];
  if (s.distance_km) parts.push(`${s.distance_km}km`);
  if (s.duration_min) parts.push(`${s.duration_min}${s.duration_min_max ? `~${s.duration_min_max}` : ''}분`);
  if (s.target_pace) parts.push(s.target_pace);
  return parts.join(' · ');
}
