# PLAN — agent-harness-eval (AlgoUniversity proof-of-work)

**Purpose:** Coding-agent harness eval for AlgoUniversity ("Show us not tell").
Benchmark 2 coding-agent prompt strategies on a 15-problem DSA set:
pass@1, avg tokens/problem, p50 latency, failure taxonomy. Reproducible eval report
(markdown + CSV) from REAL LLM runs. New public repo: `Shashank-VK/agent-harness-eval`.

## Scope gate
- IN: 15 public DSA problems (fixed prompts), 2 runs (baseline prompt strategy vs one
  changed variable: chain-of-thought style prompt), 4 metrics (pass@1, avg tokens/problem,
  p50 latency, failure categories), repro script, markdown + CSV eval report.
- OUT: new eval framework, frontend, training anything, model fine-tuning.
- LLM backend: FREE Pollinations OpenAI-compatible endpoint
  `https://text.pollinations.ai/openai` (no key needed). Real API calls in the runs;
  tests use a deterministic mock-gated backend only (no network in CI).

## Milestones (uphill first)
1. **Probe the Pollinations endpoint** — verify `https://text.pollinations.ai/openai`
   responds to a chat-completions call, tokens estimate works. If dead, root-cause
   (retry/timeout), then escalate; no invented numbers ever.
2. **Problem set** — 15 classic DSA problems (array/string/hashmap/stack/two-pointer,
   easy–medium), each with: problem statement, function signature, deterministic
   hidden test cases, difficulty tag. Must be fully specified so pass@1 is judgeable.
3. **Harness core (TDD)** — runner that for each problem calls the LLM, extracts code,
   executes in a sandboxed subprocess with timeout, grades against tests, records
   tokens (from response usage if present; else estimate via word heuristic — documented)
   and latency. Two prompt strategies: baseline (plain "write the solution") vs
   CoT-style ("think step by step, then write the solution").
4. **Metrics + report** — pass@1, avg tokens/problem, p50 latency, failure taxonomy
   (syntax error, runtime error, wrong answer, timeout, empty/parse failure).
   Output `report.md` and `results.csv` + raw per-run JSON.
5. **Real runs** — run the full 15-problem set with BOTH strategies against
   Pollinations, all numbers real. Save run logs with timestamps.
6. **One-command repro** — `make eval` (or `./run.sh`) that reruns everything and
   regenerates the report from a clean checkout. Determinism documented:
   LLM outputs vary run to run; repro re-measures, not replays.
7. **README + tests green + push** — README: what it does, how to run, test count,
   how metrics are measured. `pytest` fully green with count recorded.

## Verify gates (Phase 4)
- [ ] pytest fully green, count recorded
- [ ] Both runs complete with real measured numbers in report.md + results.csv
- [ ] One-command repro works from a clean checkout
- [ ] Pushed to GitHub Shashank-VK/agent-harness-eval, `gh repo view` confirms live
- [ ] README documents what/how-to-run/test count
- [ ] No secrets, no invented metrics (anti-invention checklist from spec)

## Files
- `problems/` — 15 problem JSON files (statement, signature, tests)
- `src/harness.py` — runner, grader, metrics
- `src/llm.py` — Pollinations OpenAI-compatible client (+ MockLLM for tests)
- `tests/` — TDD suite (mock-gated)
- `run_eval.py` / `Makefile` — one-command repro
- `report.md`, `results.csv` — real-run outputs
