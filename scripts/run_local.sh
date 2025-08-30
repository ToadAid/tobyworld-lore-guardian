#!/usr/bin/env bash
set -e
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn pydantic-settings pytest httpx
uvicorn tobyworld.api.server:app --reload --port 8080
