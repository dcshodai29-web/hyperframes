# Piloto 01 · estado da produção

Proposta aprovada: `producao/propostas/piloto-01-cerebro.md` (versão 4). Render autorizado pela
pessoa ("pode criar o vídeo") com a voz B tornada mais fluida. Nota de entrega: `REVIEW.md`.

## O que está pronto

| Item               | Arquivo                                                                | Detalhe                                                                         |
| ------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Vídeo              | `renders/piloto-01-cerebro-61s.mp4`                                    | 61 s, 1080×1920, 30 fps (fora do Git; o render é refeito a partir do projeto)   |
| Narração           | `assets/voice/narracao.mp3`                                            | `pm_alex` (Kokoro), uma passada por cena; fala de 0,10 a 57,96 s; −14,2 LUFS    |
| Síntese por cena   | `narracao/sintetizar_cenas.py`, `narracao/cenas/`                      | velocidade por cena (0,84–0,90), pausas de frase e de cena variadas             |
| Acabamento da voz  | `narracao/acabamento.py` + cadeia em `narracao/refazer-audio.sh`       | sala discreta, EQ, de-esser, compressão, limitador                              |
| Tempo das palavras | `narracao/palavras.json`                                               | 134 palavras, alinhadas ao roteiro por cena                                     |
| Cortes de cena     | `narracao/cenas.json`                                                  | no meio das pausas entre cenas                                                  |
| Legendas           | `compositions/legendas.html` (gerado por `narracao/gerar_legendas.py`) | começam em "Agora mesmo" (a 1ª frase é o título do gancho)                      |
| Cenas 1–8          | `compositions/cena1.html` … `cena8.html`                               | WebGL e gráficos, ver abaixo                                                    |
| Biblioteca visual  | `assets/lib/ciencia-gl.js`                                             | shaders do canal: olho, retina, campos visuais, mosaico, partículas, acabamento |
| Trilha             | `assets/bgm/trilha.mp3`                                                | MusicGen local; automação de volume no `index.html` (fora do Git, ver abaixo)   |
| Efeitos            | `assets/sfx/` + 34 `<audio>` no `index.html`                           | pacote embutido (licença Pixabay); `tique-longo.mp3` é o `click.mp3` com eco    |

Refazer os áudios derivados (fora do Git por tamanho): `bash narracao/refazer-audio.sh`
(com `--sintetizar` refaz também a síntese e a transcrição por cena).

## Como cada cena foi feita (tudo local, sem serviços externos)

1. Olho macro em shader (íris procedural, córnea úmida, poeira, grão); o buraco recorta a imagem; mergulho na pupila.
2. Túnel de luz → fundo de olho com cores naturais e vasos saindo do disco → fotorreceptores; o disco fica vazio.
3. Paisagem procedural; campos visuais dos dois olhos; preenchimento como continuação do entorno (a pedra não volta).
4. Leitura com pontos de fixação, olho em "câmera de rastreamento", medidor de sensibilidade e queda de contraste.
5. Olho salta, câmera salta (whip-pan) até o relógio SVG; o 1º intervalo dura 1,6 s, os seguintes 1 s.
6. Reconstrução ilustrativa da quadra (SVG); profundidade de campo = atenção; o foco muda para o gorila.
7. Cabeça em perfil; 4.200 partículas, 6% passam do olho ao córtex; mosaico seleciona/completa/monta.
8. Saída da pupila até o enquadramento do quadro 0; buraco volta e fecha; título volta; loop exato.

## Diferenças em relação à proposta

- **Narração:** em vez de frase a frase (amostra B), uma passada por cena, para a entonação fluir entre
  as frases, com pausas medidas e variadas (pedido da pessoa: voz mais fluida e humana).
- **Cena 4:** leitura de um parágrafo no lugar de "um rosto" (a leitura é o contexto clássico das ~3
  sacadas por segundo e não exige desenhar um rosto).
- **Cena 6:** sem o som de quique de bola (o download do Freesound é recusado pelo servidor).
- **Visual:** 100% local (WebGL e SVG). As placas fotorrealistas geradas externamente, previstas na
  arquitetura híbrida, não foram usadas porque não há login na HeyGen; as cenas 1, 6 e 7 são as
  candidatas a receber essas placas depois.
