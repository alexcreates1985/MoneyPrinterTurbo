#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p storage/codespaces
webui_host=127.0.0.1
# Codespaces port forwarding is private by default. Fail closed if we cannot
# explicitly enforce private visibility on this Codespace's forwarded UI port.
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  gh codespace ports visibility 8501:private -c "$CODESPACE_NAME"
  webui_host=0.0.0.0
fi
export MPT_REQUIRE_PUBLISH_APPROVAL=1
# Reuse our healthy service on repeated starts; never kill unrelated processes.
if [[ -f storage/codespaces/webui.pid ]] && kill -0 "$(cat storage/codespaces/webui.pid)" 2>/dev/null; then
  curl -fsS --max-time 5 http://127.0.0.1:8501/_stcore/health >/dev/null
  exit 0
fi
if curl -fsS --max-time 2 http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
  echo 'Port 8501 already serves an app; inspect it before starting another instance.' >&2
  exit 1
fi
nohup .venv/bin/python -m streamlit run webui/Main.py \
  --server.address="${MPT_WEBUI_HOST:-$webui_host}" --server.port=8501 --server.headless=true \
  --browser.gatherUsageStats=false --server.enableCORS=true \
  --server.enableXsrfProtection=true >storage/codespaces/webui.log 2>&1 </dev/null &
echo $! >storage/codespaces/webui.pid
for attempt in {1..30}; do
  if curl -fsS --max-time 2 http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    [[ ! -f config.toml ]] || chmod 600 config.toml
    echo 'WebUI started. Open Private port 8501 in the Codespaces Ports panel.'
    exit 0
  fi
  kill -0 "$(cat storage/codespaces/webui.pid)" 2>/dev/null || break
  sleep 1
done
echo 'WebUI did not become healthy. Inspect storage/codespaces/webui.log.' >&2
exit 1
