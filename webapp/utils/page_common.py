"""페이지 공통 헬퍼: import 경로 설정, 사이드바, Claude 호출 래퍼."""

import os
import sys

import streamlit as st


def bootstrap():
    """각 페이지 상단에서 호출. utils import 경로 보장."""
    webapp_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if webapp_root not in sys.path:
        sys.path.insert(0, webapp_root)


def api_status_sidebar():
    if os.environ.get("ANTHROPIC_API_KEY"):
        st.sidebar.success("API 연결 준비됨", icon="✅")
    else:
        st.sidebar.warning("ANTHROPIC_API_KEY 미설정", icon="⚠️")


def run_coach(system_prompt: str, user_message: str, image_data=None, image_media_type="image/png"):
    """Claude 호출. 스킬 시스템 프롬프트 앞에 공통 코칭 철학을 붙인다.

    (응답텍스트, 에러문자열) 튜플 반환. 성공 시 에러는 None.
    """
    from utils import claude_client as cc

    full_system = cc.get_coaching_system_prompt() + "\n\n" + system_prompt
    try:
        text = cc.get_coaching_response(
            full_system, user_message, image_data=image_data, image_media_type=image_media_type
        )
        return text, None
    except cc.ClaudeError as e:
        return None, str(e)
    except Exception as e:  # noqa: BLE001
        return None, f"예기치 못한 오류: {e}"
