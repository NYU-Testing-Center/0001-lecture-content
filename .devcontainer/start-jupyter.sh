#!/usr/bin/env bash
# Start JupyterLab and print the URL to click. Optionally deep-link a lecture:
#
#   bash .devcontainer/start-jupyter.sh          # link to the file browser
#   bash .devcontainer/start-jupyter.sh 29       # link straight to lecture 29
#   bash .devcontainer/start-jupyter.sh notebooks/lecture-29-....ipynb
#
# Idempotent: postAttachCommand runs every time you connect to the codespace, so
# this reuses an already-running server instead of starting a second one.
#
# Token authentication is left ON deliberately. Codespaces forwarded ports are
# private to you by default, but a port's visibility can be changed to public --
# and a token-less Jupyter server on a public port is remote code execution for
# anyone with the URL. The token costs one click and removes that risk.

set -euo pipefail
cd "$(dirname "$0")/.."

PORT=8888

# ---------------------------------------------------------------------------
# In a codespace the server sits behind GitHub's port-forwarding proxy, which
# terminates TLS and rewrites the Host header. Two things follow:
#
#   * The browser's origin is https://<name>-8888.app.github.dev, not the
#     loopback address the server is bound to. Jupyter rejects websocket
#     upgrades from an origin it does not recognise, and a rejected websocket
#     is a notebook whose kernel never connects -- it opens and then does
#     nothing. `allow_origin_pat` tells it to accept that origin. It is a
#     pattern for the forwarding domain rather than `*` so the allowance stops
#     at GitHub's proxy instead of trusting every site on the internet.
#   * `trust_xheaders` makes it honour X-Forwarded-Proto, so it builds `wss://`
#     URLs behind the https proxy instead of `ws://`.
#
# Neither is wanted outside a codespace, so both are conditional.
# ---------------------------------------------------------------------------
PROXY_ARGS=()
if [ -n "${CODESPACE_NAME:-}" ]; then
  FWD_DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  PROXY_ARGS=(
    --ServerApp.allow_origin_pat="https://.*\.${FWD_DOMAIN//./\\.}"
    --ServerApp.trust_xheaders=True
  )
fi

# ---------------------------------------------------------------------------
# Start any course-specific service here (a database server, say) before
# JupyterLab, guarded by `command -v` so a machine without it still works.
# See porting-kit/docs/4-present-and-share.md, "Adding a database service".
# ---------------------------------------------------------------------------

if jupyter server list 2>/dev/null | grep -q ":${PORT}/"; then
  echo "JupyterLab already running:"
else
  mkdir -p .devcontainer/logs
  nohup jupyter lab \
    --no-browser \
    --ip=0.0.0.0 \
    --port="${PORT}" \
    --ServerApp.root_dir="$(pwd)" \
    "${PROXY_ARGS[@]+"${PROXY_ARGS[@]}"}" \
    > .devcontainer/logs/jupyterlab.log 2>&1 &

  # Wait for the server to register itself.
  for _ in $(seq 1 40); do
    if jupyter server list 2>/dev/null | grep -q ":${PORT}/"; then break; fi
    sleep 0.5
  done
fi

TOKEN=$(jupyter server list 2>/dev/null \
        | grep -o "http://[^ ]*:${PORT}/[^ ]*token=[A-Za-z0-9]*" \
        | head -1 | sed -n 's/.*token=//p' || true)

# ---------------------------------------------------------------------------
# Resolve the optional lecture argument to a path under notebooks/, so the link
# can open the lecture itself instead of dropping you in the file browser.
# ---------------------------------------------------------------------------
NB_PATH=""
if [ $# -gt 0 ]; then
  if [ -f "$1" ]; then
    NB_PATH="$1"
  else
    NUM=$(printf "%02d" "$1" 2>/dev/null || echo "$1")
    NB_PATH=$(ls notebooks/lecture-"${NUM}"-*.ipynb 2>/dev/null | head -1 || true)
    # Fall back to a nested layout (notebooks/<course>/lecture-NN-*.ipynb), which
    # is how a repo that hosts more than one course tends to be arranged. Only
    # consulted when the flat path finds nothing, so it cannot change behaviour
    # for a normal single-course checkout.
    if [ -z "$NB_PATH" ]; then
      NB_PATH=$(ls notebooks/*/lecture-"${NUM}"-*.ipynb 2>/dev/null | head -1 || true)
    fi
    if [ -z "$NB_PATH" ]; then
      echo "No lecture matching '$1'; linking to the file browser instead." >&2
    fi
  fi
fi

# `/lab/tree/<path>` is JupyterLab's URL for "open this file"; bare `/lab` opens
# the launcher. Paths are relative to --ServerApp.root_dir, set to the repo above.
LAB_PATH="/lab"
[ -n "$NB_PATH" ] && LAB_PATH="/lab/tree/${NB_PATH}"

# ---------------------------------------------------------------------------
# Build the URL to click.
#
# `jupyter server list` reports the address the server is BOUND to (0.0.0.0),
# which is meaningless to a browser. Inside a codespace the address that works
# is the forwarded one GitHub publishes -- printing the loopback URL instead is
# what produced a dead link: VS Code auto-forwards it, but the rewrite drops the
# `?token=` query, so the browser lands on a login prompt rather than the
# lecture. Construct the forwarded URL from the variables Codespaces sets.
# ---------------------------------------------------------------------------
if [ -n "${CODESPACE_NAME:-}" ]; then
  HOSTNAME_FWD="${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  URL="https://${HOSTNAME_FWD}${LAB_PATH}?token=${TOKEN}"
else
  URL="http://127.0.0.1:${PORT}${LAB_PATH}?token=${TOKEN}"
fi
[ -n "$TOKEN" ] || URL=""

if [ -n "$NB_PATH" ]; then
  OPENS="opens $(basename "$NB_PATH")"
else
  OPENS="opens the file browser; pass a lecture number to open one directly"
fi

COURSE=$(python3 -c 'import json;print(json.load(open("course.json"))["short"])' 2>/dev/null || echo "Lecture decks")

cat <<BANNER

  ┌──────────────────────────────────────────────────────────────┐
     ${COURSE} — JupyterLab + RISE
  └──────────────────────────────────────────────────────────────┘

  Open:  ${URL:-<still starting -- run the command again in a few seconds>}

         (${OPENS})

  Then:  press  Alt+R  (Option+R on macOS) to enter the slideshow.

         Space / →   next slide        ↓        sub-slides in a demo
         Shift+Enter run a code cell   Alt+R    leave the slideshow

         Code cells that ask a question with input() work normally: click the
         box, type, press Enter. The waiting cell's Run button turns into a
         red stop button if you want to abandon it.

  Note:  RISE runs in JupyterLab, not in the VS Code notebook editor.
         Editing in VS Code is fine; presenting needs the link above.

BANNER
