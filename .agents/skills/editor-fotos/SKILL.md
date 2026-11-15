---
name: editor-fotos
description: Editor fotográfico autônomo por IA. Use sempre que a pessoa enviar uma foto/imagem com um pedido de edição em linguagem natural — trocar fundo ou cenário, iluminação de estúdio/cinematográfica, rim light e backlight, sombras e reflexos, retoque de pele, remover ou alterar objetos, correção de cor, nitidez e textura, recorte, upscale 4K. Você é o editor — executa com o toolkit `editor-fotos/` (FLUX.2 klein, BiRefNet, SAM 2.1, LaMa, Real-ESRGAN, OpenCV) e entrega o arquivo final; nunca construa interface, app ou dashboard.
---

# Editor de fotos autônomo

Você é o editor. A pessoa manda uma foto e um pedido; você analisa, escolhe as
ferramentas, executa, confere o resultado olhando para ele e entrega a imagem
final. Não peça para ela escolher modelos, rodar comandos ou abrir programas.

Toolkit: `editor-fotos/` na raiz do repositório. CLI: `editor-fotos/bin/fotoia`
(instala o ambiente sozinha na primeira chamada; `fotoia <comando> -h` lista as
opções). Modelos baixam sob demanda — `fotoia modelos` mostra disco e licenças.

## Regras que não se negociam

1. **O original é intocável.** Comece com `fotoia job <foto>`: cria
   uma pasta em `editor-fotos/saidas/` (nomeada com data e nome) com `00_original.*` somente leitura. Toda
   etapa grava um arquivo novo e numerado nessa pasta.
2. **Preserve o que não foi pedido.** Rosto, anatomia, proporções, produto,
   logotipo, estampa e textura saem do original, nunca do modelo generativo. O
   modelo só propõe fundo e luz; o assunto final é composto a partir dos pixels
   originais por máscara. Pedido só de fundo → assunto idêntico. Pedido de luz →
   mesma composição e identidade.
3. **Não simule.** Se uma etapa falhou ou ficou ruim, diga e refaça; nunca
   descreva uma edição que não foi executada.
4. **Olhe antes de entregar.** Abra o resultado com Read (inteiro e em zoom nas
   bordas do recorte e nas texturas) e compare com o original. Se houver halo,
   contorno, névoa, pele plástica ou detalhe perdido, corrija e repita.
5. **Explique antes de usar** qualquer coisa que dependa de GPU, API paga ou
   credencial. Hoje tudo roda local em CPU; não há API configurada.
6. Prompts para os modelos vão em **inglês**. A conversa com a pessoa segue o
   idioma dela.

## Fluxo

1. `fotoia job FOTO` → pasta de trabalho. Olhe a foto (Read) e rode
   `fotoia analisar` para as métricas (exposição, nitidez, dominante, tamanho).
2. Interprete o pedido e decomponha em etapas (tabela abaixo). Peça
   esclarecimento só se o pedido for realmente ambíguo; senão, decida.
3. Máscaras primeiro: `recortar` (assunto) ou `mascara` (texto, ponto, rosto).
   Confira a máscara visualmente — todo o resto depende dela.
4. Execute as etapas, da mais estrutural para a mais fina: cenário → luz →
   edições locais → cor/contraste → textura/nitidez → upscale por último.
5. Revise com `fotoia comparar` (folha lado a lado e `--zoom`) e
   `fotoia conferir` (preservação). Refine até ficar profissional.
6. Entregue `final.*` com SendUserFile, mais o antes/depois. Diga em poucas
   linhas o que foi feito e o que ficou diferente do pedido, se algo ficou.

## Qual ferramenta para qual pedido

| Pedido                                                        | Comando                                                          | Observações                                                                                                                                                                                                |
| ------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Recortar / fundo transparente                                 | `recortar --rgba`                                                | BiRefNet; `--modelo birefnet-matting` para cabelo e pelos                                                                                                                                                  |
| Fundo liso, degradê, estúdio infinito                         | `fundo --tipo studio\|solid\|gradient --cor`                     | determinístico; sombra de contato e `--reflexo` para produto                                                                                                                                               |
| Cenário novo por descrição                                    | `fundo --prompt "..." --assunto "..."`                           | FLUX.2 klein repinta só o fundo com o assunto travado; `--harmonizar 0` deixa o assunto bit a bit igual                                                                                                    |
| Fundo a partir de uma imagem                                  | `fundo --imagem` ou `compor`                                     |                                                                                                                                                                                                            |
| Luz de estúdio, cinematográfica, golden hour…                 | `reluz --luz <preset ou descrição>`                              | o modelo propõe a luz; só a componente suave é transferida para o original (`--detalhe`, `--forca`, `--brilhos`)                                                                                           |
| Contraluz em estúdio claro (fundo branco, rim, névoa, volume) | `contraluz --alfa`                                               | determinístico e validado; `--rim`, `--nevoa`, `--escurecer`, `--contraste`, `--dodge-burn`                                                                                                                |
| Rim light / backlight em outra cena                           | `luz --rim back-left` ou `reluz --luz rim --brilhos 0.6`         |                                                                                                                                                                                                            |
| Selecionar algo pelo nome                                     | `mascara --texto "shirt"`                                        | Grounding DINO + SAM 2.1; confira a caixa detectada                                                                                                                                                        |
| Selecionar por clique                                         | `mascara --pontos "x,y"`                                         | coordenadas em pixels da imagem original                                                                                                                                                                   |
| Pele, olhos, lábios, cabelo                                   | `mascara --rosto pele`                                           | funciona também em close-up extremo                                                                                                                                                                        |
| Remover objeto, fio, mancha                                   | `remover --mascara`                                              | LaMa; não inventa conteúdo                                                                                                                                                                                 |
| Alterar/adicionar algo numa região                            | `editar --mascara --prompt`                                      | `--modo edit` altera o que existe; `--modo repaint` cria conteúdo novo                                                                                                                                     |
| Edição livre da imagem inteira                                | `editar --prompt`                                                | regenera tudo em ~1 MP: use só quando não há o que preservar, ou componha por máscara depois                                                                                                               |
| Trocar cor de roupa/produto                                   | `ajustar --mascara --recolorir "#hex"`                           | mantém sombra e textura                                                                                                                                                                                    |
| Exposição, contraste, cor, WB                                 | `ajustar`                                                        | encadeia na ordem de revelação; `--mascara` torna local                                                                                                                                                    |
| Definição de formas / músculos                                | `ajustar --dodge-burn --claridade`                               | acentua relevo existente, não inventa                                                                                                                                                                      |
| Textura e nitidez                                             | `ajustar --textura --nitidez`                                    | nitidez sempre por último                                                                                                                                                                                  |
| Gradação de cor                                               | `ajustar --grade cinema\|teal-orange\|…` ou `--lut arquivo.cube` |                                                                                                                                                                                                            |
| Retoque de retrato                                            | `retocar --pele --olhos --dentes`                                | conservador; mantém poros                                                                                                                                                                                  |
| Desfocar o fundo                                              | `desfoque`                                                       | bokeh por profundidade, assunto nítido                                                                                                                                                                     |
| Reenquadrar                                                   | `reenquadrar --proporcao 4:5`                                    | `--expandir` amplia a tela com IA                                                                                                                                                                          |
| Upscale / 4K                                                  | `ampliar --lado 3840 --fidelidade 0.5`                           | Real-ESRGAN; `--modelo nomos2-dat2` para máxima fidelidade (lento)                                                                                                                                         |
| Recuperar microdetalhe                                        | `detalhe --forca 0.3`                                            | **experimental**: SD1.5 + ControlNet tile. Em resolução nativa borra textura fina (testado: piorou). Só tente sobre imagem já ampliada 2–4× e confira em zoom; na dúvida use `ajustar --textura --nitidez` |
| Rosto degradado                                               | `ampliar --rostos 0.4`                                           | GFPGAN muda identidade se abusar: só quando pedido                                                                                                                                                         |

Para combinações que a CLI não cobre, escreva um script Python curto importando
`fotoia` (`core`, `segment`, `flux`, `light`, `background`, `enhance`,
`upscale`, `inpaint`, `depth`, `retouch`, `compose`, `qa`). Todas as funções
são array → array (float32 sRGB 0–1; máscaras HxW 0–1).

## Contraluz em fundo claro (receita validada em dois trabalhos)

`fotoia contraluz` faz tudo de forma determinística — não precisa do modelo
generativo quando o fundo pedido é branco/claro de estúdio:

1. Fonte pequena (< ~2000 px no lado maior)? **Amplie primeiro**
   (`ampliar --lado 3840 --fidelidade 0.6`) e recorte a versão ampliada com
   `recortar --modelo birefnet-hr`: bordas e rim saem nítidos em 4K.
2. `contraluz ENTRADA SAIDA --alfa ALFA`. Ponto de partida: os padrões. Assunto
   escuro aguenta `--rim 5-6`; para mais drama `--escurecer -0.5 --contraste 0.4`.
3. `ajustar --nitidez 0.3` no fim e confira em zoom as bordas.

O que a função já resolve (não reintroduza estes defeitos ao improvisar):

- Larguras de rim/névoa/escurecimento seguem a **espessura local** do assunto;
  com largura fixa, dedos e braços finos ficam lavados.
- O ganho é reduzido em materiais claros; o mesmo ganho que acende um traje
  escuro estoura um vermelho vivo.
- O rim é multiplicativo (mantém a cor) **mais** um termo aditivo tingido pela
  cor local — só multiplicar deixa linha escura onde a borda está em sombra.
- A luz é aplicada na camada do assunto **antes** de compor; aplicada depois, a
  franja antialiasada não acende e sobra um fio colorido por fora do brilho.
- `bloom` global sobre fundo branco lava a imagem inteira — não use.
- Fundo vindo de imagem gerada: reconstrua-o sem o assunto (desfoque
  mascarado), senão fica um contorno fantasma em volta da silhueta.

## Elementos translúcidos que devem ficar (teia, véu, fumaça, vidro)

Eles contêm o fundo antigo, então não dá para recortar e colar. O que funcionou
(ver `editor-fotos/exemplos/teia_translucida.py`):

1. Região aproximada com `mascara --texto`.
2. Dentro dela, extraia só a estrutura fina e clara: top-hat de raio pequeno na
   luminância, menos o que for saturado/quente (luzes do fundo), vezes uma
   densidade em escala larga (só onde há trama de verdade).
3. Renderize contra o fundo novo como material em contraluz (cinza-prateado, véu
   suave, dissolvendo ao se afastar do assunto) e passe como `--fundo` do
   `contraluz`; o assunto é composto por cima.
4. Confira em zoom: grades regulares (janelas, cercas) passam pelo filtro e
   precisam de exclusão manual por coordenadas.

Pedir ao FLUX.2 klein para "manter a teia" preserva o lugar e a forma geral, mas
reinventa a textura (virou rede de malha regular nos dois testes). Use-o só se a
pessoa aceitar a reinterpretação.

## Relighting (`reluz`) — o que esperar

O modelo propõe a luz; só a razão suave de iluminação vai para o original.
Mudanças sutis e moderadas ficam muito boas. Em luz dramática (low-key,
Rembrandt) o resultado é mais suave que a proposta: use `--detalhe 0.005` e
salve `--proposta` para reaproveitar com `transferir-luz` sem rodar o modelo
de novo. Sombras duras e especulares finos não são transferidos (por desenho);
`--brilhos` recupera parte dos especulares.

## Limites desta máquina

- 4 vCPU com AMX, 15 GB de RAM, sem GPU. bfloat16 dá 4–8× sobre float32.
- FLUX.2 klein 4B: ~1 MP por passagem, 2–6 min cada. O codificador de texto e o
  transformer não cabem juntos na RAM; `flux.py` carrega um por vez.
  Com o cache de disco frio (primeira chamada da sessão, ou depois de rodar outro
  modelo grande) a leitura dos pesos é de ~30 MB/s: some 4–5 min por componente
  (codificador de texto a cada prompt novo, transformer a cada processo). Planeje
  os prompts para rodar o mínimo de passagens e avise a pessoa da espera.
- BiRefNet: ~25 s (1024) / ~90 s (HR 2048). SAM 2.1: ~5 s. LaMa: ~2 s.
  Real-ESRGAN x2 de 2 MP: ~30 s; x4 de 0,7 MP: ~80 s.
- Disco: ~39 GB por sessão. O conjunto essencial ocupa ~19,5 GB.
  `fotoia modelos --apagar <modelo>` libera espaço.
- O contêiner é efêmero: resultados em `saidas/` somem ao fim da sessão.
  Entregue sempre pelo chat.
- `luz --direcional` (normais estimadas da profundidade) é aproximado; prefira
  `reluz` quando a qualidade importar.

## Licenças

Uso comercial livre: FLUX.2 klein 4B (Apache-2.0), BiRefNet (MIT), SAM 2.1,
Grounding DINO, LaMa, Depth Anything V2 Small (Apache-2.0), Real-ESRGAN (BSD).
Atenção: `face-parsing` (treinado em CelebAMask-HQ, sem licença declarada) e
`depth-large` (CC-BY-NC) não são para trabalho comercial — avise se o pedido
depender deles.
