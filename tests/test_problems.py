import json
from pathlib import Path
import re

PROBLEMS_DIR = Path(__file__).resolve().parent.parent / "problems"


def get_problem_files():
    return sorted(list(PROBLEMS_DIR.glob("*.json")))


def test_problem_files_count():
    files = get_problem_files()
    assert len(files) == 15, f"Expected 15 problem files, found {len(files)}"


def test_problem_schema_and_validity():
    files = get_problem_files()
    assert len(files) == 15, "Cannot validate schema if 15 files are not present"

    seen_ids = set()
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        # Check required fields
        for field in ["id", "title", "difficulty", "topic", "statement", "function_name", "function_signature", "hidden_tests"]:
            assert field in data, f"{f.name} missing field '{field}'"
            assert data[field], f"{f.name} field '{field}' is empty"

        assert data["id"] not in seen_ids, f"Duplicate problem id: {data['id']}"
        seen_ids.add(data["id"])

        assert data["difficulty"] in ["Easy", "Medium", "Hard"], f"Invalid difficulty in {f.name}: {data['difficulty']}"

        # function_name must be valid Python identifier
        assert re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", data["function_name"]), f"Invalid function_name in {f.name}"

        # function_signature must define function_name
        assert f"def {data['function_name']}(" in data["function_signature"], f"Signature in {f.name} must declare def {data['function_name']}("

        # hidden_tests must be a list with at least 4 test cases
        tests = data["hidden_tests"]
        assert isinstance(tests, list), f"hidden_tests in {f.name} must be a list"
        assert len(tests) >= 4, f"hidden_tests in {f.name} must have at least 4 cases, found {len(tests)}"

        for idx, t in enumerate(tests):
            assert "input" in t, f"Test #{idx} in {f.name} missing 'input'"
            assert isinstance(t["input"], dict), f"Test #{idx} in {f.name} 'input' must be a dict"
            assert "expected" in t, f"Test #{idx} in {f.name} missing 'expected'"
