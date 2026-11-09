#!/usr/bin/env bash
# Cria um projeto de vídeo vertical em producao/<nome>, pronto para este ambiente:
# modelo HyperFrames, GSAP local (o CDN é bloqueado na nuvem), efeitos sonoros gratuitos
# e o roteiro em roteiro.txt.
#
# Uso: producao/ferramentas/novo-projeto.sh <nome> "<roteiro ou ideia>"
# Não sobrescreve: recusa se a pasta já existir.
set -euo pipefail
NOME="${1:?uso: novo-projeto.sh <nome> \"<roteiro>\"}"
ROTEIRO="${2:-}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
DEST="$RAIZ/$NOME"
[ -e "$DEST" ] && { echo "já existe: $DEST (escolha outro nome)" >&2; exit 1; }

PLUGIN_CLI="$(ls -d /root/.claude/plugins/cache/hyperframes/hyperframes/*/skills/hyperframes/scripts/plugin-cli.mjs 2>/dev/null | sort -V | tail -1 || true)"
if [ -n "$PLUGIN_CLI" ]; then HF=(node "$PLUGIN_CLI"); else HF=(npx --yes hyperframes); fi
export NODE_USE_ENV_PROXY=1 NODE_NO_WARNINGS=1

cd "$RAIZ"
"${HF[@]}" init "$NOME" --skip-skills --skill=hyperframes --non-interactive >/dev/null
mkdir -p "$DEST/assets/vendor" "$DEST/assets/sfx" "$DEST/compositions"
cp "$AQUI/vendor/gsap.min.js" "$DEST/assets/vendor/gsap.min.js"
SFX="$(ls -d /root/.claude/plugins/cache/hyperframes/hyperframes/*/skills/media-use/audio/assets/sfx 2>/dev/null | sort -V | tail -1 || true)"
if [ -n "$SFX" ]; then
  cp "$SFX"/*.mp3 "$SFX/CREDITS.md" "$SFX/manifest.json" "$DEST/assets/sfx/"
fi
[ -n "$ROTEIRO" ] && printf '%s\n' "$ROTEIRO" > "$DEST/roteiro.txt"
echo "✓ projeto criado: $DEST"
