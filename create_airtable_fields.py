"""
Airtable Metadata API를 사용해 markmarkmark 미국주식 통합용 신규 필드를 일괄 생성한다.

사용법:
  1) Airtable에서 PAT(Personal Access Token) 발급
     - https://airtable.com/create/tokens
     - 스코프: schema.bases:write (필수), data.records:read 권장
     - 액세스 베이스: appAh82iPV3cH6Xx5
  2) 환경 변수 설정:
     PowerShell> $env:AIRTABLE_PAT="patXXXXX..."
     bash      > export AIRTABLE_PAT="patXXXXX..."
  3) 실행:
     python create_airtable_fields.py
  4) 이미 존재하는 필드명은 422 에러로 스킵되며, 결과 요약이 출력됨.

대상 베이스/테이블:
  - Base: appAh82iPV3cH6Xx5
  - Table: tbljCB2CnDe2eWB3M (현재 mark.py + scanner_v2가 채우는 테이블)

생성되는 필드 (총 38개):
  - 매출액 raw 분기 8개
  - 영업이익률(%) 분기 3 + 연간 3 = 6개
  - 순이익률 분기 8 + 연간 3 = 11개
  - ROE 분기 3 + 연간 3 = 6개
  - PER 분기 3 + 연간 3 = 6개
  - PEG 최신분기 1개
"""

import os
import sys
import time
import requests

# Windows 콘솔에서 이모지/한글 출력을 위한 UTF-8 강제
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_ID = "appAh82iPV3cH6Xx5"
TABLE_ID = "tbljCB2CnDe2eWB3M"
META_URL = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables/{TABLE_ID}/fields"

# 모든 필드는 number 타입, 소수점 2자리. 매출액만 정수(precision 0)로.
NUMBER_2DP = {"type": "number", "options": {"precision": 2}}
NUMBER_INT = {"type": "number", "options": {"precision": 0}}
CHECKBOX = {"type": "checkbox", "options": {"icon": "check", "color": "greenBright"}}
SINGLE_TEXT = {"type": "singleLineText"}

FIELDS_TO_CREATE = [
    # 매출액 raw (분기 8개) - 큰 정수라서 precision 0
    ("매출액_최신분기", NUMBER_INT),
    ("매출액_전분기", NUMBER_INT),
    ("매출액_전전분기", NUMBER_INT),
    ("매출액_4분기전", NUMBER_INT),
    ("매출액_5분기전", NUMBER_INT),
    ("매출액_6분기전", NUMBER_INT),
    ("매출액_7분기전", NUMBER_INT),
    ("매출액_8분기전", NUMBER_INT),

    # 영업이익률(%) raw (분기 3 + 연간 3)
    ("영업이익률(%)_최신분기", NUMBER_2DP),
    ("영업이익률(%)_전분기", NUMBER_2DP),
    ("영업이익률(%)_전전분기", NUMBER_2DP),
    ("영업이익률(%)_1년", NUMBER_2DP),
    ("영업이익률(%)_2년", NUMBER_2DP),
    ("영업이익률(%)_3년", NUMBER_2DP),

    # 순이익률 raw (분기 8 + 연간 3)
    ("순이익률_최신분기", NUMBER_2DP),
    ("순이익률_전분기", NUMBER_2DP),
    ("순이익률_전전분기", NUMBER_2DP),
    ("순이익률_4분기전", NUMBER_2DP),
    ("순이익률_5분기전", NUMBER_2DP),
    ("순이익률_6분기전", NUMBER_2DP),
    ("순이익률_7분기전", NUMBER_2DP),
    ("순이익률_8분기전", NUMBER_2DP),
    ("순이익률_1년", NUMBER_2DP),
    ("순이익률_2년", NUMBER_2DP),
    ("순이익률_3년", NUMBER_2DP),

    # ROE (분기 3 + 연간 3)
    ("ROE_최신분기", NUMBER_2DP),
    ("ROE_전분기", NUMBER_2DP),
    ("ROE_전전분기", NUMBER_2DP),
    ("ROE_1년", NUMBER_2DP),
    ("ROE_2년", NUMBER_2DP),
    ("ROE_3년", NUMBER_2DP),

    # PER (분기 3 + 연간 3)
    ("PER_최신분기", NUMBER_2DP),
    ("PER_전분기", NUMBER_2DP),
    ("PER_전전분기", NUMBER_2DP),
    ("PER_1년", NUMBER_2DP),
    ("PER_2년", NUMBER_2DP),
    ("PER_3년", NUMBER_2DP),

    # PEG (1)
    ("PEG_최신분기", NUMBER_2DP),

    # NPM 성장률 4분기전 (markmarkmark 마진 개선 점수 1년 비교용)
    ("NPM성장률_4분기전", NUMBER_2DP),

    # 이동평균 존 (한국 ma_zone_scanner 정의 동일, scanner_v2가 채움)
    ("3일선 위", CHECKBOX),
    ("3존", CHECKBOX),
    ("8존", CHECKBOX),
    ("15존", CHECKBOX),
    ("20존", CHECKBOX),
    ("33존", CHECKBOX),
    ("50존", CHECKBOX),
    ("슈퍼존", CHECKBOX),

    # 한글 종목명 (네이버 크롤링, mark.py가 채움)
    ("한글명", SINGLE_TEXT),

    # 최신분기 표기 (예: '2026-Q1' — FMP의 가장 최근 분기)
    ("최신분기", SINGLE_TEXT),

    # === Phase 5: EPS Trend (4 카테고리 × 5 시점 = 20개, Yahoo 출처) ===
    ("현재분기_현재추정", NUMBER_2DP),
    ("현재분기_7일전", NUMBER_2DP),
    ("현재분기_30일전", NUMBER_2DP),
    ("현재분기_60일전", NUMBER_2DP),
    ("현재분기_90일전", NUMBER_2DP),
    ("다음분기_현재추정", NUMBER_2DP),
    ("다음분기_7일전", NUMBER_2DP),
    ("다음분기_30일전", NUMBER_2DP),
    ("다음분기_60일전", NUMBER_2DP),
    ("다음분기_90일전", NUMBER_2DP),
    ("현재연도_현재추정", NUMBER_2DP),
    ("현재연도_7일전", NUMBER_2DP),
    ("현재연도_30일전", NUMBER_2DP),
    ("현재연도_60일전", NUMBER_2DP),
    ("현재연도_90일전", NUMBER_2DP),
    ("내년_현재추정", NUMBER_2DP),
    ("내년_7일전", NUMBER_2DP),
    ("내년_30일전", NUMBER_2DP),
    ("내년_60일전", NUMBER_2DP),
    ("내년_90일전", NUMBER_2DP),

    # === Phase 5: Forward PE / PEG (단년 성장률 기준, Yahoo + FMP) ===
    ("선행PER_올해", NUMBER_2DP),
    ("선행PER_내년", NUMBER_2DP),
    ("선행PER_내후년", NUMBER_2DP),
    ("선행PEG_올해", NUMBER_2DP),
    ("선행PEG_내년", NUMBER_2DP),
    ("선행PEG_내후년", NUMBER_2DP),
]


def create_field(pat: str, name: str, type_def: dict) -> tuple:
    """필드 1개 생성. (status, message) 반환."""
    payload = {"name": name, **type_def}
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(META_URL, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            return ("created", f"OK")
        elif r.status_code == 422:
            # 이미 존재하는 필드 등
            try:
                err = r.json().get("error", {}).get("message", r.text)
            except Exception:
                err = r.text
            if "already exists" in err.lower() or "duplicate" in err.lower():
                return ("exists", "이미 존재")
            return ("error", f"422: {err}")
        else:
            return ("error", f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("error", f"예외: {e}")


def main():
    pat = os.getenv("AIRTABLE_PAT")
    if not pat:
        print("❌ 환경 변수 AIRTABLE_PAT 가 설정되지 않았습니다.")
        print("   PowerShell: $env:AIRTABLE_PAT=\"patXXXXX...\"")
        print("   Linux/Mac : export AIRTABLE_PAT=\"patXXXXX...\"")
        sys.exit(1)

    print(f"🎯 대상: Base {BASE_ID} / Table {TABLE_ID}")
    print(f"📋 생성 시도: 총 {len(FIELDS_TO_CREATE)}개 필드\n")

    counts = {"created": 0, "exists": 0, "error": 0}
    errors = []

    for name, type_def in FIELDS_TO_CREATE:
        status, msg = create_field(pat, name, type_def)
        counts[status] += 1
        icon = {"created": "✅", "exists": "🟡", "error": "❌"}[status]
        print(f"  {icon} {name:25} → {msg}")
        if status == "error":
            errors.append((name, msg))
        # rate limit 회피 (Airtable Metadata API: 5 req/sec)
        time.sleep(0.25)

    print("\n" + "=" * 50)
    print("📊 결과 요약")
    print(f"  ✅ 신규 생성: {counts['created']}개")
    print(f"  🟡 이미 존재: {counts['exists']}개")
    print(f"  ❌ 에러     : {counts['error']}개")

    if errors:
        print("\n에러 상세:")
        for name, msg in errors:
            print(f"  - {name}: {msg}")
        sys.exit(2)

    print("\n🎉 완료. 이제 GitHub Actions 워크플로우를 수동 트리거하면")
    print("   확장된 mark.py가 새 필드들을 채워줍니다.")


if __name__ == "__main__":
    main()
