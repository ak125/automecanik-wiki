# Makefile for wiki _scripts test suite
#
# Usage:
#   make test          — run pytest on all tests
#   make test-fixtures — run pytest only on fixtures
#   make lint          — basic linting (yamllint, json validation)
#   make all           — test + lint
#
# Reference: plan rev 6 §B.9, ADR-033

PYTHON := python3
PYTEST := $(PYTHON) -m pytest
SCRIPTS_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
WIKI_ROOT := $(realpath $(SCRIPTS_DIR)/../..)

.PHONY: all test test-fixtures lint clean help

all: test lint

test:
	cd $(SCRIPTS_DIR) && $(PYTEST) -v

test-fixtures:
	cd $(SCRIPTS_DIR) && $(PYTEST) -v -k "fixture or test_fixture_gate"

lint:
	@echo "Validating JSON schemas..."
	$(PYTHON) -c "import json; json.load(open('$(WIKI_ROOT)/_meta/schema/frontmatter.schema.json'))"
	$(PYTHON) -c "import json; json.load(open('$(WIKI_ROOT)/_meta/schema/entity-data/gamme.schema.json'))"
	@echo "Validating source-catalog YAML..."
	$(PYTHON) -c "import yaml; yaml.safe_load(open('$(WIKI_ROOT)/_meta/source-catalog.yaml'))"

clean:
	find $(SCRIPTS_DIR) -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find $(SCRIPTS_DIR) -name "*.pyc" -delete 2>/dev/null || true

help:
	@echo "Targets:"
	@echo "  test          — run pytest on all tests"
	@echo "  test-fixtures — run pytest only on fixtures"
	@echo "  lint          — validate JSON schemas + YAML"
	@echo "  all           — test + lint"
	@echo "  clean         — remove __pycache__"
