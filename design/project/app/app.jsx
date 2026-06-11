// app.jsx — root component: state, tab nav, tweaks, sheet orchestration
const { useState: useStateApp, useEffect: useEffectApp } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "coachTone": "calm",
  "accent": "#0088ff",
  "weekState": "S1",
  "density": "full"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTab] = useStateApp('today');
  const [showRecord, setShowRecord] = useStateApp(false);
  const [hasPlan, setHasPlan] = useStateApp(true);
  const [generating, setGenerating] = useStateApp(false);

  // Sync tint CSS variable with tweak
  useEffectApp(() => {
    document.documentElement.style.setProperty('--tint', t.accent);
  }, [t.accent]);

  const coach = COACH_TONE[t.coachTone] || COACH_TONE.calm;
  const weekState = t.weekState;
  const density = t.density;
  const todayWorkout = WEEK_PLAN[TODAY_INDEX];
  const tomorrowWorkout = WEEK_PLAN[TODAY_INDEX + 1] || null;
  const todayResult = todayWorkout.result || {
    distance: 8.12, min: 46, sec: 32, pace: '5:44', avgHr: 163, maxHr: 178, cadence: 176, feel: 3, note: '템포 잘 유지했어요.'
  };

  const handleGenerate = () => {
    if (!hasPlan) {
      setGenerating(true);
    } else {
      setTab('week');
    }
  };

  const handleGenerateDone = () => {
    setGenerating(false);
    setHasPlan(true);
  };

  const tabs = [
    { id: 'today',   icon: 'run',          label: '오늘' },
    { id: 'week',    icon: 'calendar',     label: '이번 주' },
    { id: 'history', icon: 'trending-up',  label: '기록' },
    { id: 'settings',icon: 'gear',         label: '설정' },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative',
      background: 'var(--bg-grouped-primary)', fontFamily: 'var(--font-text)' }}>

      {/* Scrollable content area */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', paddingBottom: 110 }}>
        {tab === 'today' && (
          <TodayTab
            weekState={weekState}
            coach={coach}
            density={density}
            workout={todayWorkout}
            result={todayResult}
            tomorrow={tomorrowWorkout}
            onGenerate={handleGenerate}
            onRecord={() => setShowRecord(true)}
            onAdjust={() => setTab('week')}
            onWeekReport={() => setTab('week')}
            onNextWeek={() => setTab('week')}
            onFullReview={() => setShowRecord(false)}
            weekEndReady={false}
          />
        )}
        {tab === 'week' && (
          <WeekTab
            hasPlan={hasPlan}
            generating={generating}
            onGenerate={generating ? handleGenerateDone : handleGenerate}
            onRecord={() => setShowRecord(true)}
            coach={coach}
          />
        )}
        {tab === 'history' && <HistoryTab density={density} />}
        {tab === 'settings' && (
          <SettingsTab
            tweaks={t} setTweak={setTweak}
            TweaksPanel={TweaksPanel}
            TweakSection={TweakSection}
            TweakRadio={TweakRadio}
            TweakColor={TweakColor}
            TweakToggle={TweakToggle}
          />
        )}
      </div>

      {/* Floating tab bar */}
      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {/* Record sheet */}
      {showRecord && (
        <RecordSheet
          workout={todayWorkout}
          coach={coach}
          onSave={(form) => { console.log('saved', form); }}
          onClose={() => setShowRecord(false)}
        />
      )}

      {/* Tweaks Panel */}
      <TweaksPanel title="Tweaks">
        <TweakSection label="앱 상태" />
        <TweakRadio label="주간 진행 상태" value={t.weekState}
          options={['S0', 'S1', 'S3', 'S4']}
          onChange={v => setTweak('weekState', v)} />
        <TweakSection label="코치" />
        <TweakRadio label="코치 톤" value={t.coachTone}
          options={['calm', 'warm', 'strict']}
          onChange={v => setTweak('coachTone', v)} />
        <TweakSection label="시각" />
        <TweakColor label="강조 색상" value={t.accent}
          options={['#0088ff', '#34c759', '#ff9500', '#ff375f', '#5e5ce6']}
          onChange={v => setTweak('accent', v)} />
        <TweakSection label="데이터" />
        <TweakRadio label="표시 밀도" value={t.density}
          options={['core', 'full']}
          onChange={v => setTweak('density', v)} />
      </TweaksPanel>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
