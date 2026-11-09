#!/usr/bin/env bash
# Reconstrói os arquivos de áudio derivados do piloto 01 (ficam fora do Git por tamanho):
#   assets/voice/narracao.mp3  ← narracao/frases/fN.wav (versionados) + pausas de frases.tsv
#   assets/bgm/trilha.mp3      ← MusicGen local, semente fixa (só se ainda não existir)
# Uso: bash narracao/refazer-audio.sh   (na pasta do projeto)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 narracao/montar.py
ffmpeg -hide_banner -loglevel error -y -i narracao/narracao-bruta.wav \
  -af "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,loudnorm=I=-15:TP=-1.5:LRA=7" \
  -ar 44100 narracao/narracao.wav
mkdir -p assets/voice assets/bgm
ffmpeg -hide_banner -loglevel error -y -i narracao/narracao.wav -c:a libmp3lame -b:a 192k assets/voice/narracao.mp3
if [ ! -f assets/bgm/trilha.mp3 ]; then
  python3 ../ferramentas/musica.py "dark cinematic science documentary underscore, deep pulsing synth bass, low sustained strings, mysterious and curious, slow build, no drums, 90 bpm" 62 assets/bgm/trilha.wav
  ffmpeg -hide_banner -loglevel error -y -i assets/bgm/trilha.wav -c:a libmp3lame -b:a 160k assets/bgm/trilha.mp3
  rm -f assets/bgm/trilha.wav
fi
echo "✓ áudio derivado pronto"
