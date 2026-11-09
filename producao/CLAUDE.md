# Produção de vídeos verticais (roteiro → MP4)

> **Leia primeiro `producao/CONTEXTO-DO-CANAL.md`**: a direção oficial do canal (nicho, 61 s,
> identidade visual, voz, edição, retenção, regras editoriais, etapas). Ela tem prioridade sobre
> esta receita, que é provisória, quando houver conflito.

A pessoa manda, pelo celular, um roteiro ou só uma ideia. A entrega é um MP4 vertical 1080×1920 com
narração pt-BR, cenas animadas, transições, legendas sincronizadas, trilha e efeitos sonoros.
Responda em português. Carregue `/hyperframes:hyperframes` (e `/hyperframes:media-use` para mídia)
antes de compor; as regras do skill valem aqui. `teste-15s/` é o exemplo de referência.

## Receita

1. **Roteiro.** Se veio só a ideia, escreva o roteiro: ~2,5 palavras por segundo de vídeo
   (15 s ≈ 38 palavras, 30 s ≈ 75), gancho na primeira frase, frases curtas, fecho com chamada.
   Mostre o roteiro em uma mensagem curta e siga (a pessoa pediu fluxo automático).
2. **Projeto.** `producao/ferramentas/novo-projeto.sh <nome> "<roteiro>"` (nunca reutilize uma pasta).
3. **Áudio.** `producao/ferramentas/preparar-audio.sh producao/<nome> --musica "<clima em inglês>"`.
   Gera narração (Kokoro `pf_dora`; `pm_alex` masculina), `assets/voice/transcript.json`,
   `compositions/legendas.html` e `assets/bgm/trilha.mp3` (narração em `assets/voice/narracao.mp3`), e imprime cada palavra com o tempo no vídeo.
   Confira a transcrição contra o roteiro (nomes, números) antes de seguir.
4. **Cenas.** Uma sub-composição por beat em `compositions/`, cortes ancorados nas palavras impressas.
   Copie a estrutura de `teste-15s/index.html`: fundo contínuo (track 0), cenas (track 1),
   `legendas` (track-kind captions, z-index acima), `<audio>` de narração (`data-start` = `--inicio`),
   narração a 0.8 e trilha a ~0.18 com fade (mix final perto de -14 LUFS), cada efeito com `data-duration` e trilha própria.
   `index.html` carrega `assets/vendor/gsap.min.js` (o CDN é bloqueado neste ambiente).
5. **Verificação.** `check --json` sem erros; `snapshot --at ...` e olhe os quadros; então `render`.
6. **Entrega.** `render --output renders/<nome>.mp4`, mande o arquivo com SendUserFile, meça o
   áudio com `audio <mp4> --json`, faça commit e push da pasta do projeto.

## Vertical (Reels/TikTok/Shorts)

- Texto e assunto entre y=168 e y=1330; abaixo de 1330 só textura. Legendas com base em `bottom: 640px`.
- Quadro 0 já mostra o gancho (é a miniatura). Novo beat a cada 2–4 s. Títulos ≥ 96 px, Inter (embutida).
- Títulos parados depois de pousar; o movimento contínuo vem do fundo. 3–5 tipos de transição,
  cada uma com causa na tela; efeitos só em ações visíveis (whoosh no corte, pop em selo/chip).
- Textos de apoio ficam ≥ 0,5 s + 0,3 s por palavra; o `check` avisa (`line_unread`).

## Ambiente (nuvem)

- Rode o CLI pelo plugin: `node /root/.claude/plugins/cache/hyperframes/hyperframes/<versão>/skills/hyperframes/scripts/plugin-cli.mjs`.
- Sempre `export NODE_USE_ENV_PROXY=1`, senão os downloads do Node falham com `ENOTFOUND`.
- Gratuito e local: voz Kokoro, legendas whisper `small --language pt`, trilha MusicGen (CPU, ~1 min por 15 s),
  efeitos do pacote do skill (licença Pixabay, sem atribuição obrigatória).
- Se o contêiner for novo e faltar `espeak-ng`, `kokoro-onnx` ou `torch`, o script de setup do
  ambiente instala; sem ele: `apt-get install -y espeak-ng cmake build-essential`,
  `pip3 install kokoro-onnx soundfile`,
  `pip3 install --index-url https://download.pytorch.org/whl/cpu torch`, `pip3 install transformers numpy`.
- Melhorias opcionais: login gratuito na HeyGen (`auth login`) dá vozes melhores com tempo por palavra,
  catálogo de músicas e busca de imagens; só use quando a pessoa pedir.
