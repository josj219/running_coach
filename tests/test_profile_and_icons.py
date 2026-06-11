"""프로필 이미지 + 기록 카드 유형별 아이콘/타입 추출 회귀 테스트 (순수 함수).

- 프로필 이미지: 비정사각형 업로드 → center-crop + 256px 리사이즈, base64 data URI 왕복.
- `_extract_workout_type`: '- 종류: 헬스' 의 '종류:' 라벨 제거, 유형별로 아이콘이 갈리는지.
"""

import io
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_profimg_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

import app  # noqa: E402
from utils import file_manager as fm  # noqa: E402


# ── 프로필 이미지 파이프라인 ─────────────────────────────────────────────────

def _png_bytes(w, h, color=(120, 80, 200)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def test_save_resizes_to_square():
    from PIL import Image
    fm.save_profile_image(_png_bytes(800, 400))
    img = Image.open(fm._profile_image_path())
    assert img.size == (fm._PROFILE_IMG_SIZE, fm._PROFILE_IMG_SIZE)
    assert img.mode == "RGB"
    fm.delete_profile_image()


def test_read_b64_roundtrip_and_delete():
    assert fm.read_profile_image_b64() == ""           # 없을 때 빈 문자열
    fm.save_profile_image(_png_bytes(300, 300))
    uri = fm.read_profile_image_b64()
    assert uri.startswith("data:image/png;base64,")
    fm.delete_profile_image()
    assert fm.read_profile_image_b64() == ""


def test_avatar_html_uses_image_when_present():
    uri = "data:image/png;base64,AAAA"
    html = app._avatar_html(uri, 38, "🏃", 19)
    assert "<img" in html and uri in html
    # 없으면 이모지 폴백
    fallback = app._avatar_html("", 38, "🏃", 19)
    assert "<img" not in fallback and "🏃" in fallback


# ── 유형별 아이콘 / '종류:' 라벨 제거 ────────────────────────────────────────

_STRENGTH = "## 훈련 내용\n- 종류: 헬스\n- 수치: 코어 3종\n\n## 훈련 리뷰\n근력 잘 수행. 달리기도 병행."
_RUNNING  = "## 훈련 내용\n- 종류: 달리기\n- 수치: 거리: 6.2km / 페이스: 5:30\n\n## 훈련 리뷰\n유산소 효율 개선. 근력 보강 추천."
_INTERVAL = "## 훈련 내용\n- 종류: 인터벌 400m x 8\n- 수치: 거리: 5km"


def test_workout_type_strips_label():
    assert app._extract_workout_type(_STRENGTH) == "헬스"          # '종류:' 제거
    assert app._extract_workout_type(_RUNNING) == "달리기"
    assert app._extract_workout_type(_INTERVAL).startswith("인터벌")


def test_icon_differs_by_type():
    """달리기와 헬스가 서로 다른 아이콘/색을 가져야 한다(이전엔 둘 다 💪)."""
    t_run  = app._extract_workout_type(_RUNNING)
    t_str  = app._extract_workout_type(_STRENGTH)
    assert app._session_emoji(t_run) != app._session_emoji(t_str)
    assert app._session_emoji(t_run) == "🏃"
    assert app._session_emoji(t_str) == "💪"


def test_running_log_mentioning_strength_not_misclassified():
    """러닝 로그 리뷰에 '근력' 이 섞여도 유형 기준이라 🏃 를 유지한다."""
    t = app._extract_workout_type(_RUNNING)   # '달리기'
    assert app._session_emoji(t) == "🏃"       # 전체 텍스트였다면 💪로 오판했을 케이스
