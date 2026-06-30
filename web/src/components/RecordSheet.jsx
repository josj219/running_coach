// 훈련 기록 입력 모달 + AI 리뷰 스트리밍.
// UX: Strava 자동 채움 → 필수 입력은 거리·시간·몸상태 3개뿐. 나머지는 '자세히'에 접어둠.
// '달리지 않았어요' 체크 시 수치 입력을 숨기고 소감(직접 기록) 기반으로 저장한다.
// 오늘뿐 아니라 임의의 과거 일자(logDate)도 기록·수정 가능 — 어제 기록을 깜빡한 경우 대비.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { api, streamReview } from '../api.js';
import { autoPace, BODY_PARTS, FEEL_OPTIONS, localISO, parseTimeToSec, wmeta } from '../workouts.js';
import { Banner, Card, CTA, Icon, MetricRow, Modal, RecoveryBadge } from './Ui.jsx';

const NORUN_PREFIX = '(달리기 기록 없음 — 직접 기록) ';

// 'YYYY-MM-DD' → '6월 18일 (목)' (로컬 기준 — Date(iso)의 UTC 파싱 하루 밀림 방지)
function fmtDateLabel(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  const wd = ['일', '월', '화', '수', '목', '금', '토'][new Date(y, m - 1, d).getDay()];
  return `${m}월 ${d}일 (${wd})`;
}

// 기존 기록 → 폼 초기값 (과거 일자 수정 시 무손실 프리필)
function formFromLog(log) {
  const dur = log?.duration_sec || 0;
  return {
    distance: log?.distance_km ? String(log.distance_km) : '',
    minutes: dur ? String(Math.floor(dur / 60)) : '',
    seconds: dur ? String(dur % 60) : '',
    pace: log?.avg_pace || '',
    avgHr: log?.avg_hr ? String(log.avg_hr) : '',
    maxHr: log?.max_hr ? String(log.max_hr) : '',
    cadence: log?.cadence ? String(log.cadence) : '',
    feel: log?.feel || 3,
    note: (log?.user_comment || '').replace(NORUN_PREFIX, ''),
  };
}

function FieldLabel({ children }) {
  return <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--label-secondary)',
    textTransform: 'uppercase', letterSpacing: '0.4px', margin: '18px 0 8px' }}>{children}</div>;
}

function NumInput({ value, onChange, placeholder, unit, flex = 1, mode = 'decimal' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: 'var(--fill-tertiary)', borderRadius: 12,
      padding: '11px 12px', flex, minWidth: 0, overflow: 'hidden' }}>
      <input type="text" inputMode={mode} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ border: 'none', outline: 'none', background: 'none', flex: '1 1 auto', minWidth: 0,
          fontFamily: 'var(--font-display)', fontSize: 19, fontWeight: 700, color: 'var(--label-primary)',
          letterSpacing: '-0.3px' }} />
      {unit && <span style={{ fontSize: 13, color: 'var(--label-tertiary)', fontWeight: 600, marginLeft: 3,
        flex: 'none', whiteSpace: 'nowrap' }}>{unit}</span>}
    </div>
  );
}

// 파일 이미지를 캔버스로 축소(긴 변 1600px)한 뒤 base64(jpeg)로 변환.
// 업로드 크기와 Claude 비전 입력 한도를 함께 줄인다.
async function fileToScaledB64(file, maxEdge = 1600, quality = 0.85) {
  const dataUrl = await new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = () => reject(new Error('파일을 읽지 못했어요.'));
    fr.readAsDataURL(file);
  });
  const img = await new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => reject(new Error('이미지를 열지 못했어요.'));
    im.src = dataUrl;
  });
  const scale = Math.min(1, maxEdge / Math.max(img.width, img.height));
  const w = Math.round(img.width * scale), h = Math.round(img.height * scale);
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h;
  canvas.getContext('2d').drawImage(img, 0, 0, w, h);
  return { b64: canvas.toDataURL('image/jpeg', quality).split(',')[1], mediaType: 'image/jpeg' };
}

// 워치/러닝앱 스크린샷 → AI 분석 → 폼 자동 채움
function ImageImport({ onExtract }) {
  const [state, setState] = useState('idle'); // idle | analyzing | error
  const [err, setErr] = useState(null);
  const inputRef = useRef(null);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';  // 같은 파일 재선택 허용
    if (!file) return;
    setState('analyzing'); setErr(null);
    try {
      const { b64, mediaType } = await fileToScaledB64(file);
      const data = await api.analyzeImage(b64, mediaType);
      if (data.found === false) {
        setState('error');
        setErr('러닝 기록 화면을 인식하지 못했어요. 다른 이미지를 올리거나 직접 입력해 주세요.');
        return;
      }
      onExtract(data);
      setState('idle');
    } catch (e2) {
      setState('error');
      setErr(e2.code === 'AI_UNAVAILABLE'
        ? 'AI 분석에 실패했어요. 직접 입력해 주세요.'
        : (e2.message || '이미지 분석에 실패했어요.'));
    }
  };

  return (
    <div style={{ marginTop: 10 }}>
      <input ref={inputRef} type="file" accept="image/*" onChange={onFile} style={{ display: 'none' }} />
      <button onClick={() => inputRef.current?.click()} disabled={state === 'analyzing'}
        style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', padding: '14px 16px',
          borderRadius: 16, border: 'none', cursor: state === 'analyzing' ? 'default' : 'pointer',
          textAlign: 'left', background: 'var(--fill-tertiary)' }}>
        <span style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--tint)',
          display: 'grid', placeItems: 'center', flex: 'none' }}>
          <Icon name={state === 'analyzing' ? 'Sparkles' : 'Camera'} size={20} color="#fff"
            style={state === 'analyzing' ? { animation: 'spin 1.2s linear infinite' } : undefined} /></span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--label-primary)' }}>
            {state === 'analyzing' ? '이미지 분석 중…' : '사진으로 입력'}</div>
          <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>
            워치·러닝앱 캡처를 올리면 거리·시간·심박을 자동 인식</div>
        </div>
        {state !== 'analyzing' && <Icon name="ChevronRight" size={18} color="var(--label-tertiary)" />}
      </button>
      {state === 'error' && <div style={{ marginTop: 8 }}><Banner tone="error">{err}</Banner></div>}
    </div>
  );
}

function StravaImport({ onPick }) {
  const [state, setState] = useState('idle'); // idle | loading | list | empty | off
  const [items, setItems] = useState([]);

  const load = async () => {
    setState('loading');
    try {
      const integ = await api.integrations();
      const calls = [];
      if (integ.strava?.connected) calls.push(api.stravaActivities(3));
      if (integ.garmin?.connected) calls.push(api.garminActivities(3));
      if (!calls.length) { setState('off'); return; }
      const results = await Promise.all(calls);
      const byId = new Map();
      results.flatMap((r) => r.items).forEach((a) => { if (!byId.has(a.id)) byId.set(a.id, a); });
      const merged = [...byId.values()]
        .sort((a, b) => (b.start_date || '').localeCompare(a.start_date || ''))
        .slice(0, 3);
      if (!merged.length) { setState('empty'); return; }
      setItems(merged);
      setState('list');
    } catch { setState('empty'); }
  };

  if (state === 'idle') {
    return (
      <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%',
        padding: '14px 16px', borderRadius: 16, border: 'none', cursor: 'pointer', textAlign: 'left',
        background: 'linear-gradient(135deg, rgba(252,76,2,0.14), rgba(252,76,2,0.06))' }}>
        <span style={{ width: 40, height: 40, borderRadius: 12, background: '#FC4C02', display: 'grid', placeItems: 'center', flex: 'none' }}>
          <Icon name="Zap" size={20} color="#fff" /></span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--label-primary)' }}>연동에서 가져오기</div>
          <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>거리·시간·페이스·심박 자동 입력</div>
        </div>
        <Icon name="ChevronRight" size={18} color="var(--label-tertiary)" />
      </button>
    );
  }
  if (state === 'loading') return <div style={{ padding: 14, fontSize: 14, color: 'var(--label-secondary)' }}>활동 불러오는 중…</div>;
  if (state === 'off') return <Banner tone="info">설정 탭에서 Strava·가민을 연결하면 기록이 자동으로 채워져요.</Banner>;
  if (state === 'empty') return <Banner tone="info">가져올 러닝 활동이 없어요. 직접 입력해 주세요.</Banner>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {items.map((a) => (
        <button key={a.id} onClick={() => onPick(a)}
          style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 14,
            border: 'none', cursor: 'pointer', background: 'var(--fill-tertiary)', textAlign: 'left' }}>
          <span style={{ width: 34, height: 34, borderRadius: 10, background: '#FC4C02', display: 'grid', placeItems: 'center', flex: 'none' }}>
            <Icon name="Footprints" size={17} color="#fff" /></span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--label-primary)', whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.name || '러닝'}</div>
            <div style={{ fontSize: 12.5, color: 'var(--label-secondary)' }}>
              {a.start_date?.slice(5, 10)} · {a.distance_km}km · {a.avg_pace}/km{a.avg_hr ? ` · ♥${a.avg_hr}` : ''}</div>
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#FC4C02', flex: 'none' }}>채우기</span>
        </button>
      ))}
    </div>
  );
}

// 스트림 원문(JSON 토큰)에서 coach_comment 값만 점진 추출 — 코드/중괄호 노출 방지
function previewFromStream(raw) {
  const m = raw.match(/"coach_comment"\s*:\s*"((?:[^"\\]|\\.)*)/);
  if (!m) return null;
  return m[1].replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

export default function RecordSheet({ session, logDate, existingLog, onClose }) {
  const w = wmeta(session?.kind || 'easy');
  const dateLabel = fmtDateLabel(logDate);
  const isToday = logDate === localISO();
  // 선택된 일자에 이미 기록이 있으면 그 값으로 프리필(수정), 없으면 빈 폼(신규)
  const initPain = existingLog?.pain_part
    ? existingLog.pain_part.split(',').map((s) => s.trim()).filter(Boolean) : [];
  const [form, setForm] = useState(() => formFromLog(existingLog));
  // '달리지 않았어요' — 거리·시간이 없는 기존 기록(보강/휴식 등)은 이 모드로 복원
  const [noRun, setNoRun] = useState(
    () => !!existingLog && !existingLog.distance_km && !existingLog.duration_sec);
  const [pain, setPain] = useState(initPain);          // 선택된 부위
  const [painLevels, setPainLevels] = useState(
    () => Object.fromEntries(initPain.map((p) => [p, existingLog?.pain_level || 3])));
  const [detailOpen, setDetailOpen] = useState(
    () => !!(existingLog?.avg_hr || existingLog?.max_hr || existingLog?.cadence || initPain.length));
  const [phase, setPhase] = useState('form');    // form | saving | review
  const [error, setError] = useState(null);
  const [logId, setLogId] = useState(null);
  const [streamText, setStreamText] = useState('');
  const [review, setReview] = useState(null);
  const [source, setSource] = useState(existingLog?.source || 'manual');
  const [externalId, setExternalId] = useState(null);
  // 연동/사진으로 값을 채우면 위쪽 가져오기 영역을 접는다 ('다시 고르기'로 복원)
  const [imported, setImported] = useState(false);

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  // 거리+시간 입력 시 페이스 자동 계산 (직접 수정도 가능)
  const calcPace = useMemo(() => autoPace(form.distance, parseTimeToSec(form.minutes, form.seconds)), [form.distance, form.minutes, form.seconds]);
  useEffect(() => { if (calcPace) set('pace', calcPace); }, [calcPace]);

  const pickActivity = (a) => {
    const min = a.duration_sec ? Math.floor(a.duration_sec / 60) : '';
    const sec = a.duration_sec ? a.duration_sec % 60 : '';
    setForm((p) => ({ ...p, distance: String(a.distance_km ?? ''), minutes: String(min), seconds: String(sec),
      pace: a.avg_pace || '', avgHr: a.avg_hr ? String(a.avg_hr) : '', maxHr: a.max_hr ? String(a.max_hr) : '',
      cadence: a.cadence ? String(a.cadence) : '' }));
    setSource(a.provider || 'strava');
    setExternalId(a.external_id);
    setDetailOpen(true);
    setImported(true);
  };

  // 가져오기 영역 복원 — 채운 값은 유지하고 목록만 다시 노출
  const resetImport = () => { setImported(false); setSource('manual'); setExternalId(null); };

  // 이미지 분석 결과로 폼 채움 — 인식 안 된 값(null)은 기존 입력 유지
  const fillFromExtract = (d) => {
    const hasDur = d.duration_sec != null;
    setForm((p) => ({ ...p,
      distance: d.distance_km != null ? String(d.distance_km) : p.distance,
      minutes: hasDur ? String(Math.floor(d.duration_sec / 60)) : p.minutes,
      seconds: hasDur ? String(d.duration_sec % 60) : p.seconds,
      pace: d.avg_pace || p.pace,
      avgHr: d.avg_hr != null ? String(d.avg_hr) : p.avgHr,
      maxHr: d.max_hr != null ? String(d.max_hr) : p.maxHr,
      cadence: d.cadence != null ? String(d.cadence) : p.cadence,
    }));
    setSource('image');
    setExternalId(null);
    setDetailOpen(true);
    setImported(true);
  };

  const maxPain = Math.max(0, ...pain.map((p) => painLevels[p] || 3));

  const save = async () => {
    setError(null);
    setPhase('saving');
    try {
      const body = {
        log_date: logDate,
        kind: session?.kind || 'easy',
        distance_km: noRun ? 0 : (parseFloat(form.distance) || 0),
        duration_sec: noRun ? null : parseTimeToSec(form.minutes, form.seconds),
        avg_pace: noRun ? null : (form.pace || null),
        avg_hr: noRun ? null : (parseInt(form.avgHr, 10) || null),
        max_hr: noRun ? null : (parseInt(form.maxHr, 10) || null),
        cadence: noRun ? null : (parseInt(form.cadence, 10) || null),
        feel: form.feel,
        fatigue_num: { 1: 9, 2: 7, 3: 3, 4: 1 }[form.feel],
        pain_part: pain.join(', ') || null,
        pain_level: maxPain,
        user_comment: noRun && form.note
          ? `${NORUN_PREFIX}${form.note}` : (form.note || null),
        source, external_id: externalId,
      };
      const res = await api.saveLog(body);
      setLogId(res.id);
      setPhase('review');
      startReview(res.id);
    } catch (e) {
      setPhase('form');
      setError(`저장 실패: ${e.message}`);
    }
  };

  const startReview = (id) => {
    setStreamText('');
    setReview(null);
    setError(null);
    streamReview(id, {
      onToken: (t) => setStreamText((p) => p + t),
      onDone: (r) => setReview(r),
      onError: () => setError('리뷰 생성에 실패했어요 — 기록은 저장됐습니다.'),
    });
  };

  const preview = previewFromStream(streamText);
  const hasMetrics = !noRun && (form.distance || form.pace || form.avgHr);

  return (
    <Modal
      title={phase === 'review' ? 'AI 코치 분석' : phase === 'saving' ? '저장 중…' : '훈련 기록'}
      subtitle={isToday
        ? (session?.title || '오늘 훈련')
        : `${dateLabel}${session?.title ? ` · ${session.title}` : ''}`}
      locked={phase === 'saving'}
      onClose={() => onClose(phase === 'review')}>

      {phase === 'saving' && (
        <div style={{ padding: '60px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 52, height: 52, borderRadius: 16, background: w.color, display: 'grid', placeItems: 'center',
            boxShadow: `0 6px 20px rgba(${w.rgb},0.35)`, animation: 'spin 1.2s linear infinite' }}>
            <Icon name="Sparkles" size={26} color="#fff" />
          </div>
          <div style={{ fontSize: 16, color: 'var(--label-secondary)' }}>기록 저장 중…</div>
        </div>
      )}

      {phase === 'review' && (
        <div style={{ padding: '18px 20px 24px' }}>
          {hasMetrics && (
            <Card style={{ marginBottom: 14 }}>
              <MetricRow size={24} items={[
                { value: form.distance || '0', unit: 'km', label: '거리' },
                { value: form.pace || '--', label: '페이스' },
                { value: form.avgHr || '--', label: '평균 심박' },
              ]} />
            </Card>
          )}
          {review?.summary && (
            <Card style={{ marginBottom: 14 }} pad={14}>
              <div style={{ display: 'flex', gap: 10 }}>
                <Icon name="CircleCheck" size={17} color={w.color} style={{ flex: 'none', marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--label-secondary)', marginBottom: 3 }}>
                    {isToday ? '오늘 훈련 요약' : `${dateLabel} 훈련 요약`}</div>
                  <div style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--label-primary)' }}>{review.summary}</div>
                </div>
              </div>
            </Card>
          )}
          <Card style={{ background: `rgba(${w.rgb},0.08)`, boxShadow: 'none', marginBottom: 14 }}>
            <div style={{ display: 'flex', gap: 11 }}>
              <span style={{ width: 30, height: 30, borderRadius: 9, background: w.color, flex: 'none',
                display: 'grid', placeItems: 'center' }}><Icon name="Sparkles" size={16} color="#fff" /></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: w.color, marginBottom: 4 }}>코치 분석</div>
                {review ? (
                  <div style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--label-primary)' }}>
                    <div>{review.coach_comment}</div>
                    {review.strengths && <div style={{ marginTop: 10 }}>
                      <b style={{ fontSize: 13 }}>잘한 점</b>
                      <div style={{ whiteSpace: 'pre-line', fontSize: 14, color: 'var(--label-secondary)' }}>{review.strengths}</div></div>}
                    {review.improvements && <div style={{ marginTop: 8 }}>
                      <b style={{ fontSize: 13 }}>개선할 점</b>
                      <div style={{ whiteSpace: 'pre-line', fontSize: 14, color: 'var(--label-secondary)' }}>{review.improvements}</div></div>}
                  </div>
                ) : error ? null : preview ? (
                  <div className="stream-cursor" style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--label-primary)',
                    whiteSpace: 'pre-line' }}>{preview}</div>
                ) : (
                  <div className="stream-cursor" style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--label-secondary)' }}>
                    코치가 기록을 분석하는 중…</div>
                )}
              </div>
            </div>
            {review && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, paddingTop: 13,
                borderTop: '0.5px solid var(--separator-non-opaque)' }}>
                <RecoveryBadge level={review.recovery} />
                {review.next_impact && <span style={{ fontSize: 13, color: 'var(--label-secondary)' }}>{review.next_impact}</span>}
              </div>
            )}
          </Card>
          {error && <div style={{ marginBottom: 14 }}>
            <Banner tone="error" action="재시도" onAction={() => startReview(logId)}>{error}</Banner></div>}
          <CTA onClick={() => onClose(true)} icon="Check">확인</CTA>
        </div>
      )}

      {phase === 'form' && (
        <div style={{ padding: '16px 20px 24px' }}>
          {!noRun && !imported && <StravaImport onPick={pickActivity} />}
          {!noRun && !imported && <ImageImport onExtract={fillFromExtract} />}
          {!noRun && imported && (
            <div style={{ marginBottom: 4 }}>
              <Banner tone="info" action="다시 고르기" onAction={resetImport}>
                {source === 'image' ? '이미지에서 값을 채웠어요.' : '연동 기록을 불러왔어요.'} 숫자를 확인하고 저장하세요.</Banner></div>
          )}

          {/* 달리기 기록이 없는 날 — 수치 입력 없이 소감 기반으로 기록 */}
          <button onClick={() => setNoRun(!noRun)}
            style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', marginTop: noRun ? 0 : 12,
              padding: '12px 14px', borderRadius: 14, border: 'none', cursor: 'pointer', textAlign: 'left',
              background: noRun ? 'color-mix(in srgb, var(--tint) 12%, transparent)' : 'var(--fill-tertiary)' }}>
            <span style={{ width: 22, height: 22, borderRadius: 7, flex: 'none', display: 'grid', placeItems: 'center',
              background: noRun ? 'var(--tint)' : 'var(--fill-secondary)', transition: 'background .12s' }}>
              {noRun && <Icon name="Check" size={14} color="#fff" strokeWidth={3} />}
            </span>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--label-primary)' }}>
                {isToday ? '오늘 달리지 않았어요' : '이 날 달리지 않았어요'}</div>
              <div style={{ fontSize: 13, color: 'var(--label-secondary)' }}>거리·시간 없이, 아래에 한 일을 적어 기록해요</div>
            </div>
          </button>

          {!noRun && (
            <>
              <FieldLabel>기본 기록</FieldLabel>
              <div style={{ display: 'flex', gap: 10 }}>
                <NumInput value={form.distance} onChange={(v) => set('distance', v)} placeholder="0.0" unit="km" />
                <NumInput value={form.minutes} onChange={(v) => set('minutes', v)} placeholder="분" mode="numeric" />
                <NumInput value={form.seconds} onChange={(v) => set('seconds', v)} placeholder="초" mode="numeric" />
              </div>
              {form.pace && <div style={{ marginTop: 8, fontSize: 13, color: 'var(--label-secondary)' }}>
                평균 페이스 <b style={{ color: 'var(--label-primary)' }}>{form.pace} /km</b> (자동 계산)</div>}
            </>
          )}

          <FieldLabel>{isToday ? '오늘 몸 상태' : '몸 상태'}</FieldLabel>
          <div style={{ display: 'flex', gap: 10 }}>
            {FEEL_OPTIONS.map((f) => (
              <button key={f.v} onClick={() => set('feel', f.v)}
                style={{ flex: 1, padding: '12px 6px', borderRadius: 14, border: 'none', cursor: 'pointer',
                  transition: 'all .15s', background: form.feel === f.v ? 'var(--tint)' : 'var(--fill-tertiary)',
                  transform: form.feel === f.v ? 'scale(1.05)' : 'none' }}>
                <div style={{ fontSize: 24, lineHeight: 1 }}>{f.emoji}</div>
                <div style={{ fontSize: 11, fontWeight: 600, marginTop: 5,
                  color: form.feel === f.v ? '#fff' : 'var(--label-tertiary)' }}>{f.label}</div>
              </button>
            ))}
          </div>

          {/* 선택 입력 접기 — 입력 부담 최소화 */}
          {!noRun && (
            <button onClick={() => setDetailOpen(!detailOpen)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '18px 0 0', background: 'none',
                border: 'none', cursor: 'pointer', color: 'var(--tint)', fontSize: 14, fontWeight: 600, padding: 0 }}>
              <Icon name={detailOpen ? 'ChevronUp' : 'ChevronDown'} size={16} strokeWidth={2.4} />
              심박·케이던스·통증 자세히 입력 {detailOpen ? '접기' : ''}
            </button>
          )}

          {(detailOpen || noRun) && (
            <div className="anim-in">
              {!noRun && (
                <>
                  <FieldLabel>심박 · 케이던스</FieldLabel>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <NumInput value={form.avgHr} onChange={(v) => set('avgHr', v)} placeholder="평균" unit="bpm" mode="numeric" />
                    <NumInput value={form.maxHr} onChange={(v) => set('maxHr', v)} placeholder="최대" unit="bpm" mode="numeric" />
                    <NumInput value={form.cadence} onChange={(v) => set('cadence', v)} placeholder="170" unit="spm" mode="numeric" />
                  </div>
                </>
              )}

              <FieldLabel>불편한 곳 (선택)</FieldLabel>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {BODY_PARTS.map((p) => {
                  const on = pain.includes(p);
                  return (
                    <button key={p} onClick={() => setPain((prev) => on ? prev.filter((x) => x !== p) : [...prev, p])}
                      style={{ padding: '7px 14px', borderRadius: 999, border: 'none', cursor: 'pointer',
                        fontSize: 14, fontWeight: 600, transition: 'all .12s',
                        background: on ? 'rgba(255,56,60,0.14)' : 'var(--fill-tertiary)',
                        color: on ? 'var(--accent-red)' : 'var(--label-secondary)' }}>{p}</button>
                  );
                })}
              </div>
              {pain.map((p) => (
                <div key={p} style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6, color: 'var(--label-primary)' }}>
                    {p} · {painLevels[p] || 3}/10</div>
                  <input type="range" min={1} max={10} value={painLevels[p] || 3}
                    onChange={(e) => setPainLevels((prev) => ({ ...prev, [p]: parseInt(e.target.value, 10) }))}
                    style={{ width: '100%', accentColor: 'var(--accent-red)' }} />
                </div>
              ))}
              {maxPain >= 4 && <div style={{ marginTop: 10 }}>
                <Banner tone="warn">통증 4/10 이상 — 코치가 회복 우선으로 판단해요.</Banner></div>}
            </div>
          )}

          <FieldLabel>{isToday ? '오늘 한 훈련 · 소감' : '한 훈련 · 소감'} {noRun ? '' : '(선택)'}</FieldLabel>
          <div style={{ background: 'var(--fill-tertiary)', borderRadius: 12, padding: '12px 14px' }}>
            <textarea value={form.note} onChange={(e) => set('note', e.target.value)}
              placeholder={'한 일을 자유롭게 적어주세요 — 코치가 요약·분석에 반영해요.\n예: 폼 드릴 15분, 푸쉬업 30×2, 철봉 20×3. 발목 괜찮았음'}
              rows={3} style={{ border: 'none', outline: 'none', background: 'none', width: '100%', resize: 'none',
                fontSize: 16, color: 'var(--label-primary)', lineHeight: 1.5 }} />
          </div>

          {error && <div style={{ marginTop: 14 }}><Banner tone="error">{error}</Banner></div>}

          <div style={{ padding: '18px 0 8px' }}>
            <CTA onClick={save} icon="Sparkles"
              disabled={noRun ? !form.note.trim() : (!form.distance && !form.minutes)}>
              저장하고 리뷰 받기</CTA>
          </div>
        </div>
      )}
    </Modal>
  );
}
