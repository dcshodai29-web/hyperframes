# Piloto 01 · nota de entrega

"Seu cérebro esconde coisas de você" · 61 s · 1080×1920 · 30 fps · `renders/piloto-01-cerebro-61s.mp4`

## Escolhas criativas

- **Voz:** `pm_alex` (Kokoro), a amostra B escolhida, agora sintetizada uma vez por cena em vez de
  frase a frase: o modelo entoa as frases de cada cena como um trecho contínuo. As pausas de fim de
  frase foram alongadas para 0,30–0,46 s (variadas) e as respirações entre cenas ficaram em
  0,62–0,82 s. Velocidade por cena entre 0,84 (fecho) e 0,90 (desenvolvimento). Acabamento: sala
  discreta (~ −23 dB), equalização (corpo, menos embolado, presença), de-esser, compressão e limitador.
- **Legendas:** começam em "Agora mesmo"; a primeira frase é o próprio título do gancho, para o texto
  não aparecer duas vezes. Branco em negrito, palavras-chave em ciano, palavra a palavra, com fundo
  escuro translúcido do tamanho do texto (necessário sobre a retina laranja e a esclera clara).
- **Cena 4:** leitura de um parágrafo no lugar de um rosto (contexto clássico das ~3 sacadas/s).
- **Transições:** mergulho na pupila (1→2), troca por desfoque (2→3), chicote vertical (3→4), o olho
  continua de uma cena para a outra (4→5), whip-pan que imita a sacada (dentro da 5), escurecimento
  (5→6), recuo para dentro da cabeça (6→7), mergulho no olho e saída da pupila (7→8).
- **Loop:** a cena 8 usa o "tempo do loop" (t − 9,10 s): zoom, poeira e granulação no último quadro
  estão no estado do quadro 0, e o push-in continua na mesma velocidade.

## O que foi medido

- `hyperframes check`: sem erros e sem avisos (fora o aviso de arquivo grande nos arquivos gerados).
- Narração: o whisper `medium` reconhece as 134 palavras sem nenhuma diferença do roteiro.
  Fala de 0,10 s a 57,96 s: o corte de 60 s do Shorts não perde palavra.
- Loop: diferença média entre o primeiro e o último quadro do MP4 = 1,3 de 255 (granulação).
- Áudio do MP4 final: −14,0 LUFS integrados (também na versão cortada em 60 s), pico −1,0 dBTP,
  sem clipping. O primeiro render saiu em −11,2 LUFS porque a voz mono vira estéreo (+3 dB na medida);
  todos os volumes desceram 3 dB por igual, mantendo o equilíbrio entre voz, trilha e efeitos.
- Render: 1.830 quadros, 61,000 s, H.264 CRF 18 com teto de 16 Mbps, 39,5 MB, ~8,7 min neste contêiner.
- Revisão por quadros: começo e meio de cada cena, ±0,2 s em volta de cada corte, folha de celular.

## O que ninguém conferiu

- **O som não foi ouvido**, só medido: a naturalidade da voz e a qualidade da trilha (MusicGen local)
  precisam do ouvido da pessoa.
- O vídeo não foi assistido num celular de verdade.

## Plano mais fraco e o que eu mudaria com mais tempo

- **Cena 6 (quadra):** figuras 2D estilizadas; funciona como "reconstrução ilustrativa", mas é a cena
  menos cinematográfica. É a primeira candidata a uma placa gerada externamente.
- **Cena 2 (túnel):** os raios de luz são genéricos; um cristalino com refração real seria melhor.
- **O olho (cenas 1 e 8):** ainda se lê como computação gráfica; a placa fotorrealista prevista na
  arquitetura híbrida resolveria (precisa de login na HeyGen ou outra ferramenta externa).
- **Som:** faltam o tique de relógio e o quique de bola reais (o Freesound recusa o download direto).

## Avisos mantidos de propósito

- `composition_file_too_large` em `legendas.html` (gerado), `cena5.html` (relógio SVG) e cenas 6–7
  (quadra SVG): arquivos gerados ou de desenho, sem ganho em dividir.
- Mensagens "GPU stall due to ReadPixels" no console: efeito da captura de WebGL por software.
- O relógio da cena 5 está marcado como decorativo para o medidor de layout: o medidor via os
  ponteiros como fundo dos números e acusava contraste baixo num mostrador claro com números escuros.
