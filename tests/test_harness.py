import pytest
from src.harness import (
    extract_python_code,
    build_prompt,
    execute_code_sandbox,
    run_eval,
)
from src.llm import MockLLM


SAMPLE_PROBLEM = {
    "id": "two_sum",
    "title": "Two Sum",
    "difficulty": "Easy",
    "topic": "array",
    "statement": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
    "function_name": "two_sum",
    "function_signature": "def two_sum(nums: list[int], target: int) -> list[int]:",
    "hidden_tests": [
        {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
    ],
}


def test_extract_python_code_fenced():
    raw = """Here is the solution:
```python
def two_sum(nums: list[int], target: int) -> list[int]:
    return [0, 1]
```
Hope that helps!"""
    extracted = extract_python_code(raw)
    assert extracted is not None
    assert "def two_sum" in extracted
    assert "Hope that helps" not in extracted


def test_extract_python_code_no_code():
    raw = "I am an AI and I cannot write code for this."
    assert extract_python_code(raw) is None
    assert extract_python_code("") is None


def test_build_prompt_baseline():
    prompt = build_prompt(SAMPLE_PROBLEM, strategy="baseline")
    assert "Two Sum" in prompt or "nums" in prompt
    assert "def two_sum" in prompt
    assert "step by step" not in prompt.lower()


def test_build_prompt_cot():
    prompt = build_prompt(SAMPLE_PROBLEM, strategy="cot")
    assert "def two_sum" in prompt
    assert "step by step" in prompt.lower()


def test_build_prompt_invalid():
    with pytest.raises(ValueError):
        build_prompt(SAMPLE_PROBLEM, strategy="invalid_strat")


def test_execute_code_sandbox_success():
    code = """
def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is True
    assert result["failure_category"] is None
    assert len(result["test_outcomes"]) == 2


def test_execute_code_sandbox_class_solution():
    code = """
class Solution:
    def two_sum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, num in enumerate(nums):
            diff = target - num
            if diff in seen:
                return [seen[diff], i]
            seen[num] = i
        return []
"""
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is True
    assert result["failure_category"] is None


def test_execute_code_sandbox_syntax_error():
    code = "def two_sum(nums, target) return [0, 1]"
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is False
    assert result["failure_category"] == "syntax_error"


def test_execute_code_sandbox_runtime_error():
    code = """
def two_sum(nums: list[int], target: int) -> list[int]:
    return 1 / 0
"""
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is False
    assert result["failure_category"] == "runtime_error"


def test_execute_code_sandbox_wrong_answer():
    code = """
def two_sum(nums: list[int], target: int) -> list[int]:
    return [99, 99]
"""
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is False
    assert result["failure_category"] == "wrong_answer"


def test_execute_code_sandbox_timeout():
    code = """
def two_sum(nums: list[int], target: int) -> list[int]:
    import time
    while True:
        time.sleep(0.1)
"""
    result = execute_code_sandbox(
        code=code,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=0.5,
    )
    assert result["passed"] is False
    assert result["failure_category"] == "timeout"


def test_execute_code_sandbox_no_code():
    result = execute_code_sandbox(
        code=None,
        function_name="two_sum",
        hidden_tests=SAMPLE_PROBLEM["hidden_tests"],
        timeout_sec=2.0,
    )
    assert result["passed"] is False
    assert result["failure_category"] == "no_code"


def test_run_eval_success():
    correct_code = """```python
def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
```"""
    mock_llm = MockLLM(default_response=correct_code)
    eval_res = run_eval(SAMPLE_PROBLEM, strategy="baseline", llm_client=mock_llm)

    assert eval_res["problem_id"] == "two_sum"
    assert eval_res["strategy"] == "baseline"
    assert eval_res["passed"] is True
    assert eval_res["failure_category"] is None
    assert eval_res["latency_seconds"] >= 0
    assert eval_res["tokens_used"] > 0
    assert eval_res["extracted_code"] is not None


def test_run_eval_cot_failure_taxonomy():
    bad_code = "I cannot solve this."
    mock_llm = MockLLM(default_response=bad_code)
    eval_res = run_eval(SAMPLE_PROBLEM, strategy="cot", llm_client=mock_llm)

    assert eval_res["passed"] is False
    assert eval_res["failure_category"] == "no_code"
