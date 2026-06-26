// 루트 — 인증 게이트(로그인/온보딩) + 탭 네비게이션 + 테마/강조색 + 오늘 데이터 공유
import React, { useCallback, useEffect, useState } from 'react';
import { api, genResult, getToken } from './api.js';
import { pendingGen, pollUntil, reconcileOnce } from './recover.js';
import { isoWeekKey } from './workouts.js';
import TabBar from './components/TabBar.jsx';
import RecordSheet from './components/RecordSheet.jsx';
import PlanSheet from './components/PlanSheet.jsx';
import { Banner, Spinner } from './components/Ui.jsx';
import Login from './Login.jsx';
import Onboarding from './Onboarding.jsx';
import Today from './tabs/Today.jsx';
import Week from './tabs/Week.jsx';
import History from './tabs/History.jsx';
import Settings from './tabs/Settings.jsx';

const TABS = [
  { id: 'today', icon: 'Footprints', label: '오늘' },
  { id: 'week', icon: 'CalendarDays', label: '이번 주' },
  { id: 'history', icon: 'TrendingUp', label: '기록' },
  { id: 'settings', icon: 'Settings', label: '설정' },
];

export default function App() {
  // 인증: loading | login | onboarding | app
  const [authState, setAuthState] = useState('loading');
  const [user, setUser] = useState(null);

  const [tab, setTab] = useState('today');
  const [theme, setThemeState] = useState(localStorage.getItem('theme') || 'dark');
  const [accent, setAccentState] = useState(localStorage.getItem('accent') || '#0088ff');
  // 기록 시트 대상: null | { date, session, log } — 오늘/주간 탭 모두 임의 일자로 연다
  const [recordTarget, setRecordTarget] = useState(null);
  // 기록 저장 시 증가 → 주간 탭이 의존성으로 받아 자동 리로드
  const [recordVersion, setRecordVersion] = useState(0);
  const [showPlan, setShowPlan] = useState(false);
  // 끊긴 생성 복구: 복구 한 바퀴 끝날 때마다 증가(자식 카드가 스피너 해제 판단), 실패 시 안내 배너
  const [recoverTick, setRecoverTick] = useState(0);
  const [genNotice, setGenNotice] = useState(null);

  const [today, setToday] = useState(null);
  const [todayLoading, setTodayLoading] = useState(true);
  const [todayError, setTodayError] = useState(null);

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
    try {
      setToday(await api.today());
    } catch (e) {
      setTodayError(e.message);
    } finally {
      setTodayLoading(false);
    }
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
        {tab === 'today' && (
          <Today data={today} loading={todayLoading} error={todayError} refresh={refreshToday}
            recoverTick={recoverTick}
            onRecord={() => setRecordTarget({ date: today.today, session: today.session, log: today.log })}
            goWeek={() => setTab('week')} onPlan={() => setShowPlan(true)} />
        )}
        {tab === 'week' && (
          <Week refreshToday={refreshToday} reloadKey={recordVersion}
            onRecord={(s) => setRecordTarget({ date: s.session_date, session: s, log: s.log })}
            onPlan={() => setShowPlan(true)} />
        )}
        {tab === 'history' && <History />}
        {tab === 'settings' && (
          <Settings theme={theme} setTheme={setTheme} accent={accent} setAccent={setAccent} />
        )}
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {recordTarget && (
        <RecordSheet session={recordTarget.session} logDate={recordTarget.date} existingLog={recordTarget.log}
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
