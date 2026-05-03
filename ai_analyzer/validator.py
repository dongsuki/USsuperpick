"""LLM 출력 검증 — JSON 카드 파싱, 점수 범위, 본문 길이.

normalize_body: LLM이 가끔 따르지 않는 시점 표현·출처 메타를 자동 치환.
"""
from __future__ import annotations

import json
import re

# 카드 JSON 블럭 추출 패턴 — 본문 마지막의 ```json {...} ``` 블럭
JSON_CARD_PATTERN = re.compile(r"```json\s*\n(\{.*?\})\s*\n```", re.DOTALL)

# 본문 길이 허용 범위 (SEC 본문 미수신 시 짧을 수 있음)
MIN_BODY_CHARS = 2500
MAX_BODY_CHARS = 18000

# 후처리 자동 치환 — LLM이 시스템 프롬프트 가끔 안 따를 때 안전망
_REPLACEMENTS: list[tuple[str, str]] = [
    # 시점 표현 — '현재' → '작성 시점'
    (r'현재 주가', '작성 시점 주가'),
    (r'현재 시총', '작성 시점 시총'),
    (r'현재 시가총액', '작성 시점 시가총액'),
    (r'현재 P/?E', '작성 시점 P/E'),
    (r'현재 P/?S', '작성 시점 P/S'),
    (r'현재 PER', '작성 시점 PER'),
    (r'현재 멀티플', '작성 시점 멀티플'),
    (r'지금 주가', '작성 시점 주가'),
    # 출처 메타 — 본문에서 잘 안 빠지는 패턴 청소
    (r'FMP\s*(?:API\s*)?(?:기준|데이터)?\s*에 (?:따르면|의하면)[,\s]*', ''),
    (r'(?:이번 입력에\s*)?macro_trend_digest\s*(?:데이터|키)?[^.]*?\.\s*', ''),
    (r'sec_excerpts\s*(?:키|데이터|값)?[^.]*?\.\s*', ''),
]


def normalize_body(text: str) -> str:
    """후처리: 금지 표현 자동 치환."""
    for pattern, replacement in _REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


class ValidationError(Exception):
    pass


def parse_output(text: str) -> tuple[str, dict]:
    """LLM 출력을 (본문 마크다운, JSON 카드 dict)로 분리.

    Returns:
        (body, card)
    Raises:
        ValidationError: JSON 카드 누락 또는 파싱 실패, 점수 범위 위반, 본문 길이 위반
    """
    m = JSON_CARD_PATTERN.search(text)
    if not m:
        raise ValidationError("JSON card block not found in output")
    try:
        card = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise ValidationError(f"JSON card parse failed: {e}")

    # 점수 범위 검증
    for score_field in ("bottleneck_score", "durability_score"):
        v = card.get(score_field)
        if v is None or not isinstance(v, (int, float)) or not (0 <= v <= 10):
            raise ValidationError(f"{score_field} out of range or missing: {v}")

    # 필수 필드
    for required in ("ticker", "company_name", "summary_3lines", "verdict"):
        if not card.get(required):
            raise ValidationError(f"required field missing in card: {required}")

    # 본문 길이 (JSON 카드 부분 제거 후)
    body = JSON_CARD_PATTERN.sub("", text).rstrip()
    n = len(body)
    if n < MIN_BODY_CHARS or n > MAX_BODY_CHARS:
        raise ValidationError(f"body length out of range: {n} (allowed {MIN_BODY_CHARS}~{MAX_BODY_CHARS})")

    # 후처리 자동 치환 (시점 표현·출처 메타)
    body = normalize_body(body)

    return body, card
