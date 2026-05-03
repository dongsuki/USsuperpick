"""FMP API + SEC 10-K 본문 발췌 + 한국 거시 다이제스트를 단일 입력 JSON으로 패키징."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

FMP_BASE = "https://financialmodelingprep.com/api/v3"
SEC_BASE = "https://www.sec.gov"
SEC_DATA = "https://data.sec.gov"
SEC_UA = os.environ.get("SEC_USER_AGENT", "USsuperpick-Research loveds7724@gmail.com")

# 10-K 본문 발췌 길이 (문자 단위)
ITEM_1_LIMIT = 12000
ITEM_1A_LIMIT = 8000

# 한국 거시 다이제스트 캐시 파일 (weekly_trend_digest.py가 채움)
TREND_CACHE_PATH = Path(__file__).parent / "_trend_digest_cache.md"


def _fmp(path: str, fmp_key: str) -> Any:
    """FMP API GET 헬퍼."""
    sep = "&" if "?" in path else "?"
    url = f"{FMP_BASE}/{path}{sep}apikey={fmp_key}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_fmp_package(ticker: str, fmp_key: str) -> dict:
    """FMP에서 1종목 데이터 6종 fetch."""
    profile_list = _fmp(f"profile/{ticker}", fmp_key)
    if not profile_list:
        raise ValueError(f"FMP /profile returned empty for {ticker}")
    return {
        "profile": profile_list[0],
        "income_quarterly": _fmp(f"income-statement/{ticker}?period=quarter&limit=8", fmp_key),
        "cash_flow_quarterly": _fmp(f"cash-flow-statement/{ticker}?period=quarter&limit=6", fmp_key),
        "ratios_quarterly": _fmp(f"ratios/{ticker}?period=quarter&limit=4", fmp_key),
        "analyst_estimates_annual": _fmp(f"analyst-estimates/{ticker}?period=annual&limit=4", fmp_key),
    }


def fetch_forex_usdkrw(fmp_key: str) -> float:
    """현재 USD/KRW 환율 (FMP /quote/USDKRW)."""
    r = _fmp("quote/USDKRW", fmp_key)
    return float(r[0]["price"])


def fetch_latest_10k_excerpts(cik: str) -> dict:
    """SEC EDGAR에서 최근 10-K accession 찾고 Item 1 / Item 1A 본문 발췌.

    Args:
        cik: 회사 CIK 번호 (10자리, 0 padding 포함). FMP /profile에서 받은 값.

    Returns:
        {filing_form, filing_date, accession, url, item_1_business, item_1a_risk_factors}
    """
    cik_padded = str(cik).zfill(10) if not str(cik).startswith("000") else str(cik)
    submissions_url = f"{SEC_DATA}/submissions/CIK{cik_padded}.json"
    r = requests.get(submissions_url, headers={"User-Agent": SEC_UA, "Accept": "application/json"}, timeout=30)
    r.raise_for_status()
    sub = r.json()

    forms = sub["filings"]["recent"]
    accession_10k = None
    filing_date_10k = None
    primary_doc = None
    for i in range(len(forms["form"])):
        if forms["form"][i] == "10-K":
            accession_10k = forms["accessionNumber"][i]
            filing_date_10k = forms["filingDate"][i]
            primary_doc = forms["primaryDocument"][i]
            break
    if not accession_10k:
        return {"filing_form": "10-K", "filing_date": None, "accession": None,
                "url": None, "item_1_business": "", "item_1a_risk_factors": ""}

    accession_no_dashes = accession_10k.replace("-", "")
    cik_int = int(cik_padded)  # URL에선 leading zero 제거
    doc_url = f"{SEC_BASE}/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{primary_doc}"

    r = requests.get(doc_url, headers={"User-Agent": SEC_UA}, timeout=60)
    r.raise_for_status()
    html = r.text

    # HTML → plain text (간단 정제)
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text
            .replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&#160;", " ").replace("&#8217;", "'")
            .replace("&#8220;", '"').replace("&#8221;", '"')
            .replace("&#8211;", "-").replace("&#174;", "(R)")
            .replace("&#8482;", "(TM)"))
    text = re.sub(r"\s+", " ", text)

    # Item 1 본문 시작 위치 (TOC가 아닌 실제 본문 — "PART I Item 1. Business" 패턴)
    item1_start = text.find("PART I Item 1. Business")
    if item1_start < 0:
        item1_start = text.find("Item 1. Business. Overview")
    if item1_start < 0:
        item1_start = 0

    item1a_start = text.find("Item 1A.", item1_start + 100)
    if item1a_start < 0:
        item1a_start = item1_start + ITEM_1_LIMIT

    item1_end = min(item1a_start, item1_start + ITEM_1_LIMIT)
    item1_excerpt = text[item1_start:item1_end].strip()

    item1b_start = text.find("Item 1B.", item1a_start + 100)
    if item1b_start < 0:
        item1b_start = item1a_start + ITEM_1A_LIMIT
    item1a_end = min(item1b_start, item1a_start + ITEM_1A_LIMIT)
    item1a_excerpt = text[item1a_start:item1a_end].strip()

    return {
        "filing_form": "10-K",
        "filing_date": filing_date_10k,
        "accession": accession_10k,
        "url": doc_url,
        "item_1_business": item1_excerpt,
        "item_1a_risk_factors": item1a_excerpt,
    }


def load_trend_digest() -> list[str]:
    """주 1회 생성된 메가트렌드 마스터 다이제스트를 로드. 없으면 빈 리스트."""
    if not TREND_CACHE_PATH.exists():
        return []
    text = TREND_CACHE_PATH.read_text(encoding="utf-8").strip()
    # 라인 단위로 잘라서 list로 (각 라인이 하나의 트렌드 인용)
    return [line.strip() for line in text.split("\n") if line.strip()]


def build_input_json(ticker: str, fmp_key: str, snapshot_date: str | None = None) -> dict:
    """종목 1개에 대한 LLM 입력 JSON을 빌드."""
    from datetime import date
    snapshot = snapshot_date or str(date.today())

    fmp = fetch_fmp_package(ticker, fmp_key)
    profile = fmp["profile"]
    forex_rate = fetch_forex_usdkrw(fmp_key)

    cik = profile.get("cik", "")
    sec = fetch_latest_10k_excerpts(cik) if cik else {
        "filing_form": "10-K", "filing_date": None, "accession": None, "url": None,
        "item_1_business": "", "item_1a_risk_factors": "",
    }

    input_data = {
        "ticker": ticker,
        "snapshot_date": snapshot,
        "exchange_rate": {"pair": "USDKRW", "rate": forex_rate, "source": f"FMP quote {snapshot}"},
        "company": {
            "name": profile["companyName"],
            "exchange": profile["exchangeShortName"],
            "sector": profile["sector"],
            "industry": profile["industry"],
            "market_cap_usd": profile["mktCap"],
            "employees": profile["fullTimeEmployees"],
            "ceo": profile["ceo"],
            "ipo_date": profile["ipoDate"],
            "description": profile["description"],
            "current_price_usd": profile["price"],
            "range_52w": profile["range"],
            "beta": profile["beta"],
            "source": f"FMP /profile {snapshot}",
        },
        "financials_quarterly": [
            {"date": x["date"], "period": x["period"], "revenue": x["revenue"],
             "grossProfit": x["grossProfit"], "operatingIncome": x["operatingIncome"],
             "netIncome": x["netIncome"], "eps": x["eps"], "reportedCurrency": x["reportedCurrency"]}
            for x in fmp["income_quarterly"]
        ],
        "cash_flow_quarterly": [
            {"date": x["date"], "ocf": x["operatingCashFlow"], "fcf": x["freeCashFlow"],
             "cashAtEnd": x["cashAtEndOfPeriod"]}
            for x in fmp["cash_flow_quarterly"]
        ],
        "ratios_quarterly": [
            {"date": x["date"], "grossMargin": x["grossProfitMargin"],
             "operatingMargin": x["operatingProfitMargin"], "netMargin": x["netProfitMargin"]}
            for x in fmp["ratios_quarterly"]
        ],
        "analyst_estimates_annual": [
            {"year": x["date"][:4], "revenue_estimate_usd": x["estimatedRevenueAvg"],
             "eps_estimate": x["estimatedEpsAvg"], "n_analysts": x["numberAnalystEstimatedRevenue"]}
            for x in fmp["analyst_estimates_annual"]
        ],
        "sec_excerpts": sec,
        "macro_trend_digest": load_trend_digest(),
    }
    return input_data


def serialize_for_llm(input_data: dict) -> str:
    """LLM에 보낼 JSON 직렬화."""
    return json.dumps(input_data, ensure_ascii=False, indent=2)
