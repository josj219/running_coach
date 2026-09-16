"""LLM이 낸 주간 계획 세션을 DB 제약(계획당 날짜 하나)에 맞게 정리한다.

sessions 테이블은 (plan_id, session_date) 유니크다. 모델이 같은 날 러닝과 보강을 따로 내면
그대로 INSERT하다 IntegrityError로 계획 생성 전체가 실패한다(2026-09-07 실사용 재현:
9/8에 '트레드밀 복귀 조깅'과 '하체 근력 + 코어'가 함께 옴). 프롬프트에 "하루 하나"를 적어도
모델은 가끔 어긴다 — 여기서 결정적으로 합쳐 저장 실패를 없앤다.
"""

from __future__ import annotations

# 보강 계열 — 같은 날 러닝과 겹치면 러닝을 본 세션으로 두고 이쪽은 note에 접는다.
SUPPLEMENT_KINDS = {"strength", "core", "mobility", "drill"}


def _is_run(sd: dict) -> bool:
    return not sd.get("is_rest") and sd.get("kind") not in SUPPLEMENT_KINDS and sd.get("kind") != "rest"


def _fold_label(sd: dict) -> str:
    title = (sd.get("title") or sd.get("kind") or "보강").strip()
    dur = sd.get("duration_min")
    return f"{title} ({dur}분)" if dur else title


def merge_same_date(sessions: list[dict], date_key: str = "date") -> list[dict]:
    """같은 날짜의 세션을 하나로 합친다. 입력 순서는 유지하고, 날짜 없는 항목은 그대로 통과.

    규칙:
    - 본 세션 = 그날 첫 러닝(휴식·보강 제외). 러닝이 없으면 그날 첫 항목.
    - 나머지는 본 세션 note 끝에 "+ 함께: <title> (<분>분)"으로 접는다 — 정보는 버리지 않는다.
    - 합쳐진 세션의 duration_min은 둘의 합(둘 다 있을 때만). 거리·페이스는 본 세션 것.
    """
    by_date: dict[str, dict] = {}
    order: list[str] = []
    passthrough: list[dict] = []
    for sd in sessions:
        d = sd.get(date_key)
        if not d:
            passthrough.append(sd)
            continue
        if d not in by_date:
            by_date[d] = dict(sd)
            order.append(d)
            continue
        primary = by_date[d]
        # 러닝이 뒤에 왔으면 그쪽을 본 세션으로 승격하고, 앞의 것을 접는다
        if not _is_run(primary) and _is_run(sd):
            primary, sd = dict(sd), primary
            by_date[d] = primary
        note = (primary.get("note") or "").rstrip()
        primary["note"] = f"{note}\n+ 함께: {_fold_label(sd)}" if note else f"+ 함께: {_fold_label(sd)}"
        if primary.get("duration_min") and sd.get("duration_min"):
            primary["duration_min"] = primary["duration_min"] + sd["duration_min"]
        # 본 세션이 휴식이었는데 보강이 붙으면 더는 휴식이 아니다
        if primary.get("is_rest") and not sd.get("is_rest"):
            primary["is_rest"] = False
            if primary.get("kind") == "rest":
                primary["kind"] = sd.get("kind", "other")
    return [by_date[d] for d in order] + passthrough
