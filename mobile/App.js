// 러닝 코치 모바일 (Expo) — 커스텀 탭바 + 4화면
import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, SafeAreaView, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { api } from './src/api';
import { C } from './src/theme';
import RecordSheet from './src/RecordSheet';
import Today from './src/screens/Today';
import Week from './src/screens/Week';
import History from './src/screens/History';
import Settings from './src/screens/Settings';

const TABS = [
  { id: 'today', emoji: '🏃', label: '오늘' },
  { id: 'week', emoji: '📅', label: '이번 주' },
  { id: 'history', emoji: '📈', label: '기록' },
  { id: 'settings', emoji: '⚙️', label: '설정' },
];

export default function App() {
  const [tab, setTab] = useState('today');
  const [showRecord, setShowRecord] = useState(false);
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshToday = useCallback(async () => {
    setError(null);
    try { setToday(await api.today()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refreshToday(); }, [refreshToday]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }}>
      <StatusBar style="light" />
      <View style={{ flex: 1 }}>
        {tab === 'today' && (
          <Today data={today} loading={loading} error={error} refresh={refreshToday}
            onRecord={() => setShowRecord(true)} goWeek={() => setTab('week')} />
        )}
        {tab === 'week' && <Week refreshToday={refreshToday} />}
        {tab === 'history' && <History />}
        {tab === 'settings' && <Settings />}
      </View>

      {/* 플로팅 탭바 */}
      <View style={{ position: 'absolute', left: 0, right: 0, bottom: 24, alignItems: 'center' }}>
        <View style={{ flexDirection: 'row', backgroundColor: 'rgba(28,28,30,0.92)', borderRadius: 999,
          padding: 6, gap: 4, shadowColor: '#000', shadowOpacity: 0.4, shadowRadius: 16,
          shadowOffset: { width: 0, height: 6 }, elevation: 12 }}>
          {TABS.map((t) => {
            const on = t.id === tab;
            return (
              <Pressable key={t.id} onPress={() => setTab(t.id)}
                style={{ alignItems: 'center', minWidth: 72, paddingVertical: 8, paddingHorizontal: 10,
                  borderRadius: 999, backgroundColor: on ? C.tint : 'transparent' }}>
                <Text style={{ fontSize: 18 }}>{t.emoji}</Text>
                <Text style={{ fontSize: 11, fontWeight: on ? '700' : '500', marginTop: 2,
                  color: on ? '#fff' : C.label2 }}>{t.label}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <RecordSheet visible={showRecord} session={today?.session} todayDate={today?.today}
        onClose={(saved) => { setShowRecord(false); if (saved) refreshToday(); }} />
    </SafeAreaView>
  );
}
