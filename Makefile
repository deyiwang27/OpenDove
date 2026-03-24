PYTHON ?= python3

.PHONY: install test run lint

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTHONPATH=src pytest

run:
	PYTHONPATH=src $(PYTHON) -m opendove.main

lint:
	ruff check .
