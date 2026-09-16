// Full PWA journey against the isolated COACH_MOCK API. Never target production writes.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { execFileSync } from 'node:child_process';

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:15173';
assert(new URL(BASE).hostname === '127.0.0.1' || new URL(BASE).hostname === 'localhost');
const OUT = process.env.E2E_OUT || '/private/tmp/coach-journey-e2e';
await fs.mkdir(OUT, { recursive: true });
const browser = await chromium.launch({ channel: process.env.E2E_CHANNEL || 'chrome', headless: true });
const page = await browser.newPage({ timezoneId: 'Asia/Seoul', viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const errors = [];
page.on('pageerror', (e) => { errors.push(e.message); console.error('PAGE ERROR', e.message); });
const fixture = JSON.parse(execFileSync(process.env.E2E_PYTHON || '.venv/bin/python', ['-m', 'app.browser_fixture'], {
  cwd: '../api', env: { ...process.env, DATABASE_URL: process.env.E2E_DATABASE_URL || 'sqlite+aiosqlite:////private/tmp/coach-journey-browser.db', COACH_MOCK: '1', TZ: 'Asia/Seoul', PYTHONDONTWRITEBYTECODE: '1' }, encoding: 'utf8'
}));
const checks = [];
const check = (name) => { checks.push(name); console.log(`PASS ${name}`); };
let token;
const request = async (path, body, method = 'GET') => {
  const r = await fetch(`${BASE}${path}`, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) });
  assert(r.ok, `${method} ${path} ${r.status}`); return r.json();
};
const tab = (name) => page.getByRole('button', { name, exact: true }).click();
try {
  await page.goto(BASE);
  await page.getByPlaceholder('이메일', { exact: true }).fill(fixture.email);
  await page.getByPlaceholder('비밀번호', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await page.getByText('PB 참고 추정', { exact: true }).waitFor();
  token = await page.evaluate(() => localStorage.getItem('auth_token'));
  let dash = await request('/api/dashboard');
  assert.equal(dash.current.data_status.record_count, 0);
  assert(dash.series.every((p) => p.predicted_sec === null));
  await page.screenshot({ path: `${OUT}/01-pb-only-home.png`, fullPage: true });
  check('J01 PB-only home: data status, no fabricated historical line');

  await tab('오늘');
  await page.getByRole('button', { name: '오늘의 훈련 만들기', exact: true }).click();
  await page.getByRole('button', { name: '컨디션 변경', exact: true }).waitFor();
  await page.getByRole('button', { name: '컨디션 변경', exact: true }).click();
  await page.getByLabel('컨디션 변경 사유').fill('수면 부족, 계획을 확인하고 싶어요');
  await page.getByRole('button', { name: '변경안 확인', exact: true }).click();
  await page.getByText('변경 전', { exact: true }).waitFor();
  await page.getByText('변경 후', { exact: true }).waitFor();
  await page.screenshot({ path: `${OUT}/02-condition-preview.png`, fullPage: true });
  await page.getByRole('button', { name: '이 변경을 오늘·주간 계획에 적용', exact: true }).click();
  await page.getByRole('button', { name: '컨디션 변경', exact: true }).waitFor();
  check('J09 existing daily card: condition preview and explicit apply');

  await page.getByRole('button', { name: '오늘 새 운동 추가', exact: true }).click();
  await page.getByPlaceholder('0.0', { exact: true }).fill('1');
  await page.getByPlaceholder('분', { exact: true }).fill('6');
  await page.getByRole('button', { name: '저장하고 리뷰 받기', exact: true }).click();
  await page.getByRole('button', { name: '이 개선점을 다음 계획 과제로 선택', exact: true }).waitFor();
  await page.getByRole('button', { name: '이 개선점을 다음 계획 과제로 선택', exact: true }).click();
  await page.getByRole('button', { name: '다음 계획 과제로 저장됨', exact: true }).waitFor();
  await page.getByRole('button', { name: '확인', exact: true }).click();
  let today = await request('/api/today');
  assert.equal(today.logs.length, 1);
  assert.equal(today.session.status, 'partial');
  check('J06 1km recorded as partial; J08 select review coaching task');

  await page.getByRole('button', { name: '오늘 새 운동 추가', exact: true }).click();
  await page.getByPlaceholder('0.0', { exact: true }).fill('8');
  await page.getByPlaceholder('분', { exact: true }).fill('48');
  await page.getByRole('button', { name: '저장하고 리뷰 받기', exact: true }).click();
  await page.getByRole('button', { name: '이 개선점을 다음 계획 과제로 선택', exact: true }).waitFor();
  await page.getByRole('button', { name: '확인', exact: true }).click();
  today = await request('/api/today');
  assert.equal(today.logs.length, 2); assert.equal(today.day_km, 9);
  const originalIds = today.logs.map((l) => l.id);
  await page.getByText('이지 런 · 8km', { exact: true }).waitFor();
  await page.getByRole('button', { name: '이 기록 수정', exact: true }).first().click();
  assert.equal(await page.getByPlaceholder('0.0', { exact: true }).inputValue(), '8');
  await page.getByPlaceholder('0.0', { exact: true }).fill('7');
  await page.getByPlaceholder('분', { exact: true }).fill('42');
  await page.getByLabel('수정 사유').fill('GPS 거리 정정');
  await page.getByRole('button', { name: '저장하고 리뷰 받기', exact: true }).click();
  await page.getByRole('button', { name: '이 개선점을 다음 계획 과제로 선택', exact: true }).waitFor();
  await page.getByRole('button', { name: '확인', exact: true }).click();
  today = await request('/api/today');
  assert.equal(today.logs.length, 2); assert.equal(today.day_km, 8);
  assert.deepEqual(today.logs.map((l) => l.id), originalIds);
  await page.screenshot({ path: `${OUT}/03-two-workouts-edited.png`, fullPage: true });
  check('J03 same-day workouts stay separate; editing preserves IDs and other record');

  await tab('이번 주');
  await page.getByText(/참여율/).first().waitFor();
  await page.getByRole('button', { name: '성장 리포트 만들기', exact: true }).click();
  await page.getByRole('button', { name: '이 평가를 다음 계획 과제로 선택', exact: true }).waitFor();
  await page.screenshot({ path: `${OUT}/04-week-report.png`, fullPage: true });
  check('J06 weekly participation vs fulfillment; weekly evaluation rendered');

  await tab('홈');
  await page.getByRole('button', { name: /미반영 활동.*확인 및 기록 추가/ }).click();
  await page.getByText('미반영 활동 3건', { exact: true }).waitFor();
  for (const checkbox of await page.getByRole('checkbox').all()) await checkbox.check();
  await page.getByRole('button', { name: '선택한 3건 확인 후 반영', exact: true }).click();
  await page.getByText('미반영 활동 0건', { exact: true }).waitFor();
  const importedLogs = await request('/api/workout-logs');
  assert.equal(importedLogs.items.length, 4);
  check('J02 confirmed import: cross-provider duplicate counted once, distinct second run preserved');
  await page.screenshot({ path: `${OUT}/05-import-status.png`, fullPage: true });
  await page.getByRole('button', { name: '닫기', exact: true }).click();
  await page.getByRole('button', { name: '성장 기록실 · 주·월·목표 비교', exact: true }).click();
  await page.getByText(/비교 불가 —/).waitFor();
  await page.getByLabel('비교 기간').selectOption('month');
  await page.getByText(/비교 불가 —/).waitFor();
  await page.getByLabel('당시 평가 선택').selectOption({ index: 1 });
  await page.getByText(/당시 평가 ·/).waitFor();
  await page.getByText(/비교 불가 —/).scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/06-growth-history.png`, fullPage: true });
  check('J04/J10 historical assessments and month comparison, insufficient sample state');

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: `${OUT}/07-desktop.png`, fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
  assert.deepEqual(errors, []);
  check('mobile and desktop render without page errors or horizontal overflow');
  await fs.writeFile(`${OUT}/results.json`, JSON.stringify({ checks, errors, completed_at: new Date().toISOString(), environment: 'local COACH_MOCK SQLite' }, null, 2));
} catch (e) {
  await page.screenshot({ path: `${OUT}/failure.png`, fullPage: true });
  console.error((await page.locator('body').innerText()).slice(-7000));
  throw e;
} finally { await browser.close(); }
