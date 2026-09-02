#!/usr/bin/env bash
# One-time container setup for the CS0001 lecture runtime.
# Runs as postCreateCommand, so students never type a pip command.

set -euo pipefail
cd "$(dirname "$0")/.."

# Install system-wide, not with --user. A user install can place RISE's server
# extension configuration somewhere Jupyter does not scan.
if ! command -v sudo >/dev/null 2>&1; then
  echo "ERROR: sudo not available; cannot install system-wide." >&2
  echo "       Run 'python -m pip install -r requirements.txt' as root." >&2
  exit 1
fi

echo "==> Installing CS0001 lecture runtime"
sudo python -m pip install --quiet --upgrade pip
sudo python -m pip install --quiet -r requirements.txt

# Guard against frontend extensions known to produce a blank RISE page. The
# clean devcontainer image does not include them, but disabling them keeps a
# later install from breaking presentation mode.
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

echo "==> Installing presentation keyboard shortcuts"
SHORTCUTS="${HOME}/.jupyter/lab/user-settings/@jupyterlab/shortcuts-extension"
mkdir -p "$SHORTCUTS"
cp tools/rise-shortcuts.jupyterlab-settings \
  "${SHORTCUTS}/shortcuts.jupyterlab-settings"

echo "==> Verifying install"
python - <<'PY'
from importlib.metadata import PackageNotFoundError, version
import importlib.util

for module in ("jupyterlab", "jupyterlab_rise", "IPython", "ipykernel", "nbformat"):
    if importlib.util.find_spec(module) is None:
        raise SystemExit(f"ERROR: required Python module is missing: {module}")

try:
    jupyterlab_version = version("jupyterlab")
    rise_version = version("jupyterlab-rise")
except PackageNotFoundError as error:
    raise SystemExit(f"ERROR: required package is missing: {error.name}") from error

if jupyterlab_version.split(".", 1)[0] != "4":
    raise SystemExit(
        f"ERROR: JupyterLab 4 is required; found {jupyterlab_version}."
    )

print(f"    JupyterLab {jupyterlab_version}")
print(f"    jupyterlab-rise {rise_version}")
print("    Python modules OK")
PY

# Jupyter colorizes extension listings, so strip ANSI escapes before matching.
LABEXT="$(jupyter labextension list 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"
for extension in jupyterlab-rise cs1-rise-run-button; do
  if printf '%s\n' "$LABEXT" | grep -Eq "${extension} v.* enabled OK"; then
    echo "    ${extension} labextension OK"
  else
    echo "ERROR: ${extension} labextension is not enabled and OK." >&2
    printf '%s\n' "$LABEXT" | sed 's/^/      /' >&2
    exit 1
  fi
done

SERVEREXT="$(jupyter server extension list 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"
if printf '%s\n' "$SERVEREXT" | grep -Eq 'jupyterlab_rise.*OK'; then
  echo "    jupyterlab_rise server extension OK"
else
  echo "ERROR: jupyterlab_rise server extension is not enabled and OK." >&2
  printf '%s\n' "$SERVEREXT" | sed 's/^/      /' >&2
  exit 1
fi

echo
echo "Setup complete. JupyterLab starts automatically; see the terminal for its URL."
