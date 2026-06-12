// 루트 — 인증 게이트(로그인/온보딩) + 탭 네비게이션 + 테마/강조색 + 오늘 데이터 공유
import React, { useCallback, useEffect, useState } from 'react';
import { api, getToken } from './api.js';
import { isoWeekKey } from './workouts.js';
import TabBar from './components/TabBar.jsx';
import RecordSheet from './components/RecordSheet.jsx';
import PlanSheet from './components/PlanSheet.jsx';
import { Spinner } from './components/Ui.jsx';
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
  const [showRecord, setShowRecord] = useState(false);
  const [showPlan, setShowPlan] = useState(false);

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
      <div className="scroll-area">
        {tab === 'today' && (
          <Today data={today} loading={todayLoading} error={todayError} refresh={refreshToday}
            onRecord={() => setShowRecord(true)} goWeek={() => setTab('week')}
            onPlan={() => setShowPlan(true)} />
        )}
        {tab === 'week' && <Week refreshToday={refreshToday} onPlan={() => setShowPlan(true)} />}
        {tab === 'history' && <History />}
        {tab === 'settings' && (
          <Settings theme={theme} setTheme={setTheme} accent={accent} setAccent={setAccent} />
        )}
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {showRecord && today && (
        <RecordSheet session={today.session} todayDate={today.today}
          onClose={(saved) => { setShowRecord(false); if (saved) refreshToday(); }} />
      )}

      {showPlan && (
        <PlanSheet onClose={closePlanSheet}
          goSettings={() => { closePlanSheet(); setTab('settings'); }}
          onDone={() => { closePlanSheet(); refreshToday(); setTab('week'); }} />
      )}
    </div>
  );
}
