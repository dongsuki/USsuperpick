"""ai_analyzer 메인 entry point.

사용법:
    # 단일 종목
    python -m ai_analyzer.analyze --ticker LQDA

    # 트리거 종목 자동 (마크미너비니 뷰 전체 → 신규/분기실적 갱신 필요한 것만)
    python -m ai_analyzer.analyze --auto

    # 전체 백필 (모든 뷰 종목)
    python -m ai_analyzer.analyze --backfill-all

환경변수:
    ANTHROPIC_API_KEY  (필수)
    FMP_API_KEY        (필수)
    AIRTABLE_PAT 또는 AIRTABLE_API_KEY  (필수)
    AIRTABLE_BASE_ID   (선택, 기본 appAh82iPV3cH6Xx5)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date

from .data_packager import build_input_json, serialize_for_llm
from .prompts import SYSTEM_PROMPT_V3_4, build_user_message
from .llm_client import call_sonnet
from .validator import parse_output, ValidationError
from .airtable_writer import find_record_by_ticker, update_ai_fields, mark_failed
from .trigger import list_view_records, should_analyze


def analyze_ticker(ticker: str, fmp_key: str, *, dry_run: bool = False) -> dict:
    """단일 종목 분석 → Airtable update.

    Returns:
        {ticker, status, body_chars, input_tokens, output_tokens, cost_usd, duration_sec, reason}
    """
    print(f"\n[{ticker}] Building input package...")
    input_data = build_input_json(ticker, fmp_key)
    input_json = serialize_for_llm(input_data)
    print(f"  Input JSON: {len(input_json)} chars")

    user_msg = build_user_message(input_json)
    print(f"  Calling Sonnet 4.6...")
    result = call_sonnet(SYSTEM_PROMPT_V3_4, user_msg)
    print(f"  Done in {result.duration_sec:.1f}s — in:{result.input_tokens} out:{result.output_tokens} cost:${result.cost_usd():.3f}")

    try:
        body, card = parse_output(result.text)
    except ValidationError as e:
        print(f"  [VALIDATION FAIL] {e}")
        # 1회 재시도
        print(f"  Retrying once...")
        result = call_sonnet(SYSTEM_PROMPT_V3_4, user_msg)
        try:
            body, card = parse_output(result.text)
        except ValidationError as e2:
            print(f"  [VALIDATION FAIL #2] {e2}")
            if not dry_run:
                rec = find_record_by_ticker(ticker)
                if rec:
                    mark_failed(rec["id"], str(e2))
            return {
                "ticker": ticker, "status": "validation_failed",
                "reason": str(e2), "duration_sec": result.duration_sec,
                "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd(),
            }

    if dry_run:
        print(f"  [DRY RUN] body={len(body)}c, bottleneck={card['bottleneck_score']}, durability={card['durability_score']}")
        return {
            "ticker": ticker, "status": "dry_run_ok", "body_chars": len(body),
            "bottleneck": card["bottleneck_score"], "durability": card["durability_score"],
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "cost_usd": result.cost_usd(), "duration_sec": result.duration_sec,
        }

    # Airtable update — record + 현재 최신분기 함께 fetch
    rec = find_record_by_ticker(ticker)
    if not rec:
        print(f"  [SKIP] {ticker} record not found in Airtable")
        return {"ticker": ticker, "status": "record_not_found"}

    rid = rec["id"]
    latest_quarter = (rec.get("fields", {}).get("최신분기") or "").strip()
    update_ai_fields(rid, body, card, latest_quarter=latest_quarter)
    print(f"  [OK] Airtable updated (record={rid}, quarter={latest_quarter or 'N/A'})")
    return {
        "ticker": ticker, "status": "ok", "body_chars": len(body),
        "bottleneck": card["bottleneck_score"], "durability": card["durability_score"],
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cost_usd": result.cost_usd(), "duration_sec": result.duration_sec,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="USsuperpick AI 분석")
    parser.add_argument("--ticker", help="단일 종목 티커 (예: LQDA)")
    parser.add_argument("--auto", action="store_true",
                        help="마크미너비니 뷰 전체 → 트리거 종목만 (신규+분기실적+stale)")
    parser.add_argument("--backfill-all", action="store_true",
                        help="뷰 전체 종목 강제 분석 (대량 비용 주의)")
    parser.add_argument("--dry-run", action="store_true", help="Airtable update 안 함")
    parser.add_argument("--limit", type=int, default=0, help="처리할 종목 수 상한 (0=무제한)")
    args = parser.parse_args()

    fmp_key = os.environ.get("FMP_API_KEY")
    if not fmp_key:
        print("ERROR: FMP_API_KEY env var required")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY env var required")
        sys.exit(1)
    if not (os.environ.get("AIRTABLE_PAT") or os.environ.get("AIRTABLE_API_KEY")):
        print("ERROR: AIRTABLE_PAT (or AIRTABLE_API_KEY) env var required")
        sys.exit(1)

    if args.ticker:
        result = analyze_ticker(args.ticker, fmp_key, dry_run=args.dry_run)
        print(f"\nFinal: {result}")
        return

    if args.auto or args.backfill_all:
        print(f"Loading 마크미너비니 view records...")
        records = list_view_records()
        print(f"  {len(records)} records loaded.")

        targets = []
        for rec in records:
            ticker = rec.get("fields", {}).get("티커")
            if not ticker:
                continue
            if args.backfill_all:
                targets.append((ticker, "backfill", "전체 백필"))
                continue
            reason_kind, reason_msg = should_analyze(rec)
            if reason_kind != "skip":
                targets.append((ticker, reason_kind, reason_msg))

        if args.limit > 0:
            targets = targets[: args.limit]
        print(f"  {len(targets)} tickers to analyze")
        for t, kind, msg in targets:
            print(f"    {t} [{kind}] {msg}")

        total_cost = 0.0
        success = 0
        for ticker, kind, msg in targets:
            try:
                result = analyze_ticker(ticker, fmp_key, dry_run=args.dry_run)
                if result.get("status") == "ok":
                    success += 1
                total_cost += result.get("cost_usd", 0.0) or 0.0
                # rate limit 회피용 sleep (Anthropic API tier에 따라 조정)
                time.sleep(2)
            except Exception as e:
                print(f"  [{ticker}] EXCEPTION: {e}")

        print(f"\n=== Summary ===")
        print(f"  Success: {success}/{len(targets)}")
        print(f"  Total cost: ${total_cost:.2f}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
