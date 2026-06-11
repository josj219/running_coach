// 시나리오 기반 UI 점검 — 아이폰 뷰포트로 전 탭 + 기록 시트 스크린샷
import { chromium } from 'playwright';
import fs from 'fs';

const OUT = '/tmp/coach-shots';
fs.mkdirSync(OUT, { recursive: true });
const BASE = 'http://localhost:5173';

const SCENARIO = process.env.SCENARIO || 'main'; // main | noplan

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
page.on('console', (m) => m.type() === 'error' && console.log('CONSOLE ERROR:', m.text()));
page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message));

const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` });
const tab = async (label) => { await page.getByRole('button', { name: label, exact: true }).click(); await page.waitForTimeout(600); };

// ── 시나리오: 주의 첫 실행(계획 없음) → 자동 시트 → 특이 일정 입력 → 생성 ──
if (SCENARIO === 'noplan') {
  await page.goto(BASE);
  await page.waitForTimeout(2000); // NO_PLAN 감지 → 자동 오픈
  await shot('n1-auto-plan-sheet');
  await page.getByPlaceholder(/기본 시간표와 다른 점만/).fill('수요일 회식, 금요일 부산 출장');
  await page.getByPlaceholder(/발목 통증 없음/).fill('컨디션 좋음, 통증 없음');
  await shot('n2-special-filled');
  await page.getByText('훈련 가능 시간 검토하고 7일 계획 생성').click();
  await page.waitForTimeout(2500); // COACH_MOCK 생성 → week 탭 전환
  await shot('n3-week-generated');
  // 닫은 주에는 다시 안 뜨는지: 새로고침 후 시트 미노출
  await page.goto(BASE);
  await page.waitForTimeout(1500);
  await shot('n4-today-after');
  await browser.close();
  console.log('done(noplan) →', OUT);
  process.exit(0);
}

await page.goto(BASE);
await page.waitForTimeout(1800);
await shot('01-today-dark');

// 당일 AI 카드 생성 (컨디션 칩 → 생성)
const dailyBtn = page.getByText('워밍업·메인·쿨다운 카드 만들기');
if (await dailyBtn.count()) {
  await page.getByText('컨디션 좋아요').click();
  await dailyBtn.click();
  await page.waitForTimeout(2000);
  await shot('01b-daily-card');
}

// 기록 시트 열기 (PRE_WORKOUT일 때만 존재)
const recordBtn = page.getByText('다녀왔어요 · 기록 입력');
if (await recordBtn.count()) {
  await recordBtn.click();
  await page.waitForTimeout(500);
  await shot('02-record-sheet');
  // 상세 입력 펼치기
  await page.getByText('심박·케이던스·통증 자세히 입력').click();
  await page.waitForTimeout(400);
  await shot('03-record-detail');
  // 거리/시간 입력 → 자동 페이스
  await page.locator('input[placeholder="0.0"]').fill('5.2');
  await page.locator('input[placeholder="분"]').fill('32');
  await page.locator('input[placeholder="초"]').fill('12');
  await page.waitForTimeout(300);
  await shot('04-record-filled');
  // 저장 → 리뷰 스트림
  await page.getByText('저장하고 리뷰 받기').click();
  await page.waitForTimeout(2500);
  await shot('05-review');
  await page.getByRole('button', { name: '확인' }).click();
  await page.waitForTimeout(1200);
  await shot('06-today-reviewed');
}

await tab('이번 주');
await shot('07-week');
await tab('기록');
await shot('08-history');
await tab('설정');
await shot('09-settings-dark');

// 훈련 가능 시간 편집 — 슬롯 수정 폼 + 저장
await page.getByLabel('편집').first().click();
await page.waitForTimeout(400);
await shot('09b-availability-edit');
await page.getByRole('button', { name: '저장' }).click();
await page.waitForTimeout(600);
await shot('09c-availability-saved');

// 라이트 테마
await page.getByRole('button', { name: '라이트', exact: true }).click();
await page.waitForTimeout(400);
await shot('10-settings-light');
await tab('오늘');
await shot('11-today-light');

await browser.close();
console.log('done →', OUT);
