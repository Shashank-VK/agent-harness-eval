.PHONY: all test eval clean

PYTHON ?= python3
PYTEST ?= ~/.local/bin/pytest

all: test eval

test:
	$(PYTEST) -v

eval:
	$(PYTHON) run_eval.py

clean:
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache
