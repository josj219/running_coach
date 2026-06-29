"""Claude 코치 서비스 — async 호출 + COACH_MOCK 분기 + JSON 파싱.

불변식: 사용자 데이터(로그)는 AI와 독립적으로 먼저 커밋한다. AI는 부가물.
"""

import json
import re
from typing import AsyncIterator

from ..config import get_settings


class CoachError(Exception):
    """AI 호출 실패 — 라우터에서 503 AI_UNAVAILABLE로 변환."""


MOCK_RESPONSES = {
    "review": {
        "summary": "이지 런 5.2km(Zone 2, 평균 심박 143)를 완료했다.",
        "coach_comment": "5.2km를 평균 심박 143으로 마쳤다. 동일 페이스 기준 심박이 직전 기록보다 낮아 유산소 효율이 개선되고 있다.",
        "strengths": "- 심박 Zone 2 안정 유지\n- 케이던스 170spm 이상 유지",
        "improvements": "- 후반 1km 페이스 8초 하락 — 초반 배분 조정 필요",
        "recovery": "low",
        "recovery_reason": "통증 0/10, 피로도 3/10, 달성률 100%",
        "next_impact": "계획대로 진행 가능",
        "plan_adjust_needed": False,
    },
    "daily": {
        "warmup": "걷기 5분 + 다이내믹 스트레칭 5분",
        "main": "이지 런 5km @ 6:30~7:00/km (Zone 2, 심박 130~145)",
        "cooldown": "걷기 5분 + 하체 정적 스트레칭",
        "note": "왼쪽 발목 감각 확인 우선. 통증 시 즉시 중단.",
        "adjusted": False,
        "detail": "#### 워밍업 (10분)\n- 걷기 5분\n- 레그 스윙 × 10회\n#### 메인 세트 (35분)\n- 5km @ 6:30~7:00/km\n#### 쿨다운 (10분)\n- 걷기 5분 + 종아리/햄스트링 스트레칭",
        "session": None,
    },
    "weekly": {
        "direction": "🟡 기초 복귀 단계 — 조깅 재개 + 폼 교정 병행",
        "direction_reason": "3주+ 공백 후 복귀. 볼륨 보수적 유지, 통증 확인 최우선.",
        "goal_km": 20,
        "intensity": "낮음",
        "sessions": [],
        "cautions": ["통증 발생 시 즉시 중단"],
    },
    "adjust": {"reason": "컨디션 저하 반영", "changes": [], "kept": []},
    "extract": {
        "found": True, "distance_km": 5.2, "duration_sec": 1860, "avg_pace": "5:58",
        "avg_hr": 145, "max_hr": 162, "cadence": 172, "elevation_m": 30,
        "note": "(mock) 스크린샷에서 거리·시간·페이스·심박을 읽었다.",
    },
    "evaluation": {
        "coach_message": "📈 복귀 첫 주 치고 심박 안정성이 좋다. 다음 주는 주 3회 조깅으로 빈도를 올리자.",
        "detail_md": "### 목표 진척도\n| 항목 | 현재 |\n|---|---|\n| 남은 기간 | 21주 |\n| 준비도 | 중 |",
    },
}


def _mock_week_sessions() -> list[dict]:
    """COACH_MOCK 주간 계획용 — 오늘부터 일요일까지 이번 주 날짜로 모의 세션 생성."""
    from datetime import date, timedelta
    today = date.today()
    templates = [
        ("easy", "이지 런 4km", 4, 35, "6:40~7:00 /km",
         "유산소 베이스 재가동", "점심 헬스장 — 트레드밀, 심박 130~145"),
        ("strength", "하체·코어 40분", 0, 40, None,
         "착지 안정성 보강", "점심 헬스장 — 스쿼트·런지·코어"),
        ("rest", "휴식일", 0, 0, None,
         "초과회복", "수면 7시간+ · 스트레칭"),
        ("easy", "이지 런 5km", 5, 35, "6:30~7:00 /km",
         "Zone 2 유산소 효율 회복", "퇴근런 — 한강 코스"),
        ("drill", "폼 드릴 15분 + 빠른 걷기 15분", 0, 30, None,
         "신경근 활성화 — 폼 효율 회복", "점심 헬스장 — High Knees·A-skip"),
        ("easy", "이지 런 5km", 5, 35, "6:30~6:50 /km",
         "케이던스 감각 회복", "주말 오전 — 야외"),
        ("long", "롱 조깅 6km", 6, 45, "6:50~7:10 /km",
         "시간 기반 지구력 회복", "주말 오전 — 통증 시 중단"),
    ]
    out = []
    for d in range(today.weekday(), 7):
        kind, title, dist, mins, pace, focus, note = templates[d]
        out.append({
            "date": (today + timedelta(days=d - today.weekday())).isoformat(),
            "kind": kind, "title": title, "distance_km": dist or None,
            "duration_min": mins or None, "duration_min_max": None,
            "target_pace": pace, "focus": focus, "note": note,
            "is_rest": kind == "rest",
        })
    return out


def parse_json_block(text: str) -> dict:
    """응답에서 ```json ...``` 블록 또는 첫 { } JSON을 추출."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = m.group(1) if m else None
    if raw is None:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise CoachError("AI 응답에서 JSON을 찾지 못했습니다.")
        raw = text[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise CoachError(f"AI JSON 파싱 실패: {e}") from e


def _client():
    import anthropic
    s = get_settings()
    if not s.anthropic_api_key:
        raise CoachError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")
    return anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)


async def generate(kind: str, system_prompt: str, user_message: str,
                   image_b64: str | None = None, image_media_type: str = "image/png") -> dict:
    """완성 응답을 받아 JSON으로 파싱해 반환. kind는 mock 키."""
    s = get_settings()
    if s.coach_mock:
        if s.coach_mock == "__ERROR__":
            raise CoachError("mock error")
        data = MOCK_RESPONSES[kind]
        if kind == "weekly" and not data.get("sessions"):
            data = {**data, "sessions": _mock_week_sessions()}
        return data

    content: list | str = user_message
    if image_b64:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": image_media_type, "data": image_b64}},
            {"type": "text", "text": user_message},
        ]
    try:
        client = _client()
        resp = await client.messages.create(
            model=s.claude_model, max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
    except CoachError:
        raise
    except Exception as e:  # noqa: BLE001 — 네트워크/키/5xx 전부 503으로
        raise CoachError(f"Claude API 호출 실패: {e}") from e
    text = "\n".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return parse_json_block(text)


async def extract_workout_image(image_b64: str, media_type: str = "image/jpeg") -> dict:
    """운동 기록 스크린샷에서 거리·시간·페이스·심박 등 수치를 추출해 dict로 반환."""
    from ..prompts import WORKOUT_IMAGE_EXTRACT_PROMPT
    return await generate(
        "extract", WORKOUT_IMAGE_EXTRACT_PROMPT,
        "이 운동 기록 스크린샷에서 수치를 추출해줘.",
        image_b64=image_b64, image_media_type=media_type,
    )


async def stream_text(system_prompt: str, user_message: str) -> AsyncIterator[str]:
    """토큰 스트림(SSE용). COACH_MOCK 시 짧은 모의 스트림."""
    s = get_settings()
    if s.coach_mock:
        if s.coach_mock == "__ERROR__":
            raise CoachError("mock error")
        for chunk in ["분석 ", "중입니다… ", "(mock)"]:
            yield chunk
        return
    try:
        client = _client()
        async with client.messages.stream(
            model=s.claude_model, max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for token in stream.text_stream:
                yield token
    except CoachError:
        raise
    except Exception as e:  # noqa: BLE001
        raise CoachError(f"Claude API 스트림 실패: {e}") from e
