# Recursive R&D Foundry -- runs COLD: the evidence kernel is vendored under
# vendor/fek, so `make test && make demo && make audit` need no external repo,
# no PAT, and no network. The demo IS the falsification run.
PY ?= python3
export PYTHONPATH := src:vendor

.DEFAULT_GOAL := help
.PHONY: help demo falsify test audit verify clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

demo: ## run the loop; exits non-zero if any falsification condition trips
	$(PY) -m foundry

falsify: demo ## alias: the demo is the falsification attempt

test: ## run the falsification suite (vendored kernel; no external deps)
	$(PY) -m pytest

audit: ## run the vendored kernel's overclaim scanner on this repo's prose
	$(PY) -m fek --root . scan-overclaims

verify: test demo audit ## the full cold-reproducible gate
	@echo "verify: OK (test + demo + audit, all cold)"

clean: ## remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache *.egg-info src/*.egg-info
