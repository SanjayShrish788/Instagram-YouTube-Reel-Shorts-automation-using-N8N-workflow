#!/usr/bin/env sh
set -eu

export PYTHONPATH=/opt/service

python scripts/init_data.py
python scripts/seed_data.py

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
