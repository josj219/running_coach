// API 클라이언트 — PWA와 동일 백엔드.
// 실기기 테스트 시 apiBaseUrl을 맥의 LAN IP로 바꿔주세요 (app.json extra).
import Constants from 'expo-constants';

const BASE = Constants.expoConfig?.extra?.apiBaseUrl || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail || body?.error || {};
    const err = new Error(detail.message || `요청 실패 (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return body;
}

export const api = {
  today: () => request('/api/today'),
  profile: () => request('/api/profile'),
  goal: () => request('/api/goal'),
  settings: () => request('/api/settings'),
  availability: () => request('/api/availability'),
  currentWeek: () => request('/api/weeks/current'),
  weeklyStats: (weeks = 6) => request(`/api/stats/weekly?weeks=${weeks}`),
  logs: (limit = 30) => request(`/api/workout-logs?limit=${limit}`),
  saveLog: (data) => request('/api/workout-logs', { method: 'POST', body: JSON.stringify(data) }),
  // RN fetch는 SSE 스트림이 불안정 → 비스트리밍(JSON) 리뷰 사용
  review: (logId) => request(`/api/workout-logs/${logId}/review`, {
    method: 'POST', headers: { Accept: 'application/json' },
  }),
  generateWeek: (data) => request('/api/weekly-plans', { method: 'POST', body: JSON.stringify(data) }),
  adjustWeek: (reason) => request('/api/weeks/current/adjust', { method: 'POST', body: JSON.stringify({ reason }) }),
  evaluateWeek: () => request('/api/weeks/current/evaluation', { method: 'POST' }),
  generateDaily: (data) => request('/api/daily-plans', { method: 'POST', body: JSON.stringify(data) }),
  integrations: () => request('/api/integrations'),
  stravaAuthUrl: () => request('/api/integrations/strava/authorize-url'),
  stravaActivities: (limit = 5) => request(`/api/integrations/strava/activities?limit=${limit}`),
  stravaDisconnect: () => request('/api/integrations/strava', { method: 'DELETE' }),
};
