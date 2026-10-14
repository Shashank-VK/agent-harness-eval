import pytest
from unittest.mock import patch, MagicMock
import requests

from src.llm import LLMResponse, MockLLM, PollinationsLLM, estimate_tokens


def test_estimate_tokens():
    text = "def two_sum(nums, target): return []"
    tokens = estimate_tokens(text)
    assert tokens > 0
    assert estimate_tokens("") == 0


def test_mock_llm_default_response():
    mock = MockLLM(default_response="def solve(): return 42")
    resp = mock.complete("Solve problem 1")
    assert isinstance(resp, LLMResponse)
    assert resp.content == "def solve(): return 42"
    assert resp.total_tokens > 0
    assert resp.latency_seconds >= 0
    assert len(mock.history) == 1
    assert mock.history[0]["prompt"] == "Solve problem 1"


def test_mock_llm_canned_mapping():
    canned = {
        "two_sum": "def two_sum(): pass",
        "valid_parentheses": "def is_valid(): pass"
    }
    mock = MockLLM(canned_responses=canned, default_response="def fallback(): pass")
    
    resp1 = mock.complete("Please implement two_sum in python")
    assert resp1.content == "def two_sum(): pass"

    resp2 = mock.complete("Unknown problem")
    assert resp2.content == "def fallback(): pass"


def test_pollinations_llm_success():
    fake_response = {
        "id": "pllns_123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "```python\ndef solution():\n    return True\n```"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    }

    client = PollinationsLLM(max_retries=1)
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = fake_response

        resp = client.complete("Write code")
        assert resp.content == "```python\ndef solution():\n    return True\n```"
        assert resp.prompt_tokens == 50
        assert resp.completion_tokens == 20
        assert resp.total_tokens == 70
        assert resp.latency_seconds >= 0


def test_pollinations_llm_usage_fallback():
    fake_response = {
        "id": "pllns_123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "return True"
                }
            }
        ]
        # usage omitted
    }

    client = PollinationsLLM(max_retries=1)
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = fake_response

        resp = client.complete("Write code")
        assert resp.content == "return True"
        assert resp.total_tokens > 0


def test_pollinations_llm_retry_on_failure():
    client = PollinationsLLM(max_retries=3, backoff_factor=0.01)
    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.RequestException("Network glitch"),
            MagicMock(status_code=500, text="Internal Server Error"),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                }
            )
        ]

        resp = client.complete("Hello")
        assert resp.content == "ok"
        assert mock_post.call_count == 3


def test_pollinations_llm_exhausted_retries():
    client = PollinationsLLM(max_retries=2, backoff_factor=0.01)
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.RequestException("Unreachable")
        with pytest.raises(RuntimeError) as exc_info:
            client.complete("Hello")
        assert "Failed to get response" in str(exc_info.value)
        assert mock_post.call_count == 2
