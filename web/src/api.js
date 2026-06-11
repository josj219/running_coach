// API 클라이언트 — fetch 래퍼 + SSE 리더
const BASE = import.meta.env.VITE_API_BASE || '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail || body?.error || {};
    const err = new Error(detail.message || `요청 실패 (${res.status})`);
    err.code = detail.code || 'ERROR';
    err.status = res.status;
    throw err;
  }
  return body;
}

export const api = {
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
  generateWeek: (data) => request('/api/weekly-plans', { method: 'POST', body: JSON.stringify(data) }),
  adjustWeek: (reason) => request('/api/weeks/current/adjust', { method: 'POST', body: JSON.stringify({ reason }) }),
  evaluateWeek: () => request('/api/weeks/current/evaluation', { method: 'POST' }),
  generateDaily: (data) => request('/api/daily-plans', { method: 'POST', body: JSON.stringify(data) }),
  integrations: () => request('/api/integrations'),
  stravaAuthUrl: () => request('/api/integrations/strava/authorize-url'),
  stravaActivities: (limit = 5) => request(`/api/integrations/strava/activities?limit=${limit}`),
  stravaDisconnect: () => request('/api/integrations/strava', { method: 'DELETE' }),
};

// 리뷰 SSE 스트림: onToken(text), onDone(review), onError(err)
export async function streamReview(logId, { onToken, onDone, onError }) {
  try {
    const res = await fetch(`${BASE}/api/workout-logs/${logId}/review`, {
      method: 'POST',
      headers: { Accept: 'text/event-stream' },
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
