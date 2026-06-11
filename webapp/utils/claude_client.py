"""Anthropic Claude API 호출 래퍼.

ANTHROPIC_API_KEY 환경변수가 필요하다. 모델은 claude-sonnet-4-6 을 사용한다.
이미지(Garmin/Strava 스크린샷)가 있으면 vision 메시지 형식으로 전달한다.
"""

import os
import base64

try:
    import anthropic
except ImportError:  # 패키지 미설치 환경에서도 import 자체는 실패하지 않도록
    anthropic = None

from . import file_manager

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


class ClaudeError(Exception):
    """Claude 호출 관련 오류."""


def _get_client():
    if anthropic is None:
        raise ClaudeError(
            "anthropic 패키지가 설치되어 있지 않습니다. `pip install anthropic` 후 다시 시도하세요."
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ClaudeError(
            "ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "터미널에서 export ANTHROPIC_API_KEY=sk-... 후 앱을 다시 실행하세요."
        )
    return anthropic.Anthropic(api_key=api_key)


def get_coaching_system_prompt() -> str:
    """CLAUDE.md의 코칭 철학을 시스템 프롬프트로 반환.

    파일을 직접 읽어 항상 최신 철학을 반영한다. 파일이 없으면 핵심 요약 폴백.
    """
    base = file_manager.get_base_dir()
    path = os.path.join(base, "CLAUDE.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception:  # noqa: BLE001
        return (
            "당신은 고고조 전용 AI 러닝 코치이다. "
            "사용자의 목표, 일정, 훈련 이력, 컨디션, 회복 상태, 날씨를 종합 고려해 "
            "장기적 러닝 성장을 지원한다. 데이터 기반으로 판단하고, 과거 기록을 절대 잊지 않으며, "
            "칭찬보다 객관적 분석을 우선한다. 회복도 훈련의 일부로 본다."
        )


# 오타 호환 별칭 (지침 문서의 함수명과 맞춤)
def get_coachig_system_prompt() -> str:  # noqa: D401 - intentional alias
    return get_coaching_system_prompt()


def _image_block(image_bytes: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": b64,
        },
    }


def get_coaching_response(
    system_prompt: str,
    user_message: str,
    image_data: bytes | None = None,
    image_media_type: str = "image/png",
) -> str:
    """Claude를 호출해 코칭 응답(텍스트)을 반환한다.

    system_prompt: 스킬별 시스템 프롬프트 (CLAUDE.md 철학 포함 권장)
    user_message: 사용자 입력 + 컨텍스트
    image_data: 첨부 이미지 바이트 (optional, vision)
    """
    client = _get_client()

    if image_data:
        content = [
            _image_block(image_data, image_media_type),
            {"type": "text", "text": user_message},
        ]
    else:
        content = user_message

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:  # noqa: BLE001
        raise ClaudeError(f"Claude API 호출 실패: {e}") from e

    # 텍스트 블록 모으기
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()
