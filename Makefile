# Recursive R&D Foundry -- the demo IS the falsification run.
PY ?= python3
# Use a sibling fractal-evidence-kernel checkout when present (dev/CI layout);
# otherwise rely on an installed package.
FEK_SIBLING := $(abspath ../fractal-evidence-kernel/src)
export PYTHONPATH := src:$(if $(wildcard $(FEK_SIBLING)),$(FEK_SIBLING),)

.DEFAULT_GOAL := help
.PHONY: help demo falsify test audit clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

demo: ## run the loop; exits non-zero if any falsification condition trips
	$(PY) -m foundry

falsify: demo ## alias: the demo is the falsification attempt

test: ## run the falsification suite
	$(PY) -m pytest

audit: ## run fractal-evidence-kernel's overclaim scanner on this repo's prose
	$(PY) -m fek --root . scan-overclaims

clean: ## remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache *.egg-info src/*.egg-info
