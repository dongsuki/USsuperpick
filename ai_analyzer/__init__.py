"""USsuperpick AI 분석 모듈

종목 1개에 대해 FMP 정형 데이터 + SEC 10-K 본문 발췌 + 한국 증권가 거시 다이제스트를
입력으로 Sonnet 4.6을 호출, 5섹션 본문 + JSON 카드를 생성해 Airtable에 저장한다.

Public:
    analyze_ticker(ticker: str) -> dict
"""
from .analyze import analyze_ticker

__all__ = ["analyze_ticker"]
