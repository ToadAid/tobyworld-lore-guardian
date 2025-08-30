SHELL := /bin/bash

# ---- paths & config ----
ROOT := $(shell pwd)
VENV ?= ../.venv
PY    := $(VENV)/bin/python
PIP   := $(VENV)/bin/pip
HOST  ?= 0.0.0.0
PORT  ?= 8080

# API prefix: leave empty for /ask ; set to /api for /api/ask if you add a router
API_PREFIX ?=
ASK_PATH := $(API_PREFIX)/ask

export PYTHONPATH := $(ROOT)/src:$(PYTHONPATH)

.PHONY: help venv install install-dev dev health diag ask routes lint format test precommit-install

help:
	@echo "make venv             # create venv at $(VENV)"
	@echo "make install          # pip install -r requirements.txt"
	@echo "make install-dev      # install runtime + dev deps"
	@echo "make dev              # run uvicorn with reload (via ./run.sh)"
	@echo "make health           # curl /health"
	@echo "make diag             # curl /diag"
	@echo "make ask Q='ping?'    # POST $(ASK_PATH)"
	@echo "make routes           # list openapi paths"
	@echo "make lint             # flake8 + isort --check + black --check + mypy"
	@echo "make format           # isort + black (auto-fix)"
	@echo "make test             # pytest -v"
	@echo "make precommit-install# install git pre-commit hooks"

venv:
	test -d $(VENV) || python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
ifneq ("$(wildcard requirements.txt)","")
	$(PIP) install -r requirements.txt
else
	$(PIP) install "fastapi[standard]" "uvicorn[standard]" httpx python-dotenv sentence-transformers faiss-cpu prometheus-client jq || true
endif

install-dev: install
ifneq ("$(wildcard dev-requirements.txt)","")
	$(PIP) install -r dev-requirements.txt
else
	@echo "No dev-requirements.txt found; skipping."
endif

dev:
	HOST=$(HOST) PORT=$(PORT) ./run.sh

health:
	curl -s http://$(HOST):$(PORT)/health | jq .

diag:
	curl -s http://$(HOST):$(PORT)/diag | jq .

ask:
	@test -n "$(Q)" || (echo "Usage: make ask Q='your question'"; exit 1)
	curl -s http://$(HOST):$(PORT)$(ASK_PATH) \
	 -H 'Content-Type: application/json' \
	 -d "$$(jq -nc --arg q "$(Q)" --arg user "make_user" '{user:$$user,question:$q}')" | jq .

routes:
	curl -s http://$(HOST):$(PORT)/openapi.json | jq '.paths'

lint:
	$(VENV)/bin/flake8 src
	$(VENV)/bin/isort --check-only src
	$(VENV)/bin/black --check src
	$(VENV)/bin/mypy src

format:
	$(VENV)/bin/isort src
	$(VENV)/bin/black src

test:
	$(VENV)/bin/pytest -v --maxfail=1 --disable-warnings -q

precommit-install:
	$(PIP) install pre-commit
	$(VENV)/bin/pre-commit install
