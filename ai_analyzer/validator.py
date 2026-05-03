"""LLM 출력 검증 — JSON 카드 파싱, 점수 범위, 본문 길이."""
from __future__ import annotations

import json
import re

# 카드 JSON 블럭 추출 패턴 — 본문 마지막의 ```json {...} ``` 블럭
JSON_CARD_PATTERN = re.compile(r"```json\s*\n(\{.*?\})\s*\n```", re.DOTALL)

# 본문 길이 허용 범위
MIN_BODY_CHARS = 4000
MAX_BODY_CHARS = 18000


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

    return body, card
