# Teste de viabilidade: cena 1 do piloto 01 (olho humano)

Direção visual decidida pela pessoa: sistema híbrido de 3D cinematográfico. Este teste avalia a
viabilidade antes da implementação. Nada foi instalado, o pipeline não mudou e o piloto não foi
renderizado. Projeto do teste: `producao/teste-viabilidade-cena1/` (render em
`renders/teste-cena1.mp4`, fora do Git).

## O que foi testado

A cena 1 (0–4,2 s) feita **só com recursos locais**: um shader WebGL escrito à mão, sem
bibliotecas nem imagens, desenhando um macro de olho com íris procedural (fibras, colarete,
criptas, anel límbico), reflexo de janela na córnea, película úmida, luz lateral quente com rim
azul elétrico, poeira fora de foco, feixes de luz, profundidade de campo simulada, tom fílmico e
granulação. Por cima: texto do gancho, o buraco preto em "Agora mesmo", trecho real da narração,
trilha e impacto grave.

### Resultado

- **Funciona bem:** a íris (detalhe orgânico convincente), o push-in contínuo, o buraco recortando
  a imagem, a luz e a granulação. Com a câmera fechada no globo, a cena funciona como motion design
  de qualidade.
- **Não alcança o padrão "cinematográfico realista":** o olho se lê como computação gráfica. O
  padrão da íris é regular e limpo demais, o reflexo da janela é geométrico e a esclera não tem a
  complexidade de um tecido real. Na primeira versão, pálpebras, pele e cílios procedurais ficaram
  chapados; a solução foi enquadrar só o globo, o que esconde o problema, mas não o resolve.
- **Render:** 56 s para 4,2 s (126 quadros), ~0,44 s por quadro neste contêiner sem GPU. Um vídeo
  de 61 s inteiramente nesse nível de shader levaria ~14 min para renderizar.
- **Arquivo:** 24,5 MB em 4,2 s, porque a granulação encarece a compressão; ajustar granulação ou
  taxa de bits no render final.

Conclusão: o procedural local serve para **elementos técnicos e gráficos**, mas não para
**anatomia, animais e ambientes com aparência real**, exatamente como a arquitetura híbrida prevê.

## Técnica recomendada para a cena 1

**Placa gerada externamente + camada técnica local:**

1. **Imagem-chave** gerada externamente: macro fotorrealista de um olho humano, íris de cor
   natural, luz lateral quente e rim azul, fundo escuro, sem texto. Gerar 3–4 opções e escolher.
2. **Tomada de vídeo** de 5 s gerada a partir dessa imagem como primeiro quadro, com prompt de
   "push-in lento, macro, profundidade de campo rasa".
3. **Em HyperFrames, localmente:** texto do gancho, o buraco (máscara procedural que acompanha o
   push-in), poeira e feixes de luz em WebGL por cima, grade de cor da marca via
   `hyperframes media-treatment`, legendas, som.
4. **Loop:** a mesma imagem-chave é o quadro 0 e o último quadro da cena 8. Como é o mesmo
   arquivo, a correspondência é exata.

## Ferramentas e dependências

| Necessidade                                                                 | Ferramenta                                                                                       | Situação                                                               |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Composição, texto, legendas, máscaras, render                               | HyperFrames CLI 0.9.26                                                                           | Já instalado                                                           |
| Shaders e efeitos científicos sem biblioteca                                | WebGL nativo do Chrome                                                                           | Já disponível (usado neste teste)                                      |
| 3D com geometria, materiais PBR e modelos (relógio, cérebro, partículas 3D) | Three.js                                                                                         | Não instalado: seria um arquivo copiado para cada projeto, como o GSAP |
| Modelos 3D prontos (anatomia, animais)                                      | Bibliotecas de modelos com licença de uso                                                        | A definir; cada modelo precisa de licença compatível com monetização   |
| Imagens e vídeos fotorrealistas                                             | `hyperframes media-use generate` (HeyGen: imagens nano-banana / gpt-image, vídeo heygen-video-1) | Precisa de login HeyGen (`auth login`) e créditos                      |
| Grade de cor consistente em material gerado                                 | `hyperframes media-treatment`                                                                    | Já disponível                                                          |

## Local × externo

**Local, neste contêiner (CPU, sem GPU):**

- composição, tipografia, legendas, transições, máscaras, render final;
- shaders WebGL: partículas, feixes, poeira, diagramas, campos de dados, retina estilizada,
  campos visuais, medidor de sensibilidade, mosaico da revelação;
- Three.js (depois de copiado): relógio 3D, objetos técnicos, câmera 3D, partículas 3D;
- narração (Kokoro), legendas (whisper), trilha (MusicGen), efeitos do pacote embutido.

Geração de imagem ou vídeo por IA **localmente não é viável aqui**: o contêiner não tem GPU, e os
geradores locais suportados pelo skill exigem Apple Silicon (FLUX/mflux) ou GPU (LTX).

**Externo (créditos):**

- planos fotorrealistas: olho (cenas 1 e 8), paisagem (cena 3), relógio realista se o Three.js não
  bastar (cena 5), quadra e gorila (cena 6), cabeça e cérebro (cena 7).

## Custo e tempo (estimativas)

Preços da rota HyperFrames/HeyGen, conforme a referência do skill `media-use` (rota com chave de
API; com login, o plano cobra os próprios créditos):

| Item                                                              | Preço de referência           |
| ----------------------------------------------------------------- | ----------------------------- |
| Imagem (nano-banana-2)                                            | US$ 0,067 por imagem          |
| Vídeo heygen-video-1, 768p, a partir de prompt ou primeiro quadro | US$ 0,02 por segundo          |
| O mesmo em 1080p                                                  | cerca de US$ 0,04 por segundo |
| Vídeo com imagem de referência                                    | US$ 0,05 por segundo          |

**Cena 1:** 4 imagens-chave (US$ 0,27) + 3 tentativas de 5 s em 1080p (US$ 0,60) ≈ **US$ 1**.

**Vídeo de 61 s no modelo híbrido:** cerca de 5 tomadas geradas de 5–8 s (cenas 1, 3, 6, 7 e a volta
da 8), com ~3 tentativas cada, mais ~15 imagens: **cerca de US$ 5 a 10 por vídeo**. As cenas 2, 4 e 5
e os efeitos ficam locais, sem custo de geração.

Tempo de produção, com o sistema montado:

| Etapa                                                        | Primeiro vídeo | Vídeos seguintes                   |
| ------------------------------------------------------------ | -------------- | ---------------------------------- |
| Roteiro, checagem e narração                                 | 1–2 h          | 1 h                                |
| Imagens e tomadas geradas (inclui escolher entre tentativas) | 1–2 h          | 1 h                                |
| Cenas locais (shaders, Three.js, composição)                 | 4–8 h          | 1–3 h, reaproveitando a biblioteca |
| Verificação, mixagem e render                                | 1 h            | 30–45 min                          |

O primeiro vídeo custa mais porque cria a biblioteca (luz, partículas, grão, tom, transições,
legendas). Estimativas de trabalho do agente; o tempo de fila dos geradores externos não está incluído.

## Consistência visual entre os vídeos

1. **Bíblia de estilo SCIENCE CINEMATIC** num arquivo do projeto: paleta, esquema de luz (key
   quente à esquerda, rim azul elétrico à direita, fundo `#080B12`), lente (macro, profundidade de
   campo rasa), nível de granulação, curva de tom, tipografia e legendas.
2. **Prompt-base fixo** para toda geração externa: o mesmo sufixo de estilo, luz e lente, sem texto
   nem logos, e as mesmas imagens de referência (frames aprovados de vídeos anteriores) passadas como
   `--reference`.
3. **Grade de cor única** aplicada a todo material gerado por `hyperframes media-treatment` (uma LUT
   da marca), preservando cores naturais e evitando azular tudo.
4. **Biblioteca local reutilizável** de shaders e componentes: poeira, feixes, grão, tom fílmico,
   partículas, máscaras, transições e legendas, versionada no repositório.
5. **Revisão por quadros** com o `snapshot` contra frames de referência aprovados antes de cada render.

## Decisões necessárias para implementar

1. Aprovar a técnica recomendada para a cena 1 (placa gerada + camada local).
2. Login HeyGen (`! npx hyperframes auth login`) e definir um limite de créditos para o projeto.
3. Autorizar copiar o Three.js para os projetos (sem instalar nada no sistema).
4. Aprovar ou ajustar a bíblia de estilo antes do primeiro vídeo.
