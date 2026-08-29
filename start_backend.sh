#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python backend/run_backend.py
