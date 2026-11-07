#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
uv sync --frozen --python 3.11
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
.venv/bin/python cli.py --help >/dev/null
