import csv
import json
import pytest
from pathlib import Path

from src.report import (
    compute_metrics,
    export_csv,
    export_json,
    generate_markdown_report,
)


SAMPLE_RESULTS = [
    {
        "problem_id": "p1",
        "problem_title": "Problem 1",
        "difficulty": "Easy",
        "topic": "array",
        "strategy": "baseline",
        "passed": True,
        "failure_category": None,
        "latency_seconds": 1.5,
        "tokens_used": 100,
        "prompt_tokens": 60,
        "completion_tokens": 40,
    },
    {
        "problem_id": "p2",
        "problem_title": "Problem 2",
        "difficulty": "Medium",
        "topic": "stack",
        "strategy": "baseline",
        "passed": False,
        "failure_category": "syntax_error",
        "latency_seconds": 2.0,
        "tokens_used": 200,
        "prompt_tokens": 80,
        "completion_tokens": 120,
    },
    {
        "problem_id": "p3",
        "problem_title": "Problem 3",
        "difficulty": "Medium",
        "topic": "hashmap",
        "strategy": "baseline",
        "passed": False,
        "failure_category": "wrong_answer",
        "latency_seconds": 3.0,
        "tokens_used": 150,
        "prompt_tokens": 70,
        "completion_tokens": 80,
    },
    {
        "problem_id": "p4",
        "problem_title": "Problem 4",
        "difficulty": "Hard",
        "topic": "two-pointer",
        "strategy": "baseline",
        "passed": True,
        "failure_category": None,
        "latency_seconds": 2.5,
        "tokens_used": 250,
        "prompt_tokens": 100,
        "completion_tokens": 150,
    },
]


def test_compute_metrics():
    metrics = compute_metrics(SAMPLE_RESULTS)
    assert metrics["total_problems"] == 4
    assert metrics["passed_count"] == 2
    assert metrics["pass_at_1_rate"] == 0.5
    assert metrics["avg_tokens"] == 175.0
    assert metrics["p50_latency"] == 2.25
    assert metrics["failure_categories"]["syntax_error"] == 1
    assert metrics["failure_categories"]["wrong_answer"] == 1
    assert metrics["failure_categories"]["runtime_error"] == 0
    assert metrics["failure_categories"]["timeout"] == 0
    assert metrics["failure_categories"]["no_code"] == 0


def test_compute_metrics_empty():
    metrics = compute_metrics([])
    assert metrics["total_problems"] == 0
    assert metrics["pass_at_1_rate"] == 0.0
    assert metrics["avg_tokens"] == 0.0
    assert metrics["p50_latency"] == 0.0


def test_export_csv(tmp_path: Path):
    csv_file = tmp_path / "results.csv"
    export_csv(SAMPLE_RESULTS, csv_file)

    assert csv_file.exists()
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 4
        assert reader[0]["problem_id"] == "p1"
        assert reader[0]["passed"] == "True"
        assert reader[1]["failure_category"] == "syntax_error"


def test_export_json(tmp_path: Path):
    json_file = tmp_path / "results.json"
    export_json(SAMPLE_RESULTS, json_file)

    assert json_file.exists()
    with open(json_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert len(loaded) == 4
        assert loaded[0]["problem_id"] == "p1"


def test_generate_markdown_report(tmp_path: Path):
    baseline_metrics = compute_metrics(SAMPLE_RESULTS)
    cot_metrics = compute_metrics(SAMPLE_RESULTS)
    report_file = tmp_path / "report.md"

    md = generate_markdown_report(
        baseline_metrics=baseline_metrics,
        cot_metrics=cot_metrics,
        baseline_results=SAMPLE_RESULTS,
        cot_results=SAMPLE_RESULTS,
        filepath=report_file,
    )

    assert report_file.exists()
    assert "# Evaluation Report: Coding-Agent Harness" in md
    assert "Pass@1" in md
    assert "p50 Latency" in md
    assert "syntax_error" in md
