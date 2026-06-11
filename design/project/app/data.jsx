// data.jsx — mock data + domain model for the running coach prototype
// All numbers are tabular & concrete (Apple voice). Korean UI copy.

// ---- Workout type meta (color-coded, SF-Symbol-style icons) ----
const WORKOUT_TYPES = {
  easy:     { label: '이지 런',   short: '이지',   icon: 'footprints', color: 'var(--accent-green)',  rgb: '52,199,89',   zone: 'Zone 2 · 회복' },
  interval: { label: '인터벌',    short: '인터벌', icon: 'zap',        color: 'var(--accent-pink)',   rgb: '255,45,85',   zone: 'Zone 5 · 스피드' },
  tempo:    { label: '템포 런',   short: '템포',   icon: 'flame',      color: 'var(--accent-orange)', rgb: '255,141,40',  zone: 'Zone 4 · 임계' },
  long:     { label: '롱런',      short: '롱런',   icon: 'mountain',   color: 'var(--accent-indigo)', rgb: '97,85,245',   zone: 'Zone 2–3 · 지구력' },
  rest:     { label: '휴식',      short: '휴식',   icon: 'bed',        color: 'var(--gray)',          rgb: '142,142,147', zone: '완전 휴식' },
  strength: { label: '근력 · 보강', short: '보강', icon: 'dumbbell',   color: 'var(--accent-teal)',   rgb: '0,195,208',   zone: '코어 · 안정성' },
};

// ---- The week. today = 수요일(index 2). Mon-first. ----
const WEEK_DAYS = ['월', '화', '수', '목', '금', '토', '일'];
const TODAY_INDEX = 2;

const WEEK_PLAN = [
  {
    day: '월', type: 'easy', title: '이지 런', distance: 6, estMin: 38,
    target: '5:50–6:20 /km', focus: '편하게 대화 가능한 페이스',
    done: true, result: { distance: 6.04, min: 37, sec: 20, pace: '6:11', avgHr: 142, maxHr: 156, cadence: 168, feel: 3, note: '컨디션 좋음. 다리 가벼웠어요.' },
  },
  {
    day: '화', type: 'interval', title: '인터벌 400m × 8', distance: 7.2, estMin: 45,
    target: '1:40 /400m', focus: '회복 90초, 폼 유지',
    done: true, result: { distance: 7.18, min: 44, sec: 10, pace: '5:02', avgHr: 168, maxHr: 184, cadence: 182, feel: 2, note: '마지막 2개 페이스 떨어짐. 숨이 찼어요.' },
  },
  {
    day: '수', type: 'tempo', title: '템포 런 8km', distance: 8, estMin: 46,
    target: '5:05–5:15 /km', focus: '임계 페이스 20분 유지',
    detail: {
      warmup: '이지 조깅 10분 + 다이내믹 스트레칭',
      main: '템포 4km @ 5:10/km (Zone 4, 심박 162–172)',
      cooldown: '이지 조깅 10분 + 정적 스트레칭',
      note: '어제 인터벌 후 회복이 덜 됐다면 페이스를 5:20까지 늦춰도 좋아요.',
    },
    done: false,
  },
  { day: '목', type: 'rest', title: '휴식일', distance: 0, estMin: 0, focus: '수면 7시간 이상 · 가벼운 스트레칭', done: false },
  { day: '금', type: 'easy', title: '이지 런', distance: 6, estMin: 38, target: '5:50–6:20 /km', focus: '회복 페이스', done: false },
  { day: '토', type: 'strength', title: '근력 · 보강 40분', distance: 0, estMin: 40, focus: '코어 · 둔근 · 발목 안정성', done: false },
  { day: '일', type: 'long', title: '롱런 18km', distance: 18, estMin: 115, target: '6:00–6:20 /km', focus: '후반 5km 살짝 빌드업', done: false },
];

// ---- Last week summary (context for S0 / history) ----
const LAST_WEEK = {
  km: 41.2, doneCount: 5, totalCount: 6, completion: 83,
  avgPace: '5:48', avgHr: 154, longest: 16.0, days: [6, 7, 8, 0, 6, 0, 16],
  note: '주간 거리 목표(40km) 달성. 인터벌 수행률이 높아졌어요.',
};

// ---- Multi-week history for 기록 탭 ----
const HISTORY_WEEKS = [
  { label: '이번 주', km: 13.2, sessions: '2/6', completion: 33, current: true },
  { label: '지난 주', km: 41.2, sessions: '5/6', completion: 83 },
  { label: '2주 전', km: 38.6, sessions: '5/6', completion: 83 },
  { label: '3주 전', km: 34.0, sessions: '4/6', completion: 67 },
  { label: '4주 전', km: 29.5, sessions: '4/5', completion: 80 },
];

const RECENT_RUNS = [
  { date: '6월 3일 화', type: 'interval', distance: 7.18, pace: '5:02', avgHr: 168, min: 44 },
  { date: '6월 2일 월', type: 'easy', distance: 6.04, pace: '6:11', avgHr: 142, min: 37 },
  { date: '6월 1일 일', type: 'long', distance: 16.0, pace: '6:08', avgHr: 151, min: 98 },
  { date: '5월 30일 금', type: 'tempo', distance: 8.0, pace: '5:12', avgHr: 165, min: 47 },
  { date: '5월 29일 목', type: 'easy', distance: 6.1, pace: '6:18', avgHr: 140, min: 38 },
];

// ---- Goal / runner profile ----
const PROFILE = {
  name: '지훈', goal: '10K 50분 돌파', goalDate: 'D-38', weeklyTarget: 45,
  paceGoal: '5:00 /km', restHr: 52, vo2: 48, maxHr: 188,
};

// ---- Coach tone copy. Keyed by tweakable tone. ----
// hero greeting (post-workout), review intro, encouragement.
const COACH_TONE = {
  calm: {
    label: '차분한 데이터형',
    s2title: '훈련을 기록할까요?',
    s2sub: '기록을 남기면 다음 추천이 더 정확해져요.',
    s3verb: '완료',
    reviewIntro: (km, pace) => `${km}km를 ${pace}/km로 마쳤어요. 목표 페이스 대비 안정적인 분포입니다.`,
    interval: (m) => m.feel <= 2
      ? '후반 페이스 저하가 보입니다. 인터벌 반복 수를 다음 주 6개로 조정하는 것을 권장해요.'
      : '심박과 페이스가 목표 구간에 잘 들어왔습니다. 현재 부하를 유지하세요.',
    tempo: '임계 페이스 유지 시간이 목표에 근접했습니다. 다음 템포에서 5분 연장을 시도해볼 만해요.',
  },
  warm: {
    label: '따뜻한 격려형',
    s2title: '오늘도 수고했어요 👏',
    s2sub: '오늘의 기록을 남기면 다음 훈련이 더 똑똑해져요.',
    s3verb: '완료',
    reviewIntro: (km, pace) => `${km}km나 달렸네요, 정말 잘했어요! ${pace}/km면 충분히 멋진 페이스예요.`,
    interval: (m) => m.feel <= 2
      ? '마지막이 힘들었죠? 충분히 잘 버텼어요. 다음엔 조금 여유를 두고 가봐요.'
      : '오늘 리듬 정말 좋았어요. 이 느낌 그대로 가져가요!',
    tempo: '임계 구간을 잘 버텼어요. 몸이 점점 단단해지고 있어요.',
  },
  strict: {
    label: '엄격한 코치형',
    s2title: '기록부터 입력한다.',
    s2sub: '데이터 없는 훈련은 추측일 뿐이다. 정확히 기록하자.',
    s3verb: '완료',
    reviewIntro: (km, pace) => `${km}km · ${pace}/km. 계획은 지켰다. 다만 디테일을 보자.`,
    interval: (m) => m.feel <= 2
      ? '후반 붕괴. 출발 페이스가 빨랐다. 다음엔 첫 2개를 의도적으로 눌러라.'
      : '목표 구간 적중. 방심하지 말고 폼을 끝까지 유지해라.',
    tempo: '임계 유지력은 합격선. 다음 단계로 부하를 올린다.',
  },
};

const FEEL_OPTIONS = [
  { v: 1, emoji: '😰', label: '매우 힘듦' },
  { v: 2, emoji: '😐', label: '힘듦' },
  { v: 3, emoji: '🙂', label: '좋음' },
  { v: 4, emoji: '💪', label: '아주 좋음' },
];

const BODY_PARTS = ['무릎', '발목', '정강이', '햄스트링', '종아리', '발바닥', '고관절', '허리'];

Object.assign(window, {
  WORKOUT_TYPES, WEEK_DAYS, TODAY_INDEX, WEEK_PLAN, LAST_WEEK,
  HISTORY_WEEKS, RECENT_RUNS, PROFILE, COACH_TONE, FEEL_OPTIONS, BODY_PARTS,
});
