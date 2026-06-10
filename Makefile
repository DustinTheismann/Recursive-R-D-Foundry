# Recursive R&D Foundry v0.2 -- governed successor evolution.
# Runs COLD: the evidence kernel is vendored under vendor/fek, so `make verify`
# needs no external repo, no token, and no network.
PY ?= python3
export PYTHONPATH := .:vendor

.DEFAULT_GOAL := help
.PHONY: help test demo demo-gate audit verify clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

test: ## full suite: internal gates + FEK falsification + ported gate-demo (cold)
	$(PY) -m pytest

demo: ## governed orchestrator run; asserts the gate BOTH opens and shuts
	$(PY) scripts/governed_demo.py

demo-gate: ## deterministic gate demonstration (honest->PROMOTED, goodhart->REFUTED)
	$(PY) -m gate_demo

audit: ## run the vendored kernel's overclaim scanner on this repo's prose
	$(PY) -m fek --root . scan-overclaims

verify: test demo demo-gate audit ## full cold gate: both halves witnessed two ways
	@echo "verify: OK (test + governed demo + gate demo + audit, all cold)"

clean: ## remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache *.egg-info
