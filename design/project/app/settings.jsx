// settings.jsx — 설정 탭
function SettingsTab({ tweaks, setTweak, TweaksPanel, TweakSection, TweakRadio, TweakColor, TweakToggle }) {
  const profile = PROFILE;
  return (
    <div>
      <NavBarLarge title="설정" />
      <div style={{ padding: '4px 0 0' }}>

        {/* Profile card */}
        <div style={{ padding: '0 16px 8px' }}>
          <Card pad={18}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--tint)', display: 'grid', placeItems: 'center', flex: 'none',
                boxShadow: '0 4px 14px rgba(0,136,255,0.30)' }}>
                <Icon name="run" size={28} color="#fff" strokeWidth={2} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--label-primary)' }}>{profile.name}</div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>
                  목표: {profile.goal}</div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-tertiary)' }}>
                  {profile.goalDate} · 주간 목표 {profile.weeklyTarget}km</div>
              </div>
            </div>
          </Card>
        </div>

        {/* 러너 프로필 */}
        <ListSection header="러너 프로필">
          <Row title="목표 레이스" value="10K 50분 돌파" accessory="disclosure" onClick={() => {}} />
          <Row title="목표일" value="2026. 7. 14" accessory="disclosure" onClick={() => {}} />
          <Row title="주간 목표 거리" value={`${profile.weeklyTarget} km`} accessory="disclosure" onClick={() => {}} />
          <Row title="최대 심박" value={`${profile.maxHr} bpm`} accessory="disclosure" onClick={() => {}} />
          <Row title="안정 심박" value={`${profile.restHr} bpm`} accessory="disclosure" onClick={() => {}} />
          <Row title="VO₂ Max (추정)" value={`${profile.vo2} mL/kg/min`} accessory="disclosure" onClick={() => {}} />
        </ListSection>

        {/* 훈련 설정 */}
        <ListSection header="훈련 설정">
          <Row title="훈련일 알림" control={<Toggle value={true} onChange={() => {}} />} />
          <Row title="훈련 후 기록 알림" control={<Toggle value={true} onChange={() => {}} />} />
          <Row title="페이스 단위" value="분/km" accessory="disclosure" onClick={() => {}} />
          <Row title="거리 단위" value="km" accessory="disclosure" onClick={() => {}} />
        </ListSection>

        {/* 데이터 연동 */}
        <ListSection header="데이터 연동" footer="가민 Connect 및 스트라바 API 연동 예정입니다.">
          <Row icon="gauge" iconColor="var(--accent-teal)" title="가민 Connect" value="연동 예정" accessory="disclosure" onClick={() => {}} />
          <Row icon="route" iconColor="var(--accent-orange)" title="스트라바" value="연동 예정" accessory="disclosure" onClick={() => {}} />
        </ListSection>

        {/* 앱 설정 */}
        <ListSection header="앱 설정">
          <Row title="언어" value="한국어" accessory="disclosure" onClick={() => {}} />
          <Row title="버전" value="1.0.0 (프로토타입)" />
        </ListSection>

      </div>
    </div>
  );
}

Object.assign(window, { SettingsTab });
