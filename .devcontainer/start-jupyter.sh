#!/usr/bin/env bash
# Start JupyterLab on attach and print the authenticated URL to click.
# Idempotent because postAttachCommand runs every time the Codespace is opened.

set -euo pipefail
cd "$(dirname "$0")/.."

PORT=8888

if jupyter server list 2>/dev/null | grep -q ":${PORT}/"; then
  echo "JupyterLab already running:"
else
  mkdir -p .devcontainer/logs
  nohup jupyter lab \
    --no-browser \
    --ip=0.0.0.0 \
    --port="${PORT}" \
    --ServerApp.root_dir="$(pwd)" \
    > .devcontainer/logs/jupyterlab.log 2>&1 &

  for _ in $(seq 1 40); do
    if jupyter server list 2>/dev/null | grep -q ":${PORT}/"; then
      break
    fi
    sleep 0.5
  done
fi

URL=$(jupyter server list 2>/dev/null | grep -o "http://[^ ]*:${PORT}/[^ ]*" | head -1 || true)
URL=${URL/0.0.0.0/127.0.0.1}

cat <<BANNER

  ┌──────────────────────────────────────────────────────────────┐
  │  CS0001 lecture decks — JupyterLab + RISE                    │
  └──────────────────────────────────────────────────────────────┘

  Open:  ${URL:-<starting, run .devcontainer/start-jupyter.sh again>}

  Then:  open a notebook under notebooks/cs1, click inside it,
         press Esc, then Alt+R (Option+R on macOS) for RISE.

         Space / →   next slide        ↓        sub-slides
         Shift+Enter run a code cell   Esc, o   slide overview

  Note:  RISE runs in JupyterLab, not in the VS Code notebook editor.
         Editing in VS Code is fine; presenting needs the link above.

BANNER
