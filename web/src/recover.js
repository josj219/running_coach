// 끊긴 AI 생성 복구 — 의도(pendingGen)를 localStorage에 남기고, 재진입 시 서버 결과를 폴링한다.
//
// 배경: 주간/당일 생성은 Claude 응답이 끝날 때까지 fetch 연결을 여는 '긴 단일 요청'이다.
// 모바일 백그라운드 suspend·탭 전환 시 그 연결이 끊겨 fetch가 reject → 거짓 에러가 뜬다.
// 하지만 서버는 결과를 upsert+commit하므로, 재진입해서 결과 존재만 확인하면 복구할 수 있다.

const KEY = 'pendingGen';
const MAX_AGE_MS = 10 * 60 * 1000; // 오래된(>10분) 의도는 무시 — 정전된(stuck) 플래그 방지
const ls = () => (typeof localStorage !== 'undefined' ? localStorage : null);

export const pendingGen = {
  set(job) {
    const s = ls();
    if (s) { try { s.setItem(KEY, JSON.stringify({ ...job, startedAt: Date.now() })); } catch { /* quota */ } }
  },
  get() {
    const s = ls();
    if (!s) return null;
    let job;
    try { job = JSON.parse(s.getItem(KEY)); } catch { return null; }
    if (!job) return null;
    if (job.startedAt && Date.now() - job.startedAt > MAX_AGE_MS) { s.removeItem(KEY); return null; }
    return job;
  },
  clear() { const s = ls(); if (s) s.removeItem(KEY); },
};

const defaultSleep = (ms) => new Promise((r) => setTimeout(r, ms));

// check(i)가 truthy를 반환할 때까지 폴링. 'found' | 'timeout'. check 예외는 '미존재'로 간주.
// 기본 15회 × 3초 ≈ 45초 — 재진입 시 서버가 아직 생성 중일 수 있는 구간을 덮는다.
export async function pollUntil(check, { attempts = 15, intervalMs = 3000, sleep = defaultSleep } = {}) {
  for (let i = 0; i < attempts; i++) {
    let ok = false;
    try { ok = await check(i); } catch { ok = false; }
    if (ok) return 'found';
    if (i < attempts - 1) await sleep(intervalMs);
  }
  return 'timeout';
}

// 동시 복구 방지 락 — 호출부(모달/카드)와 App 핸들러가 같은 resume 틱에 겹쳐 폴링하지 않게 한다.
// 먼저 진입한 쪽이 결과를 처리하고, 늦은 쪽은 'busy'를 받고 비켜선다.
let reconciling = false;
export async function reconcileOnce(runner) {
  if (reconciling) return 'busy';
  reconciling = true;
  try { return await runner(); } finally { reconciling = false; }
}
