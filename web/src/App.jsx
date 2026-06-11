// 루트 — 탭 네비게이션 + 테마/강조색 + 오늘 데이터 공유
import React, { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import { isoWeekKey } from './workouts.js';
import TabBar from './components/TabBar.jsx';
import RecordSheet from './components/RecordSheet.jsx';
import PlanSheet from './components/PlanSheet.jsx';
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
  useEffect(() => { refreshToday(); }, [refreshToday]);

  // Strava OAuth 복귀 시 설정 탭으로
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('strava')) setTab('settings');
  }, []);

  // 주의 첫 실행: 계획 없으면 주간 계획 시트 자동 오픈 (주 1회, 닫으면 그 주는 다시 안 뜸)
  useEffect(() => {
    if (today?.state === 'NO_PLAN' && localStorage.getItem('planPromptWeek') !== isoWeekKey()) {
      setShowPlan(true);
    }
  }, [today?.state]);

  const closePlanSheet = () => {
    localStorage.setItem('planPromptWeek', isoWeekKey());
    setShowPlan(false);
  };

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
