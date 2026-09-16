// 루트 — 인증 게이트(로그인/온보딩) + 탭 네비게이션 + 테마/강조색 + 오늘/대시보드 데이터 공유
import React, { useCallback, useEffect, useState } from 'react';
import { api, genResult, getToken } from './api.js';
import { pendingGen, pollUntil, reconcileOnce } from './recover.js';
import { isoWeekKey } from './workouts.js';
import TabBar from './components/TabBar.jsx';
import RecordSheet from './components/RecordSheet.jsx';
import AddRunSheet from './components/AddRunSheet.jsx';
import PlanSheet from './components/PlanSheet.jsx';
import { Banner, Spinner } from './components/Ui.jsx';
import Login from './Login.jsx';
import Onboarding from './Onboarding.jsx';
import Home from './tabs/Home.jsx';
import Today from './tabs/Today.jsx';
import Week from './tabs/Week.jsx';
import Settings from './tabs/Settings.jsx';

// 홈(대시보드)이 첫 화면 — 목표 격차를 매일 보게 한다. 옛 '기록' 탭은 홈 하단에 흡수.
const TABS = [
  { id: 'home', icon: 'House', label: '홈' },
  { id: 'today', icon: 'Footprints', label: '오늘' },
  { id: 'week', icon: 'CalendarDays', label: '이번 주' },
  { id: 'settings', icon: 'Settings', label: '설정' },
];

export default function App() {
  // 인증: loading | login | onboarding | app
  const [authState, setAuthState] = useState('loading');
  const [user, setUser] = useState(null);

  const [tab, setTab] = useState('home');
  const [theme, setThemeState] = useState(localStorage.getItem('theme') || 'dark');
  const [accent, setAccentState] = useState(localStorage.getItem('accent') || '#0088ff');
  // 기록 시트 대상: null | { date, session, log, prefill } — 오늘/주간 탭 모두 임의 일자로 연다.
  // prefill: 계획에 없던 훈련을 연동 활동으로 열 때의 초기값(session 없음)
  const [recordTarget, setRecordTarget] = useState(null);
  // 기록 저장 시 증가 → 주간 탭이 의존성으로 받아 자동 리로드
  const [recordVersion, setRecordVersion] = useState(0);
  const [showPlan, setShowPlan] = useState(false);
  const [showAddRun, setShowAddRun] = useState(false); // 계획에 없던 훈련 추가 시트 (홈 → 최근 훈련 ＋)
  // 끊긴 생성 복구: 복구 한 바퀴 끝날 때마다 증가(자식 카드가 스피너 해제 판단), 실패 시 안내 배너
  const [recoverTick, setRecoverTick] = useState(0);
  const [genNotice, setGenNotice] = useState(null);

  const [today, setToday] = useState(null);
  const [todayLoading, setTodayLoading] = useState(true);
  const [todayError, setTodayError] = useState(null);
  // 대시보드(목표 격차·궤적) — 오늘 데이터와 같이 갱신(기록 저장 시 예상 기록이 바뀐다)
  const [dash, setDash] = useState(null);
  const [dashError, setDashError] = useState(null);

  const setTheme = (v) => { setThemeState(v); localStorage.setItem('theme', v); };
  const setAccent = (v) => { setAccentState(v); localStorage.setItem('accent', v); };

  // 부팅 시 토큰 확인 + 로그아웃 이벤트(401) 처리
  useEffect(() => {
    let mounted = true;
    const onLogout = () => { setUser(null); setAuthState('login'); };
    window.addEventListener('auth:logout', onLogout);
    (async () => {
      if (!getToken()) { setAuthState('login'); return; }
      try {
        const me = await api.me();
        if (!mounted) return;
        setUser(me);
        setAuthState(me.onboarded ? 'app' : 'onboarding');
      } catch { /* 401 → onLogout이 처리 */ }
    })();
    return () => { mounted = false; window.removeEventListener('auth:logout', onLogout); };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', theme === 'dark' ? '#000000' : '#f2f2f7');
  }, [theme]);
  useEffect(() => { document.documentElement.style.setProperty('--tint', accent); }, [accent]);

  const refreshToday = useCallback(async () => {
    setTodayError(null);
    const [t, d] = await Promise.allSettled([api.today(), api.dashboard()]);
    if (t.status === 'fulfilled') setToday(t.value); else setTodayError(t.reason?.message || '불러오지 못했어요.');
    if (d.status === 'fulfilled') { setDash(d.value); setDashError(null); }
    else setDashError(d.reason?.message || '불러오지 못했어요.');
    setTodayLoading(false);
  }, []);
  // 앱 진입 상태일 때만 오늘 데이터 로드(미인증 시 401 방지)
  useEffect(() => { if (authState === 'app') refreshToday(); }, [authState, refreshToday]);

  // 끊긴 생성 복구 — 부팅 + 앱 복귀(visible) 시 pendingGen이 있으면 서버 결과를 폴링한다.
  // 주간/당일 생성 중 백그라운드 suspend·탭 전환·새로고침으로 연결이 끊겨도,
  // 서버가 저장한 결과를 찾아 거짓 에러 없이 화면을 복구한다(없으면 부드러운 재시도 안내).
  useEffect(() => {
    if (authState !== 'app') return;
    let active = true;
    const reconcile = async () => {
      const job = pendingGen.get();
      if (!job) return;
      const res = await reconcileOnce(() => pollUntil(() => genResult(job)));
      if (!active || res === 'busy') return;  // 호출부(모달/카드)가 이미 처리 중
      pendingGen.clear();
      const LABELS = { weekly: '주간 계획 생성', daily: '오늘 훈련 생성',
                       adjust: '계획 조정', evaluate: '성장 리포트' };
      if (res === 'found') {
        await refreshToday();
        setRecordVersion((v) => v + 1);  // 주간 탭 리로드
        // 당일 외(주간/조정/평가)는 주간 탭에서 시작됐으니 그쪽으로 돌려보낸다.
        if (job.type !== 'daily') { setShowPlan(false); setTab('week'); }
      } else {
        setGenNotice(`${LABELS[job.type] || '작업'}이(가) 끝나지 않았어요. 다시 시도해 주세요.`);
      }
      setRecoverTick((t) => t + 1);  // 자식 카드가 스피너 상태를 재평가
    };
    reconcile();  // 부팅 시 1회
    const onVis = () => { if (document.visibilityState === 'visible') reconcile(); };
    document.addEventListener('visibilitychange', onVis);
    return () => { active = false; document.removeEventListener('visibilitychange', onVis); };
  }, [authState, refreshToday]);

  // Strava OAuth 복귀 시 설정 탭으로
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('strava')) setTab('settings');
  }, []);

  // 주의 첫 실행: 계획 없으면 주간 계획 시트 자동 오픈 (주 1회, 닫으면 그 주는 다시 안 뜸)
  useEffect(() => {
    if (authState === 'app' && today?.state === 'NO_PLAN'
        && localStorage.getItem('planPromptWeek') !== isoWeekKey()) {
      setShowPlan(true);
    }
  }, [authState, today?.state]);

  const closePlanSheet = () => {
    localStorage.setItem('planPromptWeek', isoWeekKey());
    setShowPlan(false);
  };

  if (authState === 'loading') return <div className="app-frame"><Spinner /></div>;
  if (authState === 'login') {
    return <Login onLoggedIn={(u) => { setUser(u); setAuthState(u.onboarded ? 'app' : 'onboarding'); }} />;
  }
  if (authState === 'onboarding') {
    return <Onboarding user={user} onDone={(u) => { setUser(u); setAuthState('app'); }} />;
  }

  return (
    <div className="app-frame">
      {genNotice && (
        <div style={{ padding: '8px 16px 0' }}>
          <Banner tone="warn" action="확인" onAction={() => setGenNotice(null)}>{genNotice}</Banner>
        </div>
      )}
      <div className="scroll-area">
        {tab === 'home' && (
          <Home dash={dash} dashError={dashError} loading={todayLoading} refresh={refreshToday}
            today={today} reloadKey={recordVersion}
            goToday={() => setTab('today')} onPlan={() => setShowPlan(true)} goSettings={() => setTab('settings')}
            onAddRun={() => setShowAddRun(true)} onEdit={(log) => setRecordTarget({ date: log.log_date, session: null, log })} />
        )}
        {tab === 'today' && (
          <Today data={today} loading={todayLoading} error={todayError} refresh={refreshToday}
            recoverTick={recoverTick} dash={dash} goHome={() => setTab('home')}
            onAddRecord={() => setRecordTarget({ date: today.today, session: today.session, log: null })}
            onEditRecord={(log) => setRecordTarget({ date: today.today, session: today.session, log })}
            onRecord={() => setRecordTarget({ date: today.today, session: today.session, log: today.log })}
            goWeek={() => setTab('week')} onPlan={() => setShowPlan(true)} />
        )}
        {tab === 'week' && (
          <Week refreshToday={refreshToday} reloadKey={recordVersion}
            onRecord={(s) => setRecordTarget({ date: s.session_date, session: s, log: s.log })}
            onPlan={() => setShowPlan(true)} />
        )}
        {tab === 'settings' && (
          <Settings onChanged={refreshToday} theme={theme} setTheme={setTheme} accent={accent} setAccent={setAccent} />
        )}
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {showAddRun && (
        <AddRunSheet onClose={() => setShowAddRun(false)} onImported={() => { refreshToday(); setRecordVersion((v) => v + 1); }}
          onPick={(date, activity, existing) => {
            setShowAddRun(false);
            // 연동 활동이면 그 값으로 프리필, 직접 입력이면 빈 폼(그날 기록이 있으면 수정으로)
            setRecordTarget({ date, session: null, log: existing, prefill: activity || undefined });
          }} />
      )}

      {recordTarget && (
        <RecordSheet session={recordTarget.session} logDate={recordTarget.date} existingLog={recordTarget.log}
          prefill={recordTarget.prefill}
          onClose={(saved) => {
            setRecordTarget(null);
            if (saved) { refreshToday(); setRecordVersion((v) => v + 1); }
          }} />
      )}

      {showPlan && (
        <PlanSheet onClose={closePlanSheet}
          goSettings={() => { closePlanSheet(); setTab('settings'); }}
          onDone={() => { closePlanSheet(); refreshToday(); setTab('week'); }} />
      )}
    </div>
  );
}
