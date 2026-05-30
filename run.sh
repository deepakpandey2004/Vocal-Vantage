#!/usr/bin/env bash
# Convenience dev launcher
set -e
export $(grep -v '^#' .env 2>/dev/null | xargs) 2>/dev/null || true
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
