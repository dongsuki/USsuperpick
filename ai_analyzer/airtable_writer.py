"""Airtable 6개 신규 필드 update."""
from __future__ import annotations

import os
from datetime import date

import requests

BASE_ID_DEFAULT = os.environ.get("AIRTABLE_BASE_ID", "appAh82iPV3cH6Xx5")
TABLE_ID_DEFAULT = "tbljCB2CnDe2eWB3M"


def find_record_by_ticker(ticker: str, *, base_id: str = BASE_ID_DEFAULT,
                          table_id: str = TABLE_ID_DEFAULT) -> str | None:
    """티커로 record id 찾기. 없으면 None."""
    pat = os.environ.get("AIRTABLE_PAT") or os.environ.get("AIRTABLE_API_KEY")
    if not pat:
        raise RuntimeError("AIRTABLE_PAT (or AIRTABLE_API_KEY) not set")

    r = requests.get(
        f"https://api.airtable.com/v0/{base_id}/{table_id}",
        headers={"Authorization": f"Bearer {pat}"},
        params={"filterByFormula": f"{{티커}}='{ticker}'", "maxRecords": 1},
        timeout=30,
    )
    r.raise_for_status()
    records = r.json().get("records", [])
    return records[0]["id"] if records else None


def update_ai_fields(record_id: str, body: str, card: dict, *,
                     base_id: str = BASE_ID_DEFAULT,
                     table_id: str = TABLE_ID_DEFAULT) -> dict:
    """6개 신규 필드 PATCH."""
    pat = os.environ.get("AIRTABLE_PAT") or os.environ.get("AIRTABLE_API_KEY")
    if not pat:
        raise RuntimeError("AIRTABLE_PAT (or AIRTABLE_API_KEY) not set")

    summary_3lines = "\n".join(f"- {line}" for line in card.get("summary_3lines", []))
    data_sources_str = "; ".join(card.get("data_sources", []))[:200]

    fields = {
        "AI분석_본문": body,
        "AI분석_요약3줄": summary_3lines,
        "AI분석_병목점수": int(card["bottleneck_score"]),
        "AI분석_지속성점수": int(card["durability_score"]),
        "AI분석_갱신일": str(date.today()),
        "AI분석_데이터출처": data_sources_str,
    }

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    r = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"fields": fields},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Airtable PATCH failed {r.status_code}: {r.text[:300]}")
    return r.json()


def mark_failed(record_id: str, reason: str, *,
                base_id: str = BASE_ID_DEFAULT,
                table_id: str = TABLE_ID_DEFAULT) -> None:
    """분석 실패 시 데이터출처 필드에 실패 사유 기록 (분석_본문은 비움)."""
    pat = os.environ.get("AIRTABLE_PAT") or os.environ.get("AIRTABLE_API_KEY")
    if not pat:
        return
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    requests.patch(
        url,
        headers={"Authorization": f"Bearer {pat}", "Content-Type": "application/json; charset=utf-8"},
        json={"fields": {"AI분석_데이터출처": f"FAIL {date.today()}: {reason[:150]}"}},
        timeout=30,
    )
