// today.jsx — 오늘 탭. State machine: S0 무계획 / S1 훈련 전 / S3 리뷰 완료 / S4 주간 종료
const { useState: useStateToday } = React;

// Hero shell with big colored wash keyed to workout type (or neutral)
function Hero({ rgb, children, flat }) {
  return (
    <div style={{ position: 'relative', borderRadius: 26, padding: '22px 22px 24px', overflow: 'hidden',
      color: flat ? 'var(--label-primary)' : '#fff',
      background: flat ? 'var(--bg-grouped-secondary)'
        : `linear-gradient(150deg, rgba(${rgb},1) 0%, rgba(${rgb},0.82) 60%, rgba(${rgb},0.92) 100%)`,
      boxShadow: flat ? '0 1px 2px rgba(0,0,0,0.05), 0 6px 18px rgba(0,0,0,0.05)' : `0 10px 30px rgba(${rgb},0.30)` }}>
      {!flat && <div style={{ position: 'absolute', right: -40, top: -40, width: 180, height: 180, borderRadius: '50%',
        background: 'rgba(255,255,255,0.14)' }} />}
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
}

// ---------- S0 — 계획 없음 ----------
function TodayS0({ onGenerate }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Hero flat>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <span style={{ width: 44, height: 44, borderRadius: 14, background: 'var(--fill-tertiary)',
            display: 'grid', placeItems: 'center' }}><Icon name="calendar" size={24} color="var(--label-secondary)" strokeWidth={2} /></span>
          <RecoveryBadge level="low" />
        </div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 27, fontWeight: 700, letterSpacing: '-0.5px',
          lineHeight: 1.18, color: 'var(--label-primary)' }}>이번 주 계획이<br />아직 없어요</div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-secondary)', marginTop: 8 }}>
          {PROFILE.goal} · {PROFILE.goalDate} · 지난 주 데이터를 반영해 만들어 드릴게요.</div>
      </Hero>

      <Card pad={18}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 15, fontWeight: 600, color: 'var(--label-primary)' }}>지난 주 훈련</span>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)' }}>수행률 {LAST_WEEK.completion}%</span>
        </div>
        <div style={{ display: 'flex', gap: 0, marginBottom: 18 }}>
          <div style={{ flex: 1, display: 'grid', placeItems: 'flex-start' }}><Metric value={LAST_WEEK.km} unit="km" label="총 거리" size={30} /></div>
          <div style={{ flex: 1, display: 'grid', placeItems: 'flex-start' }}><Metric value={`${LAST_WEEK.doneCount}/${LAST_WEEK.totalCount}`} label="완료 세션" size={30} /></div>
          <div style={{ flex: 1, display: 'grid', placeItems: 'flex-start' }}><Metric value={LAST_WEEK.avgPace} label="평균 페이스" size={30} /></div>
        </div>
        <WeekBars days={LAST_WEEK.days} today={-1} />
      </Card>

      <CTA onClick={onGenerate}>이번 주 계획 세우기</CTA>
      <p style={{ textAlign: 'center', fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-tertiary)', margin: '2px 16px 0' }}>
        AI 코치가 지난 주 부하와 회복 상태를 분석해 7일 훈련을 구성해요.</p>
    </div>
  );
}

// ---------- S1 — 훈련 전 ----------
function TodayS1({ workout, coach, density, onRecord, onAdjust }) {
  const w = WORKOUT_TYPES[workout.type];
  const isRest = workout.type === 'rest';

  if (isRest) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Hero rgb={w.rgb}>
          <Icon name="bed" size={30} color="#fff" strokeWidth={2} />
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, letterSpacing: '-0.6px', marginTop: 14 }}>오늘은 쉬는 날이에요</div>
          <div style={{ fontSize: 15, opacity: 0.92, marginTop: 6, fontFamily: 'var(--font-text)' }}>{workout.focus}</div>
        </Hero>
        <Card>
          <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-secondary)', lineHeight: 1.5 }}>
            회복은 훈련의 일부예요. 잘 자고, 수분을 충분히 채우면 일요일 롱런이 한결 가벼워집니다.</div>
        </Card>
        <CTA variant="gray" icon={null} onClick={onAdjust}>주간 계획 보기</CTA>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Hero rgb={w.rgb}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, fontWeight: 600, opacity: 0.92, letterSpacing: '0.3px' }}>오늘 · {WEEK_DAYS[TODAY_INDEX]}요일</span>
          <Icon name={w.icon} size={26} color="#fff" strokeWidth={2.1} />
        </div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 700, letterSpacing: '-0.8px', marginTop: 12, lineHeight: 1 }}>{workout.title}</div>
        <div style={{ display: 'flex', gap: 22, marginTop: 18 }}>
          <div><div style={{ fontSize: 12, opacity: 0.85, fontFamily: 'var(--font-text)', fontWeight: 600, letterSpacing: '0.3px' }}>예상 시간</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>{workout.estMin}분</div></div>
          {workout.distance > 0 && <div><div style={{ fontSize: 12, opacity: 0.85, fontFamily: 'var(--font-text)', fontWeight: 600, letterSpacing: '0.3px' }}>목표 거리</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>{workout.distance}km</div></div>}
          {workout.target && <div><div style={{ fontSize: 12, opacity: 0.85, fontFamily: 'var(--font-text)', fontWeight: 600, letterSpacing: '0.3px' }}>목표 페이스</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginTop: 3 }}>{workout.target.split('–')[0].trim()}</div></div>}
        </div>
      </Hero>

      {/* AI 당일 훈련 설계 */}
      {workout.detail && (
        <div>
          <SectionLabel trailing={<span style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-text)', fontSize: 12, color: w.color, fontWeight: 600 }}><Icon name="sparkles" size={13} color={w.color} /> AI 설계</span>}>오늘 훈련 상세</SectionLabel>
          <Card pad={0}>
            {[
              { k: '워밍업', t: workout.detail.warmup, ic: 'wind', c: 'var(--accent-cyan)' },
              { k: '메인 세트', t: workout.detail.main, ic: w.icon, c: w.color },
              { k: '쿨다운', t: workout.detail.cooldown, ic: 'droplet', c: 'var(--accent-blue)' },
            ].map((s, i, arr) => (
              <div key={i} style={{ display: 'flex', gap: 13, padding: '15px 16px', borderBottom: i < arr.length - 1 ? '0.5px solid var(--separator-non-opaque)' : 'none' }}>
                <span style={{ width: 30, height: 30, borderRadius: 9, background: s.c, flex: 'none', display: 'grid', placeItems: 'center', marginTop: 1 }}><Icon name={s.ic} size={16} color="#fff" strokeWidth={2.2} /></span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: 'var(--label-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{s.k}</div>
                  <div style={{ fontFamily: 'var(--font-text)', fontSize: 16, color: 'var(--label-primary)', marginTop: 3, lineHeight: 1.4 }}>{s.t}</div>
                </div>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 9, padding: '13px 16px', background: `rgba(${w.rgb},0.07)` }}>
              <Icon name="info" size={16} color={w.color} style={{ flex: 'none', marginTop: 1 }} />
              <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', lineHeight: 1.45 }}>{workout.detail.note}</span>
            </div>
          </Card>
        </div>
      )}

      {/* 직전 유사 훈련 */}
      <Expander title={`직전 ${w.label} 기록`} icon="clock" iconColor="var(--gray)">
        <PrevSimilar type={workout.type} density={density} />
      </Expander>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 4 }}>
        <CTA onClick={onRecord} icon="check">다녀왔어요 · 기록 입력</CTA>
        <CTA variant="ghost" icon={null} onClick={onAdjust}>계획 조정이 필요해요</CTA>
      </div>
    </div>
  );
}

// previous similar workout snippet
function PrevSimilar({ type, density }) {
  const prev = RECENT_RUNS.find((r) => r.type === type) || RECENT_RUNS[0];
  const items = [
    { value: prev.distance.toFixed(1), unit: 'km', label: '거리' },
    { value: prev.pace, label: '페이스' },
  ];
  if (density !== 'core') items.push({ value: prev.avgHr, label: '평균 심박' });
  return (
    <div>
      <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, color: 'var(--label-secondary)', marginBottom: 12 }}>{prev.date}</div>
      <MetricRow items={items} size={22} />
    </div>
  );
}

// ---------- S3 — 리뷰 완료 ----------
function TodayS3({ workout, result, coach, density, tomorrow, onFullReview, onAdjust, onWeekReport, weekEndReady }) {
  const w = WORKOUT_TYPES[workout.type];
  const metrics = [
    { value: result.pace, label: '페이스 /km' },
    { value: result.avgHr, label: '평균 심박' },
  ];
  if (density !== 'core') metrics.push({ value: result.cadence, label: '케이던스' });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Hero rgb={w.rgb}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-text)', fontSize: 14, fontWeight: 600, opacity: 0.95 }}>
            <Icon name="check-circle" size={18} color="#fff" strokeWidth={2.3} /> 오늘 {coach.s3verb}</span>
          <span style={{ background: 'rgba(255,255,255,0.22)', borderRadius: 999, padding: '4px 10px', fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600 }}>{w.label}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 16 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 52, fontWeight: 700, letterSpacing: '-1.5px', lineHeight: 0.9 }}>{result.distance.toFixed(2)}</span>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 20, fontWeight: 600, opacity: 0.92 }}>km</span>
        </div>
        <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, opacity: 0.92, marginTop: 6 }}>{result.pace} /km · {result.min}분 {result.sec}초</div>
      </Hero>

      <Card>
        <MetricRow items={metrics} size={26} />
      </Card>

      {/* 코치 분석 한줄 */}
      <Card style={{ background: `rgba(${w.rgb},0.07)`, boxShadow: 'none' }} pad={16}>
        <div style={{ display: 'flex', gap: 11 }}>
          <span style={{ width: 30, height: 30, borderRadius: 9, background: w.color, flex: 'none', display: 'grid', placeItems: 'center' }}><Icon name="sparkles" size={16} color="#fff" /></span>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: w.color, marginBottom: 4 }}>코치 분석</div>
            <div style={{ fontFamily: 'var(--font-text)', fontSize: 15, color: 'var(--label-primary)', lineHeight: 1.5 }}>
              {coach.reviewIntro(result.distance.toFixed(1), result.pace)} {workout.type === 'tempo' ? coach.tempo : coach.interval(result)}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, paddingTop: 13, borderTop: '0.5px solid var(--separator-non-opaque)' }}>
          <RecoveryBadge level={result.feel <= 2 ? 'medium' : 'low'} />
          <button onClick={onFullReview} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: w.color, fontFamily: 'var(--font-text)', fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 2 }}>전체 분석 보기 <Icon name="chevron-right" size={16} color={w.color} strokeWidth={2.6} /></button>
        </div>
      </Card>

      {/* 내일 예고 */}
      {tomorrow && (
        <div>
          <SectionLabel>내일 예고</SectionLabel>
          <Card pad={16}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 46, height: 46, borderRadius: 13, background: WORKOUT_TYPES[tomorrow.type].color, display: 'grid', placeItems: 'center', flex: 'none' }}>
                <Icon name={WORKOUT_TYPES[tomorrow.type].icon} size={24} color="#fff" strokeWidth={2.1} /></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 17, fontWeight: 600, color: 'var(--label-primary)' }}>{tomorrow.title}</div>
                <div style={{ fontFamily: 'var(--font-text)', fontSize: 14, color: 'var(--label-secondary)', marginTop: 2 }}>
                  {tomorrow.type === 'rest' ? tomorrow.focus : `${tomorrow.distance ? tomorrow.distance + 'km · ' : ''}${tomorrow.estMin}분`}</div>
              </div>
            </div>
          </Card>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 2 }}>
        {weekEndReady
          ? <CTA onClick={onWeekReport}>이번 주 성장 리포트 만들기</CTA>
          : <CTA variant="ghost" icon={null} onClick={onAdjust}>계획 조정이 필요해요</CTA>}
      </div>
    </div>
  );
}

// ---------- S4 — 주간 종료 ----------
function TodayS4({ onWeekReport, onNextWeek }) {
  const cur = HISTORY_WEEKS[0];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Hero rgb={'97,85,245'}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="trophy" size={20} color="#fff" strokeWidth={2.1} />
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 14, fontWeight: 600, opacity: 0.95 }}>이번 주 훈련 종료</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 14 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 56, fontWeight: 700, letterSpacing: '-1.5px', lineHeight: 0.9 }}>{LAST_WEEK.km}</span>
          <span style={{ fontFamily: 'var(--font-text)', fontSize: 20, fontWeight: 600, opacity: 0.92 }}>km</span>
        </div>
        <div style={{ display: 'flex', gap: 26, marginTop: 16 }}>
          <div><div style={{ fontSize: 12, opacity: 0.85, fontFamily: 'var(--font-text)', fontWeight: 600 }}>완료 세션</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, marginTop: 2 }}>{LAST_WEEK.doneCount}/{LAST_WEEK.totalCount}</div></div>
          <div><div style={{ fontSize: 12, opacity: 0.85, fontFamily: 'var(--font-text)', fontWeight: 600 }}>수행률</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, marginTop: 2 }}>{LAST_WEEK.completion}%</div></div>
        </div>
      </Hero>

      <Card style={{ background: 'var(--bg-grouped-secondary)' }}>
        <div style={{ display: 'flex', gap: 11 }}>
          <Icon name="sparkles" size={20} color="var(--accent-indigo)" style={{ flex: 'none', marginTop: 2 }} />
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600, color: 'var(--label-primary)', lineHeight: 1.45, letterSpacing: '-0.3px' }}>
            “꾸준함이 속도를 만듭니다. 이번 주, 임계주 수행이 가장 크게 늘었어요.”</div>
        </div>
      </Card>

      <Card>
        <WeekBars days={LAST_WEEK.days} today={-1} accent="var(--accent-indigo)" />
      </Card>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <CTA onClick={onWeekReport}>이번 주 성장 리포트 만들기</CTA>
        <CTA variant="gray" icon={null} onClick={onNextWeek}>다음 주 계획 세우기</CTA>
      </div>
    </div>
  );
}

function TodayTab(props) {
  const { weekState } = props;
  let body;
  if (weekState === 'S0') body = <TodayS0 onGenerate={props.onGenerate} />;
  else if (weekState === 'S1') body = <TodayS1 {...props} workout={props.workout} />;
  else if (weekState === 'S4') body = <TodayS4 onWeekReport={props.onWeekReport} onNextWeek={props.onNextWeek} />;
  else body = <TodayS3 {...props} />;

  const titleMap = { S0: '오늘', S1: '오늘', S3: '오늘', S4: '주간 요약' };
  return (
    <div>
      <NavBarLarge title={titleMap[weekState]} trailing={
        <span style={{ fontFamily: 'var(--font-text)', fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)' }}>{PROFILE.goalDate}</span>
      } />
      <div style={{ padding: '4px 16px 0' }}>{body}</div>
    </div>
  );
}

Object.assign(window, { TodayTab });
