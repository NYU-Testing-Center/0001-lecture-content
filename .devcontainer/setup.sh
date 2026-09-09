#!/usr/bin/env bash
# One-time container setup: install the lecture runtime and make sure RISE
# cannot be broken by a conflicting JupyterLab extension.
#
# Runs as postCreateCommand, so students never type a pip command.

set -euo pipefail
cd "$(dirname "$0")/.."

# Install system-wide, not with --user.
#
# A --user install looks like it works but silently breaks RISE: pip drops
# jupyterlab_rise's server-extension config into ~/.local/etc/jupyter, which
# Jupyter does not scan (it reads ~/.jupyter and /usr/local/etc/jupyter). The
# extension then never registers, there is no /rise endpoint, and the slideshow
# cannot load. Installing as root puts the config in /usr/local/etc/jupyter and
# the entry points in /usr/local/bin, both already on the default path.
if ! command -v sudo >/dev/null 2>&1; then
  echo "ERROR: sudo not available; cannot install system-wide." >&2
  echo "       Run 'python -m pip install -r requirements.txt' as root." >&2
  exit 1
fi

echo "==> Installing lecture runtime"
sudo python -m pip install --quiet --upgrade pip
sudo python -m pip install --quiet -r requirements.txt

# ---------------------------------------------------------------------------
# Defensive guard.
#
# A clean image has none of these, so this file is a no-op there. It matters if
# the base image ever starts shipping them (or someone pip-installs ipywidgets
# or panel later): RISE's bundle does not provide the `@jupyterlab/console`
# shared module these extensions require, they throw during widget creation, and
# the slideshow renders as a blank white page with no visible error.
#
# Disabling them only affects JupyterLab's frontend. The Python packages keep
# working; you just cannot render an interactive widget onto a RISE slide, which
# RISE cannot do in any case.
# ---------------------------------------------------------------------------
echo "==> Writing RISE compatibility guard"
LABCONFIG="${HOME}/.jupyter/labconfig"
mkdir -p "$LABCONFIG"
cat > "${LABCONFIG}/page_config.json" <<'JSON'
{
  "disabledExtensions": {
    "@jupyter-widgets/jupyterlab-manager": true,
    "@pyviz/jupyterlab_pyviz": true,
    "@lckr/jupyterlab_variableinspector": true,
    "jupyterlab-plotly": true
  }
}
JSON

# ---------------------------------------------------------------------------
# Course-specific services go here.
#
# If a lecture needs a database server (MongoDB, Postgres, Neo4j ...), install
# it in this block and start it from start-jupyter.sh, with the connection
# string exported through `remoteEnv` in devcontainer.json so the lecture's own
# code can read it from the environment.
#
# A worked MongoDB example -- apt repository, key handling, the arm64 caveat and
# the `apt-get update` trap in this base image -- is in
# porting-kit/docs/4-present-and-share.md under "Adding a database service".
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Presenting shortcut: Shift+Enter should run a cell without advancing the
# slide. See the header of the settings file for the reasoning.
# ---------------------------------------------------------------------------
echo "==> Installing presentation keyboard shortcuts"
SHORTCUTS="${HOME}/.jupyter/lab/user-settings/@jupyterlab/shortcuts-extension"
mkdir -p "$SHORTCUTS"
cp tools/rise-shortcuts.jupyterlab-settings \
   "${SHORTCUTS}/shortcuts.jupyterlab-settings"

# ---------------------------------------------------------------------------
# Suppress JupyterLab's first-run prompts.
#
# On a fresh profile JupyterLab asks "Would you like to get notified about
# official Jupyter news?" and can offer version-update notices. A student's
# first action after clicking the link should be opening a lecture, not
# dismissing a dialog they have no context for. `fetchNews` defaults to "none",
# which is what makes it ask; "false" answers it once, for everyone.
# ---------------------------------------------------------------------------
echo "==> Suppressing JupyterLab first-run prompts"
NOTIF="${HOME}/.jupyter/lab/user-settings/@jupyterlab/apputils-extension"
mkdir -p "$NOTIF"
cat > "${NOTIF}/notification.jupyterlab-settings" <<'JSON'
{
  "fetchNews": "false",
  "checkForUpdates": false
}
JSON

# ---------------------------------------------------------------------------
# Smoke check: fail loudly now rather than mid-lecture.
# ---------------------------------------------------------------------------
echo "==> Verifying install"
python - <<'PY'
import sys, importlib.util
# Keep this list in step with requirements.txt: it is what turns a missing
# lecture dependency into a failure at container-build time rather than a
# traceback in front of a class. CS 1's lectures import only the standard
# library, so the third-party half of this list is just the presentation stack;
# the stdlib names are here because a broken interpreter should fail here too.
missing = [m for m in
           ("jupyterlab", "jupyterlab_rise",
            "random", "time", "math", "string", "urllib", "csv")
           if not importlib.util.find_spec(m)]
if missing:
    sys.exit(f"FAIL: missing modules: {', '.join(missing)}")
print("    python modules OK")
PY

# `jupyter labextension list` colourises its output, so strip ANSI escapes
# before matching or the greps silently never hit.
LABEXT="$(jupyter labextension list 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"

for ext in jupyterlab-rise dma-rise-run-button; do  # bundle name is cosmetic; see docs
  if echo "$LABEXT" | grep -q "${ext} v.* enabled OK"; then
    echo "    ${ext} labextension OK"
  else
    echo "    WARNING: ${ext} labextension not reported enabled:"
    echo "$LABEXT" | sed 's/^/      /'
  fi
done

if jupyter server extension list 2>&1 | grep -q "jupyterlab_rise.*OK"; then
  echo "    jupyterlab_rise server extension OK"
else
  echo "    WARNING: jupyterlab_rise server extension not reported OK"
fi

echo
echo "Setup complete. JupyterLab starts automatically; see the terminal for its URL."
