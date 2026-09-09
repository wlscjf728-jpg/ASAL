SHELL := /usr/bin/env bash
PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
ROOT := $(CURDIR)
ATTACK8 := $(ROOT)/experiments/anonymous_subround_multiround_attack_8_oracle
DISCOVERY := $(ROOT)/experiments/anonymous_subround_multiround_attack_Leakage_Channel_Discovery
KEYDIVERSITY := $(ROOT)/experiments/anonymous_subround_multiround_attack_key_diversity
PHASEALPHA := $(ROOT)/experiments/anonymous_subround_multiround_attack_phase_alpha
GATE := $(ROOT)/experiments/extra_exp1
DFT := $(ROOT)/experiments/RTL1_DFT_RESTUDY

.PHONY: help install smoke one-bit-96-dry-run one-bit-96 discovery-smoke key-diversity-smoke tracking gate-smoke dft-prepare dft-run audit git-status

help:
	@echo "make evidence-verify (review evidence without EDA tools)"
	@echo "make one-bit-384-dry-run | one-bit-384 | one-bit-384-verify"
	@echo "make install | smoke | one-bit-96-dry-run | one-bit-96"
	@echo "make discovery-smoke | key-diversity-smoke | tracking | gate-smoke"
	@echo "make dft-prepare | dft-run | audit"

install:
	$(PIP) install -r requirements.txt

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
	@git -C "$(ROOT)" status --short
