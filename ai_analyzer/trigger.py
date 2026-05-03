"""분석 실행 여부 판단 — 신규 진입 + 분기실적 발표 후 갱신."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Literal

import requests

BASE_ID_DEFAULT = os.environ.get("AIRTABLE_BASE_ID", "appAh82iPV3cH6Xx5")
TABLE_ID_DEFAULT = "tbljCB2CnDe2eWB3M"
VIEW_ID_DEFAULT = "viwtY7XrICnpAgyvY"  # 마크미너비니 뷰

TriggerReason = Literal["new_entry", "earnings_update", "stale", "skip"]


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


def should_analyze(record: dict, *, stale_days: int = 90) -> tuple[TriggerReason, str]:
    """이 record를 분석해야 하는지 판단."""
    fields = record.get("fields", {})
    ai_body = fields.get("AI분석_본문", "")
    ai_updated = fields.get("AI분석_갱신일")
    latest_quarter = fields.get("최신분기")  # 예: "2026-Q1"
    update_date = fields.get("업데이트 날짜")  # mark.py가 매일 갱신

    # 1. 본문 비어있음 → 신규 진입
    if not ai_body or not ai_body.strip():
        return "new_entry", "AI 분석 없음 (신규 진입)"

    # 2. 분기실적 발표 후 갱신 필요
    # 최신분기가 ai_updated 이후로 변경됐는지 확인
    if latest_quarter and ai_updated:
        # 최신분기 종료일 + 60일 (실적 발표 늦은 케이스 포함) > ai_updated 이면 갱신 필요
        try:
            year_str, q_str = latest_quarter.split("-Q")
            year = int(year_str)
            q = int(q_str)
            quarter_end = {1: f"{year}-03-31", 2: f"{year}-06-30",
                           3: f"{year}-09-30", 4: f"{year}-12-31"}[q]
            quarter_release_deadline = (datetime.fromisoformat(quarter_end) + timedelta(days=60)).date()
            ai_dt = datetime.fromisoformat(ai_updated[:10]).date()
            if quarter_release_deadline > ai_dt:
                return "earnings_update", f"{latest_quarter} 실적 갱신 필요 (마지막 분석 {ai_updated})"
        except (ValueError, KeyError):
            pass

    # 3. 너무 오래된 분석 → stale 갱신
    if ai_updated:
        try:
            ai_dt = datetime.fromisoformat(ai_updated[:10]).date()
            if (date.today() - ai_dt).days > stale_days:
                return "stale", f"마지막 분석 {ai_updated} ({stale_days}일 초과)"
        except ValueError:
            pass

    return "skip", "최근 분석됨"
