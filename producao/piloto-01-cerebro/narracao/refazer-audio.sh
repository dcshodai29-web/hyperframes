#!/usr/bin/env bash
# Reconstrói os arquivos de áudio derivados do piloto 01 (ficam fora do Git por tamanho).
#
# Narração (versão fluida): uma passada do Kokoro por cena, pausas de fim de frase ajustadas
# com o tempo de cada palavra, sala discreta, equalização, compressão, -14 LUFS com limitador.
#   narracao/cenas/cN-bruta.flac       síntese por cena (versionada)
#   narracao/cenas/cN-transcript.json  tempos do whisper por cena (versionados)
#   → narracao/narracao-bruta.wav, narracao/palavras.json, narracao/cenas-fala.json
#   → narracao/narracao-sala.wav → narracao/narracao.wav → assets/voice/narracao.mp3
# Trilha: MusicGen local, semente fixa (só se ainda não existir).
#
# Uso (na pasta do projeto): bash narracao/refazer-audio.sh [--sintetizar]
#   --sintetizar   refaz também a síntese e a transcrição de cada cena (precisa do Kokoro e do whisper)
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_USE_ENV_PROXY=1 NODE_NO_WARNINGS=1

if [ "${1:-}" = "--sintetizar" ]; then
  PLUGIN_CLI="$(ls -d /root/.claude/plugins/cache/hyperframes/hyperframes/*/skills/hyperframes/scripts/plugin-cli.mjs | sort -V | tail -1)"
  python3 narracao/sintetizar_cenas.py sintetizar
  TMP="$(mktemp -d)"
  for f in narracao/cenas/c*-bruta.flac; do
    n="$(basename "$f" -bruta.flac)"
    mkdir -p "$TMP/$n"
    ffmpeg -hide_banner -loglevel error -y -i "$f" "$TMP/$n/a.wav"
    (cd "$TMP/$n" && node "$PLUGIN_CLI" transcribe a.wav --model small --language pt --json >/dev/null)
    cp "$TMP/$n/transcript.json" "narracao/cenas/$n-transcript.json"
  done
  rm -rf "$TMP"
fi

python3 narracao/sintetizar_cenas.py pausas
python3 narracao/acabamento.py
ffmpeg -hide_banner -loglevel error -y -i narracao/narracao-sala.wav \
  -af "highpass=f=70,equalizer=f=160:t=q:w=0.9:g=1.5,equalizer=f=350:t=q:w=1.2:g=-1.2,equalizer=f=3000:t=q:w=1.0:g=1.2,deesser=i=0.25,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-15:TP=-1.5:LRA=8,volume=1.6dB,alimiter=limit=0.84:attack=4:release=60:level=disabled" \
  -ar 44100 narracao/narracao.wav
mkdir -p assets/voice assets/bgm
ffmpeg -hide_banner -loglevel error -y -i narracao/narracao.wav -c:a libmp3lame -b:a 192k assets/voice/narracao.mp3

if [ ! -f assets/bgm/trilha.mp3 ]; then
  python3 ../ferramentas/musica.py "dark cinematic science documentary underscore, deep pulsing synth bass, low sustained strings, mysterious and curious, slow build, no drums, 90 bpm" 62 assets/bgm/trilha.wav
  ffmpeg -hide_banner -loglevel error -y -i assets/bgm/trilha.wav -c:a libmp3lame -b:a 160k assets/bgm/trilha.mp3
  rm -f assets/bgm/trilha.wav
fi
python3 narracao/gerar_legendas.py
echo "✓ áudio derivado e legendas prontos"
