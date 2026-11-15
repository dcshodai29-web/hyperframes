# Editor de fotos por IA

Toolkit usado pelo Claude para editar fotografias a pedido, sem interface: a
pessoa envia a foto e descreve a edição; o agente executa e devolve o arquivo.
As instruções de operação do agente estão em
`.claude/skills/editor-fotos/SKILL.md`.

## Instalação

```bash
bash editor-fotos/setup.sh            # ambiente Python (PyTorch CPU, Diffusers, OpenCV…)
bash editor-fotos/setup.sh --modelos  # opcional: pré-baixa o conjunto essencial (~19 GB)
```

`bin/fotoia` instala o ambiente sozinho se ele não existir. Os modelos são
baixados na primeira vez que um comando precisa deles.

## Uso

```bash
editor-fotos/bin/fotoia job foto.jpg                  # pasta de trabalho + cópia intocável
editor-fotos/bin/fotoia recortar foto.jpg alfa.png
editor-fotos/bin/fotoia fundo foto.jpg saida.jpg --alfa alfa.png --prompt "a marble counter, soft window light"
editor-fotos/bin/fotoia reluz foto.jpg saida.jpg --luz rembrandt
editor-fotos/bin/fotoia ajustar foto.jpg saida.jpg --contraste 0.2 --claridade 0.3 --nitidez 0.5
editor-fotos/bin/fotoia ampliar foto.jpg saida.jpg --lado 3840
editor-fotos/bin/fotoia modelos                       # modelos, licenças e espaço em disco
```

`fotoia -h` lista todos os comandos; `fotoia <comando> -h` as opções.

## Estrutura

| Módulo          | Função                                                                                                         |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| `core.py`       | E/S com gestão de cor (EXIF, ICC, 16 bits, HEIC, RAW), espaço linear, pastas de trabalho, proteção do original |
| `models.py`     | registro de modelos, licenças e download sob demanda                                                           |
| `segment.py`    | BiRefNet (assunto), SAM 2.1 (ponto/caixa), Grounding DINO (texto), rosto, máscaras                             |
| `flux.py`       | FLUX.2 klein 4B em CPU: gerar, editar, repintar com geometria travada                                          |
| `light.py`      | transferência de luz preservando textura, relighting, rim light                                                |
| `background.py` | fundos procedurais, sombra, reflexo, composição, cenário por IA                                                |
| `inpaint.py`    | remoção (LaMa) e preenchimento generativo                                                                      |
| `upscale.py`    | Real-ESRGAN / DAT2 em blocos, rostos (GFPGAN), refino por ControlNet tile                                      |
| `enhance.py`    | exposição, cor, contraste, claridade, textura, nitidez, gradação, acabamento                                   |
| `retouch.py`    | retoque de retrato por separação de frequências                                                                |
| `depth.py`      | profundidade e bokeh                                                                                           |
| `compose.py`    | recorte por proporção e expansão de tela                                                                       |
| `qa.py`         | análise, verificação de preservação e folhas de comparação                                                     |

`entradas/` e `saidas/` ficam fora do git.
