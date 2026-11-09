# Piloto 01: "Seu cérebro esconde coisas de você"

Proposta editorial, **versão 4** · **produzido** em 2026-11-09 (ver `producao/piloto-01-cerebro/PRODUCAO.md` e `REVIEW.md`). Aprovados: tema, as oito cenas, identidade visual, duração de
61 s e final em loop. Produção ainda não autorizada; a voz está em avaliação pela pessoa. Nada foi
renderizado e o pipeline não foi alterado. Segue `producao/CONTEXTO-DO-CANAL.md` (SCIENCE
CINEMATIC, RETENTION CINEMATIC, 61 s, 1080×1920, 30 fps).

## O que mudou da versão 3 (preparação de produção)

Voz adotada: amostra B (`pm_alex`, Kokoro, 0,9×, frase a frase com pausas planejadas).

1. **"olho":** o fonetizador lia "ólio" (`ˈɔljʊ`, "ó" aberto). A voz recebe a grafia fonética
   "ôlho"; roteiro e legendas continuam com "olho". Verificado: transcrito como "olho".
2. **"E o buraco?":** a voz fundia "E o" e não faz entonação de pergunta (o tom cai de 165 para
   111 Hz, igual a uma afirmação). A frase virou afirmação: **"E aquele buraco continua aí."**,
   transcrita sem erro e com entonação natural de afirmação.
3. **"há em volta":** transcrito como "é em volta". Trocado por **"existe em volta"**, transcrito
   sem erro.
4. Narração final: 59,16 s → **58,75 s**; começa em 0,10 s e termina em **58,80 s** no vídeo,
   antes do corte de 60 s do Shorts. −15,4 LUFS, pico −1,7 dBFS. As 134 palavras conferem com o
   roteiro, frase a frase.

Os tempos de cena desta proposta (versão 3) mudam menos de 0,5 s; os definitivos estão em
`producao/piloto-01-cerebro/narracao/cenas.json`.

## O que mudou da versão 2

1. **Cena 3:** o preenchimento do ponto cego aparece como continuação das linhas e cores das
   bordas, com guias visíveis, e não como uma imagem nova.
2. **Cena 4:** a supressão sacádica aparece como queda momentânea e gradual da percepção (contraste
   e nitidez) durante cada salto; o rastro do movimento continua existindo, só que fraco demais
   para ser notado.
3. **Loop:** aprovado; a cena 8 detalha como o último quadro volta ao estado do quadro 0.

Roteiro, tempos, legendas e trilha não mudaram.

## O que mudou da versão 1

1. **Supressão sacádica:** o roteiro não diz mais que o cérebro "apaga" instantes; diz que a
   sensibilidade visual diminui durante cada salto dos olhos.
2. **Cronóstase:** a fala deixa explícito que a ilusão acontece depois de mover os olhos até o
   relógio, e que é o primeiro segundo observado que parece mais longo.
3. **Ponto cego:** separa os dois mecanismos: com os dois olhos, um olho cobre a falha do outro;
   com um só, o cérebro preenche a falha com o que há em volta.
4. **Gorila:** a cena é anunciada na tela como reconstrução ilustrativa do experimento original.
5. **Duração:** o roteiro caiu de ~157 para 134 palavras. A duração foi medida com a voz `pm_alex`
   real, gerada frase a frase com pausas planejadas, sem acelerar: **58,8 s de fala, ~2,3 palavras
   por segundo**, começando em 0,15 s e terminando em ~59,0 s.

## Roteiro revisado (134 palavras)

Tempos medidos na narração de teste `pm_alex` a 0,9× (início em 0,15 s). Os cortes de cena caem no
meio das pausas.

| Cena                | Imagem    | Fala      | Narração                                                                                                                              |
| ------------------- | --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 1 · Gancho          | 0,0–4,2   | 0,15–3,9  | Existe um buraco na sua visão. Agora mesmo.                                                                                           |
| 2 · Curiosidade     | 4,2–9,8   | 4,5–9,5   | No fundo de cada olho, onde nasce o nervo óptico, não há células que captam luz.                                                      |
| 3 · Contexto        | 9,8–16,9  | 10,0–16,6 | Com os dois olhos abertos, um cobre a falha do outro. Com um só, o cérebro preenche com o que existe em volta.                        |
| 4 · Desenvolvimento | 16,9–27,4 | 17,2–27,1 | Seus olhos saltam cerca de três vezes por segundo. Durante cada salto, a sensibilidade visual diminui. E o borrão passa despercebido. |
| 5 · Desenvolvimento | 27,4–33,9 | 27,6–33,6 | Depois de mover os olhos até um relógio, o primeiro segundo que você vê parece mais longo.                                            |
| 6 · Surpresa        | 33,9–43,8 | 34,2–43,4 | Num experimento clássico sobre atenção, voluntários contavam passes de basquete. Quase metade não notou alguém fantasiado de gorila.  |
| 7 · Revelação       | 43,8–51,7 | 44,1–51,4 | Os sentidos captam mais do que você percebe. Então o cérebro seleciona, completa e monta uma versão do mundo.                         |
| 8 · Conclusão       | 51,7–61,0 | 52,0–59,0 | Você vive dentro dessa versão. E aquele buraco continua aí. Agora mesmo.                                                              |

- **Pausas expressivas:** 0,3–0,4 s entre frases da mesma cena, 0,55–0,7 s entre cenas, e uma
  respiração maior antes de "Agora mesmo". Elas são parte do ritmo, não enchimento.
- **Corte do Shorts:** a fala acaba em ~59,0 s, então o corte de 60 s não perde nenhuma palavra.
  De 59,0 a 61 s ficam só a imagem final e a cauda da trilha.
- **Relação com a estrutura de referência:** gancho 0–4 s; curiosidade e contexto 4–17 s;
  desenvolvimento 17–34 s; surpresa 34–44 s; revelação 44–52 s; conclusão 52–61 s. A revelação
  chega ~1 s antes do previsto e a conclusão ganha mais tempo, por causa das pausas finais.
- O fecho repete o gancho ("Agora mesmo") e o último quadro é igual ao primeiro, para o loop
  (aprovado; detalhes na cena 8).

## Checagem científica

| Afirmação no roteiro                                                                                    | Base                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cada olho tem um ponto sem células que captam luz, onde nasce o nervo óptico.                           | Disco óptico: não tem fotorreceptores. Fisiologia ocular padrão; descrito por Mariotte em 1660.                                                                                 |
| Com os dois olhos abertos, um cobre a falha do outro.                                                   | Os pontos cegos dos dois olhos caem em regiões diferentes do campo visual, então cada olho enxerga o que falta ao outro (compensação binocular, não preenchimento).             |
| Com um só, o cérebro preenche com o que existe em volta.                                                | Preenchimento perceptivo ("filling-in"): a região é completada com a cor e o padrão do entorno (Ramachandran, 1992; Komatsu, 2006, _Nature Reviews Neuroscience_).              |
| Os olhos saltam cerca de três vezes por segundo.                                                        | Sacadas: ~3 a 4 por segundo na leitura e na exploração visual (Rayner, 1998, _Psychological Bulletin_).                                                                         |
| Durante cada salto, a sensibilidade visual diminui.                                                     | Supressão sacádica: redução seletiva da sensibilidade visual durante a sacada (Burr, Morrone e Ross, 1994, _Nature_; revisão de Matin, 1974).                                   |
| E o borrão passa despercebido.                                                                          | Consequência observada; a frase não atribui isso a uma única causa (a supressão e o mascaramento pela imagem seguinte contribuem).                                              |
| Depois de mover os olhos até um relógio, o primeiro segundo que você vê parece mais longo.              | Cronóstase: após uma sacada, o primeiro intervalo observado no ponteiro dos segundos é percebido como mais longo (Yarrow, Haggard, Heal, Brown e Rothwell, 2001, _Nature_ 414). |
| Voluntários contavam passes de basquete; quase metade não notou alguém fantasiado de gorila.            | Simons e Chabris, 1999, _Perception_ 28: 46% dos participantes não notaram a pessoa fantasiada de gorila.                                                                       |
| Os sentidos captam mais do que você percebe; o cérebro seleciona, completa e monta uma versão do mundo. | Atenção seletiva e percepção como construção são consenso da neurociência. A frase é uma síntese sem números.                                                                   |
| Você vive dentro dessa versão.                                                                          | Metáfora de fechamento, não uma afirmação experimental.                                                                                                                         |

## Cenas: visual, 3D, câmera e som

Paleta SCIENCE CINEMATIC: fundo `#080B12`; luz e informação em azul elétrico `#1769FF` e ciano
`#00D9FF`; texto `#F5F7FA`; rótulos e fontes em cinza `#929BAA`. Íris, pele, paisagem e gorila
mantêm as cores naturais. As cenas não pressupõem ferramenta: o modelo de animação 3D ainda não
foi definido.

### Cena 1 — Gancho (0,0–4,2 s)

- **Visual:** macro de um olho em 3D, íris de cor natural, luz volumétrica lateral, profundidade
  de campo rasa. O quadro 0 já mostra o olho e "EXISTE UM BURACO NA SUA VISÃO" (é a miniatura).
  Em "Agora mesmo", um círculo preto recorta a própria imagem.
- **Câmera:** push-in lento rumo à pupila; corte seco no surgimento do buraco.
- **Som:** trilha começa no quadro 0 (pulso grave, sem vinheta); impacto sub-grave discreto no buraco.

### Cena 2 — Curiosidade (4,2–9,8 s)

- **Visual:** mergulho pela pupila, através do cristalino, em feixes de luz, até a retina: um campo
  de fotorreceptores acesos em azul e ciano. As fibras convergem num disco sem nenhuma célula, de
  onde sai o nervo óptico. Rótulo: "PONTO CEGO".
- **Câmera:** dive contínuo (a transição é o próprio movimento), pouso lento no disco, órbita de 10–15°.
- **Som:** whoosh grave suave na entrada pela pupila.

### Cena 3 — Contexto: dois mecanismos (9,8–16,9 s)

- **Visual:** dois tempos, um para cada mecanismo.
  1. "Com os dois olhos abertos": dois campos visuais translúcidos (esquerdo e direito) se
     sobrepõem; cada um tem seu buraco em lugar diferente, e cada buraco fica coberto pela imagem
     do outro olho. Rótulo: "OLHO ESQUERDO + OLHO DIREITO".
  2. "Com um só": um dos campos sai e o buraco fica exposto sobre uma cena de padrão regular e
     cores naturais, escolhida para a continuidade ficar legível: por exemplo, as fileiras de uma
     plantação cortadas por uma linha de horizonte. O preenchimento mostra que o cérebro continua
     o que existe nas bordas, não que cria algo novo:
     - um anel fino em ciano marca a borda do buraco e "amostra" o entorno: as cores e as linhas
       que tocam a borda;
     - guias tracejadas prolongam cada linha (as fileiras e o horizonte) da borda para dentro,
       na mesma direção, e a cor das bordas avança junto com elas;
     - o buraco se fecha com exatamente essa continuação; as guias somem e resta a cena contínua,
       sem nenhum detalhe que não estivesse nas bordas.
       Rótulo: "PREENCHIMENTO: CONTINUAÇÃO DO ENTORNO". Como reforço opcional, um objeto pequeno
       colocado inteiro dentro do buraco (uma pedra numa fileira) não reaparece: no lugar dele fica a
       fileira contínua. É o mesmo efeito do teste clássico do ponto cego, em que um ponto
       desaparece e dá lugar ao fundo.
- **Câmera:** estável e frontal, para o espectador ver as duas imagens se combinarem e depois as
  linhas atravessarem a falha.
- **Som:** textura granular breve no preenchimento.

### Cena 4 — Desenvolvimento: sacadas (16,9–27,4 s)

- **Visual:** pontos de fixação ciano saltam sobre um rosto, ligados por traços (padrão real de
  sacadas). O olho 3D em perfil executa os saltos; rótulo "~3 SALTOS POR SEGUNDO".
  - Em "a sensibilidade visual diminui", a cena passa a mostrar a percepção, não a câmera: a
    cada salto, a imagem inteira perde contraste e nitidez por um instante (fica mais pálida,
    nunca preta nem cortada) e volta ao normal quando o olho pousa. Um medidor discreto de
    "sensibilidade visual" desce e sobe no mesmo ritmo. É uma redução gradual e momentânea, não
    um corte.
  - Em "E o borrão passa despercebido", o movimento da imagem na retina durante o salto aparece
    como um rastro tênue, com a mesma palidez do momento de baixa sensibilidade: o rastro existe,
    mas chega fraco demais para chamar atenção. Ele não é removido nem substituído.
  - Selo em cinza: "ilustração em câmera lenta" (uma sacada real dura poucas dezenas de
    milissegundos).
- **Câmera:** whips curtos acompanhando cada sacada; zoom pontual no medidor.
- **Som:** cliques muito baixos em cada salto; a ambiência perde brilho por um instante a cada
  salto (filtro leve), espelhando a queda de sensibilidade.

### Cena 5 — Desenvolvimento: cronóstase (27,4–33,9 s)

- **Visual:** a câmera salta até um relógio analógico 3D, com borrão (é a sacada). Ao pousar, o
  ponteiro dos segundos fica visivelmente um pouco mais tempo no primeiro intervalo; os seguintes
  correm normais. Rótulos: "CRONÓSTASE" e "1º segundo após mover os olhos"; fonte em cinza:
  "Yarrow et al., Nature, 2001".
- **Câmera:** whip-pan com blur até o relógio, depois câmera parada; só o ponteiro se move.
- **Som:** tique-taque seco; o primeiro tique com cauda levemente mais longa.

### Cena 6 — Surpresa: o gorila (33,9–43,8 s)

- **Visual:** **reconstrução ilustrativa**, não reprodução do vídeo original. Selo fixo durante a
  cena: "RECONSTRUÇÃO ILUSTRATIVA · experimento original: Simons & Chabris, 1999". Jogadores
  translúcidos de branco e de preto passam uma bola luminosa; um contador marca os passes; a
  profundidade de campo segue só a bola (é a atenção). Em "alguém fantasiado de gorila", um rack
  focus revela a figura de gorila (cor natural) no meio da quadra. Texto: "46% NÃO NOTARAM".
- **Câmera:** travelling lateral acompanhando a bola; foco travado no gorila no reveal e zoom-out
  lento mostrando que ele estava em quadro desde o início.
- **Som:** quiques abafados; a trilha quase some no reveal, porque o ponto da cena é não ter percebido.

### Cena 7 — Revelação (43,8–51,7 s)

- **Visual:** a câmera recua da quadra e mostra que a cena estava dentro de uma cabeça. Milhares
  de feixes azuis de informação entram pelos olhos e se afunilam num fio ciano até o cérebro, onde
  fragmentos montam um mosaico do mundo. Em "seleciona, completa e monta", três ações visíveis:
  fragmentos descartados, lacunas preenchidas, peça final encaixada.
- **Câmera:** o pull-back mais longo do vídeo, depois órbita lenta enquanto o mosaico se monta.
- **Som:** fluxo de dados subindo; a trilha cresce para o ponto alto; três impactos suaves nas três ações.

### Cena 8 — Conclusão (51,7–61,0 s)

- **Visual:** a câmera sai do cérebro e volta ao olho da cena 1, com a mesma lente, luz e
  enquadramento. Em "E aquele buraco", o círculo preto reaparece pequeno; em "continua aí.
  Agora mesmo", fica parado sobre a pupila.
- **Loop (aprovado):** o último quadro (61,0 s) é igual ao quadro 0, e a passagem do fim para o
  começo é uma continuação, não um corte:
  - 59,0–60,2 s: o círculo preto se fecha devagar até sumir, devolvendo o olho ao estado do
    quadro 0 (no começo, o buraco só aparece em "Agora mesmo").
  - 59,4–59,9 s: o texto do gancho, "EXISTE UM BURACO NA SUA VISÃO", reaparece no mesmo lugar e
    estilo do quadro 0. Ele entra logo depois de "Agora mesmo", então lê como continuação da fala.
  - Câmera: termina no mesmo push-in lento do início, na mesma velocidade, chegando ao
    enquadramento exato do quadro 0 em 61,0 s. Na repetição, o movimento continua sem salto.
  - Som: a cauda do acorde final e do sub-grave cai até perto do silêncio em 61 s, e o pulso
    grave do quadro 0 recomeça como o próximo tempo da mesma música.
  - Versão de 60 s (Shorts): como o círculo fecha e o texto volta antes de 60 s, o quadro final
    também corresponde ao quadro 0; a diferença é só 1 s do push-in lento, imperceptível.
- **Câmera:** pull-back até o enquadramento inicial, emendando no push-in lento do quadro 0.
- **Som:** whoosh de saída; sub-grave final em "Agora mesmo", com cauda que se resolve até 61 s.

## Trilha

Instrumental cinematográfica: pulso grave de sintetizador e cordas baixas, ~90 bpm, desde o
quadro 0. Camadas entram na cena 3 (cordas) e na cena 5 (pulso rítmico, eco do relógio). Quase
silêncio no reveal do gorila; crescendo na revelação; acorde sustentado na conclusão, com cauda que
fecha o loop. A voz sempre na frente: trilha de 18 a 20 dB abaixo da narração, mix final perto de
−14 LUFS.

## Legendas

> **Versão 4:** os tempos e os grupos definitivos estão no projeto, em
> `producao/piloto-01-cerebro/compositions/legendas.html` (gerado por `narracao/gerar_legendas.py`
> a partir da narração final). A tabela abaixo é a referência da versão 3.

Palavra a palavra, texto branco `#F5F7FA` em negrito e caixa alta, palavras-chave em ciano
`#00D9FF`, um grupo de 2 a 4 palavras por vez, na faixa segura (y entre 168 e 1330). Tempos
medidos na narração de teste; serão refeitos sobre a narração final.

Palavras-chave em ciano: **BURACO, PREENCHE, TRÊS VEZES, SENSIBILIDADE, PRIMEIRO SEGUNDO, QUASE
METADE, GORILA, VERSÃO, BURACO**.

| Entrada (s) | Legenda                    |
| ----------- | -------------------------- |
| 0,1         | EXISTE UM **BURACO**       |
| 1,6         | NA SUA VISÃO.              |
| 2,7         | AGORA MESMO.               |
| 4,4         | NO FUNDO DE CADA OLHO,     |
| 6,0         | ONDE NASCE O NERVO ÓPTICO, |
| 7,7         | NÃO HÁ CÉLULAS             |
| 8,4         | QUE CAPTAM LUZ.            |
| 10,0        | COM OS DOIS OLHOS ABERTOS, |
| 11,7        | UM COBRE                   |
| 12,2        | A FALHA DO OUTRO.          |
| 13,5        | COM UM SÓ,                 |
| 14,2        | O CÉREBRO **PREENCHE**     |
| 15,5        | COM O QUE HÁ EM VOLTA.     |
| 17,2        | SEUS OLHOS SALTAM          |
| 18,4        | CERCA DE **TRÊS VEZES**    |
| 19,6        | POR SEGUNDO.               |
| 20,8        | DURANTE CADA SALTO,        |
| 22,3        | A **SENSIBILIDADE** VISUAL |
| 24,0        | DIMINUI.                   |
| 24,9        | E O BORRÃO                 |
| 25,6        | PASSA DESPERCEBIDO.        |
| 27,6        | DEPOIS DE MOVER            |
| 28,7        | OS OLHOS ATÉ UM RELÓGIO,   |
| 30,4        | O **PRIMEIRO SEGUNDO**     |
| 31,6        | QUE VOCÊ VÊ                |
| 32,2        | PARECE MAIS LONGO.         |
| 34,2        | NUM EXPERIMENTO CLÁSSICO   |
| 35,9        | SOBRE ATENÇÃO,             |
| 36,9        | VOLUNTÁRIOS CONTAVAM       |
| 38,6        | PASSES DE BASQUETE.        |
| 39,8        | **QUASE METADE** NÃO NOTOU |
| 41,6        | ALGUÉM FANTASIADO          |
| 42,6        | DE **GORILA**.             |
| 44,1        | OS SENTIDOS CAPTAM         |
| 45,4        | MAIS DO QUE VOCÊ PERCEBE.  |
| 47,4        | ENTÃO O CÉREBRO            |
| 48,4        | SELECIONA,                 |
| 49,3        | COMPLETA E MONTA           |
| 50,4        | UMA **VERSÃO** DO MUNDO.   |
| 52,0        | VOCÊ VIVE DENTRO           |
| 53,4        | DESSA **VERSÃO**.          |
| 54,8        | E O **BURACO**?            |
| 56,3        | CONTINUA AÍ.               |
| 58,0        | AGORA MESMO.               |

Rótulos gráficos ("PONTO CEGO", "PREENCHIMENTO", "~3 SALTOS POR SEGUNDO", "CRONÓSTASE", "46% NÃO
NOTARAM", selo de reconstrução) ficam acima das legendas e curtos; fontes científicas em cinza.

## Teste de voz `pm_alex` (Kokoro)

Amostras em `producao/propostas/amostras-voz-piloto-01/`, todas com o mesmo trecho (gancho e ponto
cego, 35 palavras), normalizadas a −16 LUFS para comparar por igual:

| Arquivo                            | Variação                                           | Duração | Ritmo da fala |
| ---------------------------------- | -------------------------------------------------- | ------- | ------------- |
| `A-velocidade-095.mp3`             | 0,95×, frase a frase com pausas                    | 12,8 s  | 2,75 pal/s    |
| `B-velocidade-090-recomendada.mp3` | 0,90×, frase a frase com pausas                    | 13,1 s  | 2,68 pal/s    |
| `C-velocidade-085.mp3`             | 0,85×, frase a frase com pausas                    | 13,8 s  | 2,54 pal/s    |
| `D-090-mais-grave.mp3`             | B com tom 1 semitom abaixo e mais corpo nos graves | 13,1 s  | 2,68 pal/s    |
| `E-090-leitura-continua.mp3`       | 0,90×, leitura contínua sem pausas planejadas      | 10,6 s  | 3,3 pal/s     |

Observações objetivas (as amostras não foram ouvidas por quem as gerou; a avaliação é da pessoa):

- **Pronúncia de "olho":** nas três amostras transcritas, o reconhecimento de fala ouviu "óleo"
  no lugar de "olho" (no singular; "olhos" saiu certo). Indica um "lh" pouco claro nessa palavra.
- **"E o buraco?":** na narração completa foi transcrito como "Dio buracos", sinal de que a voz
  junta "E o" e o fim da pergunta perde nitidez.
- **Controles disponíveis:** o Kokoro não tem ajuste de emoção ou ênfase; só velocidade, divisão
  em frases e pausas. A expressividade possível vem do ritmo das pausas (B a D) em comparação com
  a leitura contínua (E).
- **Variação D:** baixar o tom por processamento também desloca o timbre e pode soar artificial.
- A narração completa de teste (não entregue) mediu 57,3 s a 0,95×, 58,8 s a 0,9× e 61,7 s a
  0,85×; só 0,95× e 0,9× cabem no limite de ~59,5 s para o Shorts.

## Decisões pendentes

1. **Voz:** avaliar as amostras. Se `pm_alex` não atingir "grave, natural, sem entonação
   robótica", é preciso escolher outra forma de gerar a narração.
2. **Técnica de animação 3D:** ainda não definida.

Decidido: final em loop, com o último quadro igual ao primeiro (cena 8).
