#!/usr/bin/env bash
# Instala o ambiente do editor (idempotente). Os modelos são baixados sob demanda;
# use `--modelos` para pré-baixar o conjunto essencial (~19 GB).
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${FOTOIA_VENV:-/opt/fotoia/venv}"
PY="$(command -v python3.12 || command -v python3)"
if [ ! -x "$VENV/bin/python" ]; then
  mkdir -p "$(dirname "$VENV")"
  if command -v uv >/dev/null 2>&1; then uv venv --python "$PY" "$VENV"; else "$PY" -m venv "$VENV"; fi
fi
if command -v uv >/dev/null 2>&1; then PIP="uv pip install --python $VENV/bin/python"; else PIP="$VENV/bin/pip install"; fi
$PIP --index-url https://download.pytorch.org/whl/cpu torch torchvision
$PIP -r "$HERE/requirements.txt"
mkdir -p "$HERE/entradas" "$HERE/saidas"
if [ "$1" = "--modelos" ]; then
  cd "$HERE" && "$VENV/bin/python" -m fotoia modelos --baixar flux2-klein-4b birefnet birefnet-hr sam2 grounding-dino \
    yunet face-parsing depth-small lama realesrgan-x4plus realesrgan-x2plus
fi
echo "[fotoia] ambiente pronto em $VENV"
