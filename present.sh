#!/usr/bin/env bash
# Present a lecture with RISE, on this machine (not in a codespace).
#
#   ./present.sh                  # list the lectures
#   ./present.sh 5                # present lecture 5
#   ./present.sh notebooks/x.ipynb
#
# Why this script exists
# ----------------------
# RISE's standalone app loads every JupyterLab extension it can find, but its
# own bundle does not provide the `@jupyterlab/console` shared module. Anaconda
# environments typically ship extensions that require it -- jupyter-widgets,
# pyviz/panel, plotly, variableinspector -- so those fail to initialise and the
# notebook widget is never created. The slideshow comes up blank.
#
# So we launch RISE with an isolated JUPYTER_CONFIG_DIR that disables just those
# extensions. Your normal `jupyter lab` setup is untouched: ipywidgets, panel
# and plotly keep working exactly as before everywhere else.

set -euo pipefail
cd "$(dirname "$0")"

CONFIG_DIR=".jupyter-rise"
PORT="${RISE_PORT:-8899}"

# Make the per-cell Run button extension discoverable. Jupyter looks for
# `labextensions/` under every directory on JUPYTER_PATH, so pointing at this
# repo-local data dir loads the extension without installing anything into your
# Python environment -- your normal `jupyter lab` is unaffected.
export JUPYTER_PATH="$(cd "$(dirname "$0")" && pwd)/tools/jupyter-data"

COURSE=$(python3 -c 'import json;print(json.load(open("course.json"))["short"])' 2>/dev/null || echo "Lecture decks")

if [ $# -eq 0 ]; then
  echo "$COURSE"
  echo "Lectures:"
  for f in notebooks/lecture-*.ipynb; do
    n=$(basename "$f" | sed -E 's/^lecture-0?([0-9]+)-.*/\1/')
    t=$(basename "$f" .ipynb | sed -E 's/^lecture-[0-9]+-//; s/-/ /g')
    printf "  %2s  %s\n" "$n" "$t"
  done
  echo
  echo "Usage: $0 <lecture-number>"
  exit 0
fi

# Resolve the argument to a notebook path.
if [ -f "$1" ]; then
  NB="$1"
else
  NUM=$(printf "%02d" "$1" 2>/dev/null || echo "$1")
  NB=$(ls notebooks/lecture-"$NUM"-*.ipynb 2>/dev/null | head -1 || true)
  if [ -z "$NB" ]; then
    echo "No lecture matching '$1'. Run '$0' with no arguments to list them." >&2
    exit 1
  fi
fi

mkdir -p "$CONFIG_DIR/labconfig"
cat > "$CONFIG_DIR/labconfig/page_config.json" <<'JSON'
{
  "disabledExtensions": {
    "@jupyter-widgets/jupyterlab-manager": true,
    "@pyviz/jupyterlab_pyviz": true,
    "@lckr/jupyterlab_variableinspector": true,
    "jupyterlab-plotly": true
  }
}
JSON

# Shift+Enter runs the cell without jumping to the next slide. See the header of
# the settings file for why. Scoped to this config dir, so a normal `jupyter lab`
# keeps stock behaviour.
SHORTCUTS="$CONFIG_DIR/lab/user-settings/@jupyterlab/shortcuts-extension"
mkdir -p "$SHORTCUTS"
cp tools/rise-shortcuts.jupyterlab-settings \
   "$SHORTCUTS/shortcuts.jupyterlab-settings"

echo "Presenting: $NB"
echo "Opening a browser tab; Ctrl+C here when you're done."
echo

# `jupyter rise` does not exist -- the package ships no console script.
# The module entry point is the standalone launcher.
JUPYTER_CONFIG_DIR="$(pwd)/$CONFIG_DIR" \
  exec python3 -m jupyterlab_rise "$NB" --port "$PORT"
