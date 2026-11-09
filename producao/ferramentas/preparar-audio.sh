#!/usr/bin/env bash
# Prepara o áudio de um vídeo a partir do roteiro, tudo gratuito e local:
#   roteiro.txt → narração (Kokoro, pt-BR) → palavras com tempo (whisper)
#   → compositions/legendas.html → trilha instrumental (MusicGen)
#
# Uso:
#   producao/ferramentas/preparar-audio.sh <pasta-do-projeto> [opções]
#     --voz pf_dora|pm_alex|pm_santa   (padrão pf_dora)
#     --velocidade 1.0                 (0.8 a 1.2)
#     --inicio 0.3                     (segundo em que a narração começa no vídeo)
#     --duracao 15                     (duração total do vídeo, em segundos)
#     --musica "calm lo-fi ..."        (clima da trilha, em inglês; "nenhuma" pula)
#
# O projeto precisa ter roteiro.txt. Arquivos já existentes de outro nome não são tocados;
# narracao.mp3, transcript.json, legendas.html e trilha.mp3 são regravados a cada execução.
set -euo pipefail

PROJ="${1:?uso: preparar-audio.sh <pasta-do-projeto> [opções]}"
shift
VOZ="pf_dora"
VEL="1.0"
INICIO="0.3"
DURACAO=""
MUSICA="calm lo-fi chillhop, soft electric piano, warm pads, gentle drums, 85 bpm"
while [ $# -gt 0 ]; do
  case "$1" in
    --voz) VOZ="$2"; shift 2 ;;
    --velocidade) VEL="$2"; shift 2 ;;
    --inicio) INICIO="$2"; shift 2 ;;
    --duracao) DURACAO="$2"; shift 2 ;;
    --musica) MUSICA="$2"; shift 2 ;;
    *) echo "opção desconhecida: $1" >&2; exit 1 ;;
  esac
done

AQUI="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_CLI="$(ls -d /root/.claude/plugins/cache/hyperframes/hyperframes/*/skills/hyperframes/scripts/plugin-cli.mjs 2>/dev/null | sort -V | tail -1 || true)"
if [ -n "$PLUGIN_CLI" ]; then HF=(node "$PLUGIN_CLI"); else HF=(npx --yes hyperframes); fi
export NODE_USE_ENV_PROXY=1 NODE_NO_WARNINGS=1   # o Node só passa pelo proxy da nuvem com isto

cd "$PROJ"
[ -f roteiro.txt ] || { echo "falta roteiro.txt em $PROJ" >&2; exit 1; }
mkdir -p assets/voice assets/bgm compositions

echo "▸ narração ($VOZ, ${VEL}x)"
"${HF[@]}" tts roteiro.txt --voice "$VOZ" --speed "$VEL" -o assets/voice/narracao-bruta.wav | tail -1
# A voz do Kokoro tem picos altos para o volume médio: comprime e normaliza para ~-15 LUFS.
ffmpeg -hide_banner -loglevel error -y -i assets/voice/narracao-bruta.wav \
  -af "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,loudnorm=I=-15:TP=-1.5:LRA=7" \
  -ar 44100 assets/voice/narracao.wav
rm -f assets/voice/narracao-bruta.wav

echo "▸ palavras com tempo (whisper small, português)"
"${HF[@]}" transcribe assets/voice/narracao.wav --model small --language pt --json | tail -1 >/dev/null

FALA=$(ffprobe -v error -show_entries format=duration -of csv=p=0 assets/voice/narracao.wav)
if [ -z "$DURACAO" ]; then
  DURACAO=$(python3 -c "import math; print(math.ceil($FALA + $INICIO + 2.2))")
fi
echo "  fala: ${FALA}s · vídeo: ${DURACAO}s"

echo "▸ legendas"
node "$AQUI/legendas.mjs" assets/voice/transcript.json compositions/legendas.html \
  --offset "$INICIO" --duracao "$DURACAO"

if [ "$MUSICA" != "nenhuma" ]; then
  echo "▸ trilha (MusicGen local, ~1-2 min)"
  python3 "$AQUI/musica.py" "$MUSICA" "$(python3 -c "print($DURACAO + 1)")" assets/bgm/trilha.wav 2>&1 | grep '^\[musica\]'
  ffmpeg -hide_banner -loglevel error -y -i assets/bgm/trilha.wav -c:a libmp3lame -b:a 160k assets/bgm/trilha.mp3
  rm -f assets/bgm/trilha.wav
fi

# MP3 no projeto: o repositório recusa binários acima de 500 KB fora do Git LFS.
ffmpeg -hide_banner -loglevel error -y -i assets/voice/narracao.wav -c:a libmp3lame -b:a 192k assets/voice/narracao.mp3
rm -f assets/voice/narracao.wav

# Resumo para montar as cenas: cada palavra com o tempo já deslocado para o vídeo.
python3 - "$INICIO" <<'EOF'
import json, sys
off = float(sys.argv[1])
w = json.load(open("assets/voice/transcript.json"))
print("▸ palavras (tempo no vídeo):")
print(" ".join(f"{x['text']}@{x['start'] + off:.2f}" for x in w))
EOF
echo "✓ áudio pronto em $PROJ"
