// 디자인 토큰 — web/src/styles/tokens.css 의 다크 테마와 동일 값
export const C = {
  bg: '#000000',
  card: '#161618',
  fill: 'rgba(118,118,128,0.24)',
  fill2: 'rgba(120,120,128,0.32)',
  label: '#ffffff',
  label2: 'rgba(235,235,245,0.60)',
  label3: 'rgba(235,235,245,0.30)',
  sep: 'rgba(255,255,255,0.14)',
  tint: '#0091ff',
  green: '#30d158',
  orange: '#ff9230',
  red: '#ff4245',
  indigo: '#6d7cff',
  strava: '#FC4C02',
};

export const WORKOUT_TYPES = {
  easy:     { label: '이지 런',  emoji: '👟', color: '#30d158' },
  interval: { label: '인터벌',   emoji: '⚡', color: '#ff375f' },
  tempo:    { label: '템포 런',  emoji: '🔥', color: '#ff9230' },
  long:     { label: '롱런',     emoji: '⛰️', color: '#6d7cff' },
  race:     { label: '대회',     emoji: '🏆', color: '#ff375f' },
  rest:     { label: '휴식',     emoji: '🛏️', color: '#8e8e93' },
  strength: { label: '근력 · 보강', emoji: '🏋️', color: '#00d2e0' },
  drill:    { label: '폼 드릴',  emoji: '🦵', color: '#3cd3fe' },
  core:     { label: '코어',     emoji: '🛡️', color: '#00d2e0' },
  mobility: { label: '가동성',   emoji: '🤸', color: '#3cd3fe' },
  other:    { label: '기타',     emoji: '🏃', color: '#8e8e93' },
};
export const wmeta = (k) => WORKOUT_TYPES[k] || WORKOUT_TYPES.other;

export const FEEL_OPTIONS = [
  { v: 1, emoji: '😰', label: '매우 힘듦' },
  { v: 2, emoji: '😐', label: '힘듦' },
  { v: 3, emoji: '🙂', label: '좋음' },
  { v: 4, emoji: '💪', label: '아주 좋음' },
];

export function sessionSubtitle(s) {
  if (!s) return '';
  if (s.is_rest) return s.focus || '완전 휴식';
  const parts = [];
  if (s.distance_km) parts.push(`${s.distance_km}km`);
  if (s.duration_min) parts.push(`${s.duration_min}${s.duration_min_max ? `~${s.duration_min_max}` : ''}분`);
  if (s.target_pace) parts.push(s.target_pace);
  return parts.join(' · ');
}

const WEEK_DAYS_KO = ['월', '화', '수', '목', '금', '토', '일'];
// 요일 배열 → "평일"/"주말"/"월·수·금"
export function fmtDays(days) {
  const s = [...days].sort();
  if (s.join() === '0,1,2,3,4') return '평일';
  if (s.join() === '5,6') return '주말';
  if (s.length === 7) return '매일';
  return s.map((d) => WEEK_DAYS_KO[d]).join('·');
}

export function autoPace(distanceKm, durationSec) {
  const d = parseFloat(distanceKm);
  if (!d || !durationSec) return '';
  const spk = durationSec / d;
  return `${Math.floor(spk / 60)}:${String(Math.round(spk % 60)).padStart(2, '0')}`;
}
