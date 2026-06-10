# Recursive R&D Foundry v0.2 -- governed successor evolution.
# Runs COLD: the evidence kernel is vendored under vendor/fek, so `make verify`
# needs no external repo, no token, and no network.
PY ?= python3
export PYTHONPATH := .:vendor

.DEFAULT_GOAL := help
.PHONY: help test demo audit verify clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

test: ## full suite: internal gates + ported FEK falsification suite (cold)
	$(PY) -m pytest

demo: ## run a short governed cycle and print the FEK governance summary
	$(PY) -c "from rsi_foundry.core.orchestrator import Foundry; \
f=Foundry({'cycles':3,'seed':7}); f.run(); s=f.evidence_gate.state(); \
print('claims',len(s['claims']),'refuted',sum(1 for c in s['claims'].values() if c['status']=='refuted'),\
'promoted',sum(1 for c in s['claims'].values() if c['status']=='accepted'),\
'events',sum(s['event_counts'].values()))"

audit: ## run the vendored kernel's overclaim scanner on this repo's prose
	$(PY) -m fek --root . scan-overclaims

verify: test demo audit ## the full cold-reproducible gate
	@echo "verify: OK (test + demo + audit, all cold)"

clean: ## remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache *.egg-info
