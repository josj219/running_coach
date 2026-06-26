// API 클라이언트 — fetch 래퍼 + SSE 리더 + 토큰(JWT) 관리
const BASE = import.meta.env.VITE_API_BASE || '';
const TOKEN_KEY = 'auth_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => { if (t) localStorage.setItem(TOKEN_KEY, t); };
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

function authHeaders(extra = {}) {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}`, ...extra } : { ...extra };
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...authHeaders(options.headers) },
      ...options,
    });
  } catch {
    // fetch 자체가 reject — 연결 단절(백그라운드 suspend·터널 끊김 등).
    // 서버는 처리 중이거나 이미 끝냈을 수 있어 'NETWORK'로 표시 → 호출부가 결과를 폴링해 복구한다.
    const err = new Error('연결이 끊겼어요. 잠시 후 다시 시도해 주세요.');
    err.code = 'NETWORK';
    err.status = 0;
    throw err;
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401) {
      // 토큰 만료/무효 → 로그아웃 신호. App이 받아 로그인 화면으로 전환.
      clearToken();
      window.dispatchEvent(new Event('auth:logout'));
    }
    const detail = body?.detail || body?.error || {};
    const err = new Error(detail.message || `요청 실패 (${res.status})`);
    err.code = detail.code || 'ERROR';
    err.status = res.status;
    throw err;
  }
  return body;
}

export const api = {
  login: (email, password) => request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/api/auth/me'),
  onboard: (data) => request('/api/auth/onboard', { method: 'POST', body: JSON.stringify(data) }),
  today: () => request('/api/today'),
  profile: () => request('/api/profile'),
  patchProfile: (data) => request('/api/profile', { method: 'PATCH', body: JSON.stringify(data) }),
  goal: () => request('/api/goal'),
  putGoal: (data) => request('/api/goal', { method: 'PUT', body: JSON.stringify(data) }),
  settings: () => request('/api/settings'),
  availability: () => request('/api/availability'),
  putAvailability: (slots) => request('/api/availability', { method: 'PUT', body: JSON.stringify({ slots }) }),
  patchSettings: (data) => request('/api/settings', { method: 'PATCH', body: JSON.stringify(data) }),
  currentWeek: () => request('/api/weeks/current'),
  weeklyStats: (weeks = 6) => request(`/api/stats/weekly?weeks=${weeks}`),
  logs: (limit = 30) => request(`/api/workout-logs?limit=${limit}`),
  saveLog: (data) => request('/api/workout-logs', { method: 'POST', body: JSON.stringify(data) }),
  analyzeImage: (image_b64, media_type = 'image/jpeg') =>
    request('/api/workout-logs/analyze-image', { method: 'POST', body: JSON.stringify({ image_b64, media_type }) }),
  generateWeek: (data) => request('/api/weekly-plans', { method: 'POST', body: JSON.stringify(data) }),
  adjustWeek: (reason) => request('/api/weeks/current/adjust', { method: 'POST', body: JSON.stringify({ reason }) }),
  evaluateWeek: () => request('/api/weeks/current/evaluation', { method: 'POST' }),
  generateDaily: (data) => request('/api/daily-plans', { method: 'POST', body: JSON.stringify(data) }),
  integrations: () => request('/api/integrations'),
  stravaAuthUrl: () => request('/api/integrations/strava/authorize-url'),
  stravaActivities: (limit = 5) => request(`/api/integrations/strava/activities?limit=${limit}`),
  stravaDisconnect: () => request('/api/integrations/strava', { method: 'DELETE' }),
};

// 끊긴 생성의 결과가 서버에 저장됐는지 확인 — 복구용. job: {type, date?}
// - weekly  : 이번 주 계획 존재(200) 여부
// - daily   : 오늘 당일 카드(daily_plan) 존재 여부
// - evaluate: 이번 주 성장 리포트(evaluation.coach_message) 저장 여부
// - adjust  : 조정은 세션 제자리 수정뿐이라 별도 마커가 없다 → 연결만 회복되면(현재 주 재조회 성공)
//             충분하다고 본다. 조정 결과는 세션에 반영돼 있으므로 다시 불러오면 보인다.
export async function genResult(job) {
  if (job?.type === 'weekly') {
    try { await api.currentWeek(); return true; }
    catch (e) { if (e.status === 404) return false; throw e; }
  }
  if (job?.type === 'daily') {
    const t = await api.today();
    return !!(t.daily_plan && t.today === job.date);
  }
  if (job?.type === 'evaluate') {
    const w = await api.currentWeek();
    return !!w.evaluation?.coach_message;
  }
  if (job?.type === 'adjust') {
    await api.currentWeek();  // 404/네트워크면 throw → 폴링 계속, 성공이면 복구
    return true;
  }
  return false;
}

// 리뷰 SSE 스트림: onToken(text), onDone(review), onError(err)
export async function streamReview(logId, { onToken, onDone, onError }) {
  try {
    const res = await fetch(`${BASE}/api/workout-logs/${logId}/review`, {
      method: 'POST',
      headers: authHeaders({ Accept: 'text/event-stream' }),
    });
    if (!res.ok || !res.body) throw new Error(`리뷰 생성 실패 (${res.status})`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let event = 'message';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) {
          const data = line.slice(5).replace(/^ /, '');
          if (event === 'token') onToken?.(data);
          else if (event === 'done') onDone?.(JSON.parse(data));
          else if (event === 'error') throw Object.assign(new Error(JSON.parse(data).message), { code: 'AI_UNAVAILABLE' });
        }
      }
    }
  } catch (err) {
    onError?.(err);
  }
}
