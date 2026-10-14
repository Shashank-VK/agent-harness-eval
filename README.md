# Agent Harness Eval (`agent-harness-eval`)

> **Coding-Agent Prompt Strategy Evaluation Harness**  
> Empirical comparison between **Direct Baseline** and **Chain-of-Thought (CoT)** prompt strategies across a 15-problem classic Data Structures & Algorithms (DSA) benchmark suite.
>
> *Note: This repository will be published at [github.com/Shashank-VK/agent-harness-eval](https://github.com/Shashank-VK/agent-harness-eval).*

---

## Overview

`agent-harness-eval` is an end-to-end evaluation harness designed to benchmark coding-agent prompts with scientific rigor. It evaluates real LLM generations on 15 classic DSA problems under two distinct prompting strategies:
1. **Baseline Strategy**: Plain, direct instruction requesting the Python 3 solution without extra commentary.
2. **Chain-of-Thought (CoT) Strategy**: Systematic instruction prompting the model to reason step-by-step through logic, edge cases, and complexity before providing code.

Every generated solution is extracted from Markdown fenced blocks and executed inside an isolated, sandboxed Python subprocess against hidden test cases under strict timeout limits (5.0s).

### Key Features
- **Zero-Invention Guarantee**: 100% of benchmark numbers originate from real LLM completions executed against the Pollinations OpenAI-compatible endpoint (`https://text.pollinations.ai/openai`).
- **Zero API Keys Required**: Completely self-contained and reproducible without private credentials.
- **Subprocess Isolation Sandbox**: Sandboxed execution preventing test pollution, infinite loops, and hangs.
- **Granular Failure Taxonomy**: Attributed categorisation (`syntax_error`, `runtime_error`, `wrong_answer`, `timeout`, `no_code`).
- **Mock-Gated Unit Tests**: Complete 28-test TDD suite with strict isolation from the network.

---

## Benchmark Results (Real Measured Run)

*Run executed against Pollinations OpenAI endpoint (`openai` model) on 2026-10-14.*

| Metric | Baseline (Direct Code) | CoT (Think Step-by-Step) | Delta (CoT vs Baseline) |
| :--- | :---: | :---: | :---: |
| **Pass@1 Rate** | **100.0%** (15/15) | **100.0%** (15/15) | **+0.0%** |
| **Avg Tokens / Problem** | **670.40** | **1185.73** | **+515.33** (+76.9%) |
| **Median Latency (p50)** | **8.32s** | **18.48s** | **+10.16s** (+122.1%) |
| **Avg Prompt Tokens** | 436.13 | 450.13 | +14.00 |
| **Avg Completion Tokens** | 234.27 | 735.60 | +501.33 (+214.0%) |
| **Failures** | 0 | 0 | 0 |

### Key Empirical Finding
For standard, well-scoped DSA problems at this model tier, **Chain-of-Thought delivered identical 100% accuracy to the concise direct prompt, while consuming 76.9% more tokens and more than doubling median latency (+122.1%)**. Detailed per-problem breakdowns are available in [report.md](report.md) and [results/results.csv](results/results.csv).

---

## How Metrics Are Measured

1. **Pass@1**:
   $$\text{Pass@1} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{all hidden tests pass for problem } i)}{N}$$
   Solutions must pass 100% of hidden test cases (minimum 4-7 cases per problem covering standard cases, negative numbers, edge boundaries, and empty structures).

2. **Avg Tokens / Problem**:
   Measured directly from the API response `usage` object (`prompt_tokens`, `completion_tokens`, and `total_tokens`). If usage is absent, a heuristic of $\approx 1.33 \times \text{words}$ is applied.

3. **p50 Latency**:
   Median end-to-end response time measured via `time.perf_counter()` from HTTP request dispatch until full response parsing.

4. **Failure Taxonomy**:
   - `syntax_error`: Code fails Python AST compilation via `compile(code, "<solution>", "exec")`.
   - `runtime_error`: Code raises an unhandled exception (e.g. `ZeroDivisionError`, `IndexError`, missing function) during execution.
   - `wrong_answer`: Function returns a value not equal to the expected output for a hidden test.
   - `timeout`: Execution exceeds the 5.0s subprocess time limit (e.g. infinite loops).
   - `no_code`: Model fails to produce a valid Python code block.

---

## Problem Suite (15 DSA Problems)

The benchmark includes 15 classic DSA problems across 5 core topics located in `problems/`:
1. `01_two_sum.json` (Easy, Array)
2. `02_valid_parentheses.json` (Easy, Stack)
3. `03_best_time_to_buy_and_sell_stock.json` (Easy, Array)
4. `04_valid_anagram.json` (Easy, String)
5. `05_valid_palindrome.json` (Easy, Two-Pointer)
6. `06_maximum_subarray.json` (Medium, Array - Kadane's)
7. `07_merge_intervals.json` (Medium, Array)
8. `08_product_of_array_except_self.json` (Medium, Array)
9. `09_longest_consecutive_sequence.json` (Medium, Hashmap)
10. `10_subarray_sum_equals_k.json` (Medium, Hashmap - Prefix Sums)
11. `11_container_with_most_water.json` (Medium, Two-Pointer)
12. `12_trapping_rain_water.json` (Hard, Two-Pointer)
13. `13_longest_substring_without_repeating_characters.json` (Medium, String / Sliding Window)
14. `14_eval_rpn.json` (Medium, Stack)
15. `15_daily_temperatures.json` (Medium, Stack / Monotonic Stack)

---

## Getting Started & Repro

### Prerequisites
- Python 3.10+
- `pytest` (e.g., `pip install pytest requests`)
- Network access for live evaluations (no API key required)

### 1. Run Unit Tests (Mock-Gated, No Network)
The test suite validates problem schema, client retry/backoff, mock determinism, sandboxed execution, failure categorization, and report generation:

```bash
make test
# or: pytest -v
```

**Test Status**: **28 of 28 passed** in 2.96s.

### 2. Run Live Benchmark Evaluation (One-Command Repro)
To execute both strategies against the live Pollinations endpoint and regenerate `report.md` and `results/results.csv`:

```bash
make eval
# or: python3 run_eval.py
```

The script automatically:
1. Probes endpoint connectivity with exponential backoff.
2. Runs all 15 problems under Baseline strategy.
3. Runs all 15 problems under CoT strategy.
4. Emits `results/baseline_results.json`, `results/cot_results.json`, and `results/results.csv`.
5. Compiles and writes the comparative [report.md](report.md).

---

## Project Structure

```
agent-harness-eval/
├── Makefile                # One-command targets (make test, make eval)
├── PLAN.md                 # Scope and architecture specification
├── README.md               # Project documentation & results summary
├── report.md               # Generated Markdown comparative evaluation report
├── run_eval.py             # CLI runner for live benchmark runs
├── problems/               # 15 DSA problem JSON definitions
│   ├── 01_two_sum.json
│   └── ...
├── results/                # Output datasets from real runs
│   ├── baseline_results.json
│   ├── cot_results.json
│   └── results.csv
├── src/
│   ├── __init__.py
│   ├── harness.py          # Sandboxed runner, code extractor, and grader
│   ├── llm.py              # Pollinations API client & MockLLM
│   └── report.py           # Metrics computation and report generator
└── tests/
    ├── __init__.py
    ├── test_harness.py     # Subprocess sandbox and taxonomy tests
    ├── test_llm.py         # LLM client & MockLLM tests
    ├── test_problems.py    # Problem JSON schema and test case tests
    └── test_report.py      # Metrics calculation and export tests
```
