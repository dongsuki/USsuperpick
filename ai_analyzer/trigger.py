"""분석 실행 여부 판단.

트리거 정책 (사용자 결정):
1. 신규 진입 (new_entry) — AI분석_본문이 비어있음
2. 분기실적 갱신 (earnings_update) — 'AI분석_분석분기'(마지막 분석 시점에 사용된 최신분기 값)와
   현재 '최신분기'(mark.py가 매일 채움)가 다름 → 새 분기 데이터가 들어왔다는 신호
그 외 = skip. stale(주기적 갱신) 정책 없음.
"""
from __future__ import annotations

import os
from typing import Literal

import requests

BASE_ID_DEFAULT = os.environ.get("AIRTABLE_BASE_ID", "appAh82iPV3cH6Xx5")
TABLE_ID_DEFAULT = "tbljCB2CnDe2eWB3M"
VIEW_ID_DEFAULT = "viwioKkozk9MTIT84"  # 종합점수(재무) 50+ 뷰 (N/A 제외, AI 분석 대상)

TriggerReason = Literal["new_entry", "earnings_update", "skip"]


def list_view_records(view_id: str = VIEW_ID_DEFAULT,
                      base_id: str = BASE_ID_DEFAULT,
                      table_id: str = TABLE_ID_DEFAULT) -> list[dict]:
    """뷰의 모든 record를 페이지네이션으로 가져온다."""
    pat = os.environ.get("AIRTABLE_PAT") or os.environ.get("AIRTABLE_API_KEY")
    if not pat:
        raise RuntimeError("AIRTABLE_PAT (or AIRTABLE_API_KEY) not set")

    records = []
    offset = None
    while True:
        params = {"view": view_id}
        if offset:
            params["offset"] = offset
        r = requests.get(
            f"https://api.airtable.com/v0/{base_id}/{table_id}",
            headers={"Authorization": f"Bearer {pat}"},
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def should_analyze(record: dict) -> tuple[TriggerReason, str]:
    """record가 분석 대상인지 판단.

    Returns:
        (reason, message) — reason in {"new_entry", "earnings_update", "skip"}
    """
    fields = record.get("fields", {})
    ai_body = fields.get("AI분석_본문", "")
    ai_analyzed_quarter = (fields.get("AI분석_분석분기") or "").strip()
    current_quarter = (fields.get("최신분기") or "").strip()

    # 1. 신규 진입
    if not ai_body or not ai_body.strip():
        return "new_entry", "AI 분석 없음 (신규 진입)"

    # 2. 분기 변경 — mark.py가 새 분기 데이터를 채워 넣었으면 갱신
    if current_quarter and ai_analyzed_quarter != current_quarter:
        return "earnings_update", f"분기 변경: {ai_analyzed_quarter or '(없음)'} → {current_quarter}"

    return "skip", "분기 변경 없음"
