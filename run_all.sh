#!/usr/bin/env bash
# One-shot rebuild: fetch (network) -> calc (cache only) -> render (HTML only).
set -euo pipefail; cd "$(dirname "$0")"; PY=.venv/bin/python; $PY fetch.py && $PY calc.py && $PY render.py
