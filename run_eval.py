#!/usr/bin/env python3
"""CLI runner for evaluating coding agents on 15 DSA problems using real Pollinations LLM."""

import argparse
import json
from pathlib import Path
import sys
import time

from src.harness import run_eval
from src.llm import PollinationsLLM
from src.report import (
    compute_metrics,
    export_csv,
    export_json,
    generate_markdown_report,
)


def probe_endpoint(llm_client: PollinationsLLM, max_probe_retries: int = 3) -> bool:
    """Probe the Pollinations endpoint before starting the eval run."""
    print("Probing Pollinations OpenAI-compatible endpoint...")
    for attempt in range(1, max_probe_retries + 1):
        try:
            resp = llm_client.complete("Respond with 'PONG'", seed=42)
            if resp and resp.content:
                print(f"Endpoint responsive (probe latency: {resp.latency_seconds:.2f}s). Ready to run benchmark.\n")
                return True
        except Exception as e:
            print(f"Probe attempt {attempt}/{max_probe_retries} failed: {e}")
            if attempt < max_probe_retries:
                sleep_time = 2 ** attempt
                print(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

    return False


def load_problems(problems_dir: Path) -> list:
    problem_files = sorted(list(problems_dir.glob("*.json")))
    problems = []
    for pf in problem_files:
        with open(pf, "r", encoding="utf-8") as f:
            problems.append(json.load(f))
    return problems


def run_strategy_benchmark(
    problems: list,
    strategy: str,
    llm_client: PollinationsLLM,
) -> list:
    print(f"{'='*60}")
    print(f"Running Strategy: {strategy.upper()} ({len(problems)} problems)")
    print(f"{'='*60}")

    results = []
    for idx, prob in enumerate(problems, 1):
        pid = prob["id"]
        title = prob.get("title", pid)
        diff = prob.get("difficulty", "Medium")

        print(f"[{idx:02d}/{len(problems):02d}] {title:<35} ({diff:<6}) ... ", end="", flush=True)

        try:
            eval_res = run_eval(prob, strategy=strategy, llm_client=llm_client)
            results.append(eval_res)

            status_str = "PASS" if eval_res["passed"] else f"FAIL ({eval_res['failure_category']})"
            print(
                f"{status_str:<18} [Latency: {eval_res['latency_seconds']:.2f}s, Tokens: {eval_res['tokens_used']}]"
            )
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "problem_id": pid,
                "problem_title": title,
                "difficulty": diff,
                "topic": prob.get("topic", "General"),
                "strategy": strategy,
                "passed": False,
                "failure_category": "runtime_error",
                "latency_seconds": 0.0,
                "tokens_used": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "extracted_code": None,
                "raw_response": None,
                "error_message": str(e),
                "test_outcomes": [],
            })

    return results


def main():
    parser = argparse.ArgumentParser(description="Coding Agent Harness Benchmark")
    parser.add_argument("--problems-dir", type=Path, default=Path("problems"), help="Path to problems directory")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Path to save raw results")
    parser.add_argument("--report-file", type=Path, default=Path("report.md"), help="Path to save report.md")
    parser.add_argument("--csv-file", type=Path, default=None, help="Path to save results.csv")
    args = parser.parse_args()

    args.results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = args.csv_file or (args.results_dir / "results.csv")

    llm_client = PollinationsLLM(
        endpoint="https://text.pollinations.ai/openai",
        model="openai",
        max_retries=3,
        backoff_factor=2.0,
        timeout=60,
    )

    # Milestone 1: Probe endpoint
    if not probe_endpoint(llm_client):
        print("\nFATAL: Pollinations endpoint is down after multiple attempts.")
        print("Evaluation stopped to adhere to zero-invention rule. Check network connection or endpoint health.")
        sys.exit(1)

    problems = load_problems(args.problems_dir)
    if not problems:
        print(f"Error: No problem JSON files found in {args.problems_dir}")
        sys.exit(1)

    print(f"Loaded {len(problems)} DSA problems.")

    # Run Baseline
    baseline_results = run_strategy_benchmark(problems, strategy="baseline", llm_client=llm_client)
    export_json(baseline_results, args.results_dir / "baseline_results.json")

    # Run CoT
    cot_results = run_strategy_benchmark(problems, strategy="cot", llm_client=llm_client)
    export_json(cot_results, args.results_dir / "cot_results.json")

    # Aggregate metrics
    baseline_metrics = compute_metrics(baseline_results)
    cot_metrics = compute_metrics(cot_results)

    # Save combined CSV
    all_results = baseline_results + cot_results
    export_csv(all_results, csv_file)
    print(f"\nSaved CSV results to {csv_file}")

    # Generate Markdown report
    generate_markdown_report(
        baseline_metrics=baseline_metrics,
        cot_metrics=cot_metrics,
        baseline_results=baseline_results,
        cot_results=cot_results,
        filepath=args.report_file,
    )
    print(f"Generated report at {args.report_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"Baseline Pass@1: {baseline_metrics['pass_at_1_pct']} ({baseline_metrics['passed_count']}/{baseline_metrics['total_problems']})")
    print(f"Baseline Avg Tokens: {baseline_metrics['avg_tokens']}, Median Latency: {baseline_metrics['p50_latency']}s")
    print(f"CoT Pass@1:      {cot_metrics['pass_at_1_pct']} ({cot_metrics['passed_count']}/{cot_metrics['total_problems']})")
    print(f"CoT Avg Tokens:      {cot_metrics['avg_tokens']}, Median Latency: {cot_metrics['p50_latency']}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
