# Evaluation Report: Coding-Agent Harness

> **Generated at**: 2026-10-14 10:35:13 UTC  
> **Backend**: Pollinations OpenAI-compatible endpoint (`https://text.pollinations.ai/openai`)  
> **Model**: `openai` (zero-shot baseline vs. chain-of-thought)  
> **Evaluation Dataset**: 15 self-contained LeetCode-style DSA problems across Arrays, Strings, Two Pointers, Stacks, and Hashmaps.  

## 1. Executive Summary & Comparative Metrics

| Metric | Baseline (Direct Code) | CoT (Think Step-by-Step) | Delta (CoT vs Baseline) |
| :--- | :---: | :---: | :---: |
| **Pass@1 Rate** | **100.0%** (15/15) | **100.0%** (15/15) | **+0.0%** |
| **Avg Tokens / Problem** | 670.4 | 1185.73 | +515.3 |
| **p50 Latency (Median)** | 8.319s | 18.475s | +10.156s |
| **Latency Range (Min - Max)** | 6.91s - 56.752s | 11.389s - 33.04s | — |
| **Avg Prompt Tokens** | 436.13 | 450.13 | +14.0 |
| **Avg Completion Tokens** | 234.27 | 735.6 | +501.3 |

## 2. Failure Taxonomy Breakdown

All failures are graded inside an isolated Python subprocess with a strict 5.0-second execution timeout.

| Failure Category | Baseline Count | CoT Count | Description |
| :--- | :---: | :---: | :--- |
| `syntax_error` | 0 | 0 | Code failed Python AST compilation |
| `runtime_error` | 0 | 0 | Unhandled exception during test execution |
| `wrong_answer` | 0 | 0 | Output did not match expected hidden test case |
| `timeout` | 0 | 0 | Exceeded 5.0s subprocess timeout limit |
| `no_code` | 0 | 0 | Failed to parse valid fenced python block |

## 3. Problem-by-Problem Results Matrix

| # | Problem | Difficulty | Topic | Baseline Pass | Baseline Latency | CoT Pass | CoT Latency |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| 01 | Two Sum | Easy | array | PASS | 6.91s | PASS | 33.04s |
| 02 | Valid Parentheses | Easy | stack | PASS | 7.94s | PASS | 12.94s |
| 03 | Best Time to Buy and Sell Stock | Easy | array | PASS | 7.96s | PASS | 16.88s |
| 04 | Valid Anagram | Easy | string | PASS | 8.30s | PASS | 11.39s |
| 05 | Valid Palindrome | Easy | two-pointer | PASS | 8.53s | PASS | 18.48s |
| 06 | Maximum Subarray | Medium | array | PASS | 8.32s | PASS | 22.24s |
| 07 | Merge Intervals | Medium | array | PASS | 10.40s | PASS | 19.76s |
| 08 | Product of Array Except Self | Medium | array | PASS | 25.19s | PASS | 24.00s |
| 09 | Longest Consecutive Sequence | Medium | hashmap | PASS | 9.06s | PASS | 30.64s |
| 10 | Subarray Sum Equals K | Medium | hashmap | PASS | 56.75s | PASS | 16.39s |
| 11 | Container With Most Water | Medium | two-pointer | PASS | 7.98s | PASS | 19.71s |
| 12 | Trapping Rain Water | Hard | two-pointer | PASS | 8.93s | PASS | 17.71s |
| 13 | Longest Substring Without Repeating Characters | Medium | string | PASS | 7.76s | PASS | 12.19s |
| 14 | Evaluate Reverse Polish Notation | Medium | stack | PASS | 10.83s | PASS | 18.46s |
| 15 | Daily Temperatures | Medium | stack | PASS | 8.24s | PASS | 21.21s |

## 4. Methodology & Evaluation Setup

1. **Zero-Invention Guarantee**: All metrics above were measured by real HTTP calls to the Pollinations OpenAI-compatible endpoint.
2. **Subprocess Isolation**: Every extracted code snippet was compiled and executed against hidden test batches in a separate sandboxed Python process.
3. **Mock-Gated Unit Tests**: All unit tests in `tests/` run in isolation using `MockLLM` with zero network dependency.
4. **One-Command Repro**: Re-running the entire benchmark and regenerating this report can be triggered via `make eval` or `python3 run_eval.py`.
