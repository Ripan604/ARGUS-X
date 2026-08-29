#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/frontend"
npm run dev -- --host 127.0.0.1 --port 5173
