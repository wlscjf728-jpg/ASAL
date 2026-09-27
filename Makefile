SHELL := /usr/bin/env bash
PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
ROOT := $(CURDIR)
ATTACK8 := $(ROOT)/experiments/temporal_key_recovery
DISCOVERY := $(ROOT)/experiments/channel_discovery
KEYDIVERSITY := $(ROOT)/experiments/key_diversity
PHASEALPHA := $(ROOT)/experiments/channel_tracking
GATE := $(ROOT)/experiments/gate_topologies
DFT := $(ROOT)/experiments/partial_scan_testability

.PHONY: help install smoke one-bit-96-dry-run one-bit-96 discovery-smoke key-diversity-smoke tracking gate-smoke dft-prepare dft-run audit git-status

help:
	@echo "make check (software, bundled records, dry-runs and bounded startup)"
	@echo "make test | smoke | evidence-verify | audit"
	@echo "make one-bit-startup (bounded real solver startup, not full recovery)"
	@echo "make one-bit-384-dry-run | one-bit-384 | one-bit-384-verify"
	@echo "make install | smoke | one-bit-96-dry-run | one-bit-96"
	@echo "make discovery-smoke | key-diversity-smoke | tracking | gate-smoke"
	@echo "make dft-prepare | dft-run | audit"

install:
	$(PIP) install -r requirements.txt

.PHONY: test one-bit-startup
.PHONY: check
check: test smoke evidence-verify audit one-bit-384-dry-run one-bit-96-dry-run discovery-smoke tracking gate-smoke gate-records-test gate-reference-test dft-prepare one-bit-startup

.PHONY: gate-reference-test gate-records-test
gate-reference-test:
	$(PYTHON) -m pytest -q -rs experiments/gate_reference/tests

gate-records-test:
	$(PYTHON) -m pytest -q experiments/gate_topologies/tests

test:
	$(PYTHON) -m pytest -q tests

one-bit-startup:
	$(PYTHON) scripts/startup_check.py

smoke:
	$(PYTHON) scripts/reproduce.py smoke

one-bit-96-dry-run:
	$(PYTHON) scripts/reproduce.py one-bit-96 --dry-run

one-bit-96:
	$(PYTHON) scripts/reproduce.py one-bit-96

.PHONY: one-bit-384 one-bit-384-dry-run one-bit-384-verify
one-bit-384:
	$(PYTHON) scripts/paper384.py

one-bit-384-dry-run:
	$(PYTHON) scripts/paper384.py --dry-run

one-bit-384-verify:
	$(PYTHON) scripts/paper384.py --verify

discovery-smoke:
	$(PYTHON) scripts/reproduce.py discovery-smoke

key-diversity-smoke:
	$(PYTHON) scripts/reproduce.py key-diversity-smoke

tracking:
	$(PYTHON) scripts/reproduce.py tracking

gate-smoke:
	$(PYTHON) scripts/reproduce.py gate-smoke

dft-prepare:
	$(PYTHON) scripts/reproduce.py dft-prepare

dft-run:
	$(PYTHON) scripts/reproduce.py dft-run

audit:
	$(PYTHON) scripts/audit_repository.py

.PHONY: evidence-verify
evidence-verify:
	$(PYTHON) scripts/evidence.py
	$(PYTHON) scripts/paper384.py --verify

git-status:
	@git status --short
