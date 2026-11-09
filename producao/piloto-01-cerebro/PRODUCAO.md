# Piloto 01 · estado da produção

Proposta aprovada: `producao/propostas/piloto-01-cerebro.md` (versão 4). Render completo
**não autorizado** ainda: aguardar a pessoa.

## Pronto

| Item                  | Arquivo                      | Detalhe                                                                                                                                  |
| --------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Narração final        | `assets/voice/narracao.mp3`  | `pm_alex` (Kokoro), 0,9×, frase a frase com pausas planejadas; 58,75 s; −15,4 LUFS, pico −1,7 dBFS; entra em 0,10 s e termina em 58,80 s |
| Texto da narração     | `narracao/frases.tsv`        | texto exibido × texto enviado à voz ("ôlho") e pausa depois de cada frase                                                                |
| Montagem da narração  | `narracao/montar.py`         | junta `narracao/frases/fN.wav`; grava `narracao/frases.json`                                                                             |
| Tempo de cada palavra | `narracao/palavras.json`     | 134 palavras, transcritas frase a frase (whisper small, pt) e alinhadas ao roteiro                                                       |
| Cortes de cena        | `narracao/cenas.json`        | cortes no meio das pausas entre cenas                                                                                                    |
| Legendas              | `compositions/legendas.html` | gerado por `narracao/gerar_legendas.py`: branco em negrito, palavras-chave em ciano, palavra a palavra                                   |
| Timeline              | `index.html`                 | 61 s, 1080×1920, 30 fps; cenas 1–8 nos tempos definitivos, legendas, narração e trilha                                                   |
| Trilha (candidata)    | `assets/bgm/trilha.mp3`      | MusicGen local, 62 s; fora do Git (1,2 MB passa do limite de 500 KB sem LFS)                                                             |

Os áudios derivados (narração montada e trilha) ficam fora do Git por tamanho. Para refazê-los
a partir das frases versionadas em `narracao/frases/`: `bash narracao/refazer-audio.sh`.

Para regerar só a trilha (semente fixa):

```bash
cd producao/piloto-01-cerebro
python3 ../ferramentas/musica.py "dark cinematic science documentary underscore, deep pulsing synth bass, low sustained strings, mysterious and curious, slow build, no drums, 90 bpm" 62 assets/bgm/trilha.wav
ffmpeg -i assets/bgm/trilha.wav -c:a libmp3lame -b:a 160k assets/bgm/trilha.mp3 && rm assets/bgm/trilha.wav
```

Para refazer narração, tempos e legendas depois de mudar `narracao/frases.tsv`: gerar cada frase
com `hyperframes tts narracao/frases/fN.txt --voice pm_alex --speed 0.9 -o narracao/frases/fN.wav`,
rodar `python3 narracao/montar.py`, normalizar (mesma cadeia do `preparar-audio.sh`), transcrever
cada frase e rodar `python3 narracao/gerar_legendas.py`.

## Pendente

1. **Visual das cenas 1–8:** `compositions/cena1.html` a `cena8.html` são marcadores provisórios
   (texto cinza com o nome da cena). A técnica de animação 3D ainda não foi definida
   (`CONTEXTO-DO-CANAL.md`, seção 9).
2. **Efeitos sonoros:** os do pacote embutido estão em `assets/sfx/`. O tique de relógio e o quique
   de bola não vieram: a Openverse achou opções, mas o `cdn.freesound.org` recusa o download direto
   (HTTP 403 do próprio servidor, não do proxy).
3. **Mixagem da trilha:** quase silêncio no reveal do gorila e crescendo na revelação (automação
   de volume), e normalização final do mix para ~−14 LUFS.
4. **Loop:** o quadro 0 e o fim (59,0–61 s) dependem do visual da cena 1 e da cena 8.
