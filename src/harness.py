"""Evaluation harness for running and grading coding-agent prompts in a sandboxed subprocess."""

import json
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

from src.llm import LLMResponse, PollinationsLLM


def extract_python_code(raw_text: Optional[str]) -> Optional[str]:
    """Extract python code from raw text, prioritizing fenced python blocks."""
    if not raw_text or not raw_text.strip():
        return None

    # Priority 1: ```python ... ``` or ```py ... ```
    pattern_python = r"```(?:python|py)\s*\n(.*?)```"
    matches = re.findall(pattern_python, raw_text, re.DOTALL | re.IGNORECASE)
    if matches:
        # If multiple blocks, find one that defines a function or class, or pick the last one
        for match in reversed(matches):
            if "def " in match:
                return match.strip()
        return matches[-1].strip()

    # Priority 2: Generic ``` ... ```
    pattern_generic = r"```\s*\n(.*?)```"
    generic_matches = re.findall(pattern_generic, raw_text, re.DOTALL)
    if generic_matches:
        for match in reversed(generic_matches):
            if "def " in match:
                return match.strip()
        return generic_matches[-1].strip()

    # Priority 3: Check if the raw text contains a function definition and is valid python
    if "def " in raw_text:
        # Try compiling the text
        try:
            compile(raw_text.strip(), "<string>", "exec")
            return raw_text.strip()
        except SyntaxError:
            pass

    return None


def build_prompt(problem: Dict[str, Any], strategy: str) -> str:
    """Build prompt for baseline or chain-of-thought (cot) strategy."""
    title = problem.get("title", "")
    statement = problem.get("statement", "")
    signature = problem.get("function_signature", "")

    if strategy == "baseline":
        return f"""You are an expert Python software engineer. Solve the following algorithmic problem:

Problem: {title}
Description: {statement}

Function Signature:
{signature}

Requirements:
- Implement the requested function in Python 3.
- Do NOT provide markdown explanation or tests.
- Enclose your solution strictly inside a ```python ... ``` code block.
"""

    elif strategy == "cot":
        return f"""You are an expert Python software engineer. Solve the following algorithmic problem:

Problem: {title}
Description: {statement}

Function Signature:
{signature}

Requirements:
- Think step by step: explain your logic, time and space complexity, and edge cases.
- Then, provide the complete, self-contained Python 3 implementation.
- Enclose your final solution inside a ```python ... ``` code block.
"""
    else:
        raise ValueError(f"Unknown strategy '{strategy}'. Supported strategies: 'baseline', 'cot'.")


RUNNER_SCRIPT_TEMPLATE = '''
import sys
import json
import math
import collections
import heapq
import itertools
from typing import *

def main():
    with open({test_file_repr}, "r", encoding="utf-8") as f:
        meta = json.load(f)

    code = meta["code"]
    function_name = meta["function_name"]
    hidden_tests = meta["hidden_tests"]

    user_globals = {}
    user_globals.update(globals())

    try:
        exec(code, user_globals)
    except Exception as e:
        sys.stdout.write(json.dumps({
            "passed": False,
            "failure_category": "runtime_error",
            "error_message": f"Execution setup error: {type(e).__name__}: {e}",
            "test_outcomes": []
        }))
        return

    target_func = user_globals.get(function_name)
    if not callable(target_func):
        # Check if wrapped in class Solution
        sol_cls = user_globals.get("Solution")
        if sol_cls and hasattr(sol_cls, function_name):
            try:
                inst = sol_cls()
                target_func = getattr(inst, function_name)
            except Exception as e:
                sys.stdout.write(json.dumps({
                    "passed": False,
                    "failure_category": "runtime_error",
                    "error_message": f"Could not instantiate Solution: {e}",
                    "test_outcomes": []
                }))
                return

    if not callable(target_func):
        sys.stdout.write(json.dumps({
            "passed": False,
            "failure_category": "runtime_error",
            "error_message": f"Function '{function_name}' not found or not callable",
            "test_outcomes": []
        }))
        return

    test_outcomes = []
    for idx, test_case in enumerate(hidden_tests):
        inputs = test_case["input"]
        expected = test_case["expected"]
        try:
            if isinstance(inputs, dict):
                actual = target_func(**inputs)
            elif isinstance(inputs, list):
                actual = target_func(*inputs)
            else:
                actual = target_func(inputs)

            passed = (actual == expected)
            outcome = {
                "test_index": idx,
                "passed": passed,
                "actual": actual,
                "expected": expected
            }
            test_outcomes.append(outcome)

            if not passed:
                sys.stdout.write(json.dumps({
                    "passed": False,
                    "failure_category": "wrong_answer",
                    "error_message": f"Test {idx} failed. Expected {expected}, got {actual}",
                    "test_outcomes": test_outcomes
                }))
                return

        except Exception as e:
            test_outcomes.append({
                "test_index": idx,
                "passed": False,
                "error": f"{type(e).__name__}: {e}"
            })
            sys.stdout.write(json.dumps({
                "passed": False,
                "failure_category": "runtime_error",
                "error_message": f"Test {idx} raised exception: {type(e).__name__}: {e}",
                "test_outcomes": test_outcomes
            }))
            return

    sys.stdout.write(json.dumps({
        "passed": True,
        "failure_category": None,
        "error_message": None,
        "test_outcomes": test_outcomes
    }))

if __name__ == "__main__":
    main()
'''


def execute_code_sandbox(
    code: Optional[str],
    function_name: str,
    hidden_tests: List[Dict[str, Any]],
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """Executes extracted python code in an isolated subprocess with timeout."""
    if not code or not code.strip():
        return {
            "passed": False,
            "failure_category": "no_code",
            "error_message": "No code extracted from model response.",
            "test_outcomes": [],
        }

    # Pre-compile to catch syntax errors immediately
    try:
        compile(code, "<solution>", "exec")
    except SyntaxError as e:
        return {
            "passed": False,
            "failure_category": "syntax_error",
            "error_message": f"SyntaxError: {e.msg} at line {e.lineno}",
            "test_outcomes": [],
        }

    with tempfile.NamedTemporaryFile("w+", suffix=".json", encoding="utf-8") as test_file, \
         tempfile.NamedTemporaryFile("w+", suffix=".py", encoding="utf-8") as script_file:

        meta = {
            "code": code,
            "function_name": function_name,
            "hidden_tests": hidden_tests,
        }
        json.dump(meta, test_file)
        test_file.flush()

        runner_src = RUNNER_SCRIPT_TEMPLATE.replace("{test_file_repr}", repr(test_file.name))
        script_file.write(runner_src)
        script_file.flush()

        try:
            proc = subprocess.run(
                [sys.executable, script_file.name],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "failure_category": "timeout",
                "error_message": f"Execution timed out after {timeout_sec} seconds.",
                "test_outcomes": [],
            }
        except Exception as e:
            return {
                "passed": False,
                "failure_category": "runtime_error",
                "error_message": f"Subprocess execution error: {e}",
                "test_outcomes": [],
            }

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0 and not stdout:
            return {
                "passed": False,
                "failure_category": "runtime_error",
                "error_message": f"Process exited with code {proc.returncode}: {stderr}",
                "test_outcomes": [],
            }

        try:
            result = json.loads(stdout)
            return result
        except json.JSONDecodeError:
            return {
                "passed": False,
                "failure_category": "runtime_error",
                "error_message": f"Could not decode sandbox output: {stdout} | {stderr}",
                "test_outcomes": [],
            }


def run_eval(
    problem: Dict[str, Any],
    strategy: str,
    llm_client: Optional[Any] = None,
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """Run evaluation for a single problem using specified strategy."""
    if llm_client is None:
        llm_client = PollinationsLLM()

    prompt = build_prompt(problem, strategy=strategy)
    response = llm_client.complete(prompt)

    extracted_code = extract_python_code(response.content)
    exec_result = execute_code_sandbox(
        code=extracted_code,
        function_name=problem["function_name"],
        hidden_tests=problem["hidden_tests"],
        timeout_sec=timeout_sec,
    )

    return {
        "problem_id": problem["id"],
        "problem_title": problem.get("title", problem["id"]),
        "difficulty": problem.get("difficulty", "Unknown"),
        "topic": problem.get("topic", "General"),
        "strategy": strategy,
        "passed": exec_result["passed"],
        "failure_category": exec_result["failure_category"],
        "latency_seconds": response.latency_seconds,
        "tokens_used": response.total_tokens,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "extracted_code": extracted_code,
        "raw_response": response.content,
        "error_message": exec_result.get("error_message"),
        "test_outcomes": exec_result.get("test_outcomes", []),
    }
