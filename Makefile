PYTHON ?= python3

.PHONY: install format lint test check precommit-install precommit-run run

install:
	$(PYTHON) -m pip install -e ".[dev]"

format:
	ruff format .

precommit-install:
	pre-commit install

precommit-run:
	pre-commit run --all-files

check: lint test

test:
	PYTHONPATH=src pytest

run:
	PYTHONPATH=src $(PYTHON) -m opendove.main

lint:
	ruff check .
