"""Anthropic API (Claude Sonnet 4.6) 호출 래퍼."""
from __future__ import annotations

import os
import time

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16000
TIMEOUT_SEC = 240.0


class LLMResult:
    def __init__(self, text: str, input_tokens: int, output_tokens: int, model: str, duration_sec: float):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model
        self.duration_sec = duration_sec

    def cost_usd(self, input_per_m: float = 3.0, output_per_m: float = 15.0) -> float:
        """Sonnet 4.6 기준 비용 추정 (입력 $3/M, 출력 $15/M)."""
        return (self.input_tokens * input_per_m + self.output_tokens * output_per_m) / 1_000_000


def call_sonnet(system_prompt: str, user_msg: str, *, max_retries: int = 1) -> LLMResult:
    """Sonnet 4.6 호출. 재시도 1회 (rate limit / timeout 시)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            start = time.time()
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                timeout=TIMEOUT_SEC,
            )
            elapsed = time.time() - start
            text = resp.content[0].text
            return LLMResult(
                text=text,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                model=resp.model,
                duration_sec=elapsed,
            )
        except (anthropic.RateLimitError, anthropic.APITimeoutError) as e:
            last_err = e
            if attempt < max_retries:
                wait = 30 * (attempt + 1)
                print(f"  [LLM retry] {type(e).__name__}: waiting {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"unreachable; last_err={last_err}")
