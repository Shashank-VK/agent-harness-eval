"""LLM client for Pollinations OpenAI-compatible endpoint and deterministic MockLLM for testing."""

from dataclasses import dataclass
import time
from typing import Dict, List, Optional
import requests


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation (~4 chars per token / ~1.3 tokens per word)."""
    if not text or not text.strip():
        return 0
    words = len(text.split())
    # Blend word-count and char-count heuristic
    token_est = max(1, int(words * 1.33))
    return token_est


class MockLLM:
    """Deterministic mock LLM for testing without network requests."""

    def __init__(
        self,
        canned_responses: Optional[Dict[str, str]] = None,
        default_response: str = "```python\ndef solution():\n    pass\n```",
    ):
        self.canned_responses = canned_responses or {}
        self.default_response = default_response
        self.history: List[Dict[str, str]] = []

    def complete(self, prompt: str, **kwargs) -> LLMResponse:
        self.history.append({"prompt": prompt, "kwargs": kwargs})

        matched_content = self.default_response
        for key, response_text in self.canned_responses.items():
            if key in prompt:
                matched_content = response_text
                break

        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = estimate_tokens(matched_content)
        total_tokens = prompt_tokens + completion_tokens

        return LLMResponse(
            content=matched_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_seconds=0.01,
        )


class PollinationsLLM:
    """Client for the free Pollinations OpenAI-compatible endpoint."""

    def __init__(
        self,
        endpoint: str = "https://text.pollinations.ai/openai",
        model: str = "openai",
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: int = 60,
    ):
        self.endpoint = endpoint
        self.model = model
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

    def complete(self, prompt: str, seed: Optional[int] = 42, **kwargs) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if seed is not None:
            payload["seed"] = seed

        payload.update(kwargs)

        headers = {"Content-Type": "application/json"}
        last_exception = None

        for attempt in range(self.max_retries):
            start_time = time.perf_counter()
            try:
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code >= 500 or response.status_code == 429:
                    raise requests.RequestException(
                        f"Server returned status {response.status_code}: {response.text[:200]}"
                    )

                response.raise_for_status()
                data = response.json()
                latency = round(time.perf_counter() - start_time, 3)

                content = ""
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]

                usage = data.get("usage")
                if usage and isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens", estimate_tokens(prompt))
                    completion_tokens = usage.get("completion_tokens", estimate_tokens(content))
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                else:
                    prompt_tokens = estimate_tokens(prompt)
                    completion_tokens = estimate_tokens(content)
                    total_tokens = prompt_tokens + completion_tokens

                return LLMResponse(
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_seconds=latency,
                )

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)

        raise RuntimeError(
            f"Failed to get response from {self.endpoint} after {self.max_retries} attempts: {last_exception}"
        )
