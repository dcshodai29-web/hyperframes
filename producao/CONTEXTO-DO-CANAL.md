# Contexto oficial do projeto: canal de Ciência e Curiosidades

Direção oficial do projeto, definida pela pessoa (versão 2, 2026-11-09; substitui a versão 1 do
mesmo dia). Vale para todas as etapas seguintes e tem prioridade sobre `CLAUDE.md`, sobre os
padrões dos scripts em `ferramentas/` e sobre o exemplo `teste-15s/` quando houver conflito
(ver "Conflitos conhecidos" no fim).

**Status:** diretrizes registradas. O projeto evolui por etapas: não implementar funcionalidades,
alterar o pipeline, instalar dependências nem modificar os vídeos de teste sem instrução explícita
da pessoa. Aguardar as próximas instruções.

## 1. Objetivo

Construir um sistema de produção de vídeos curtos para TikTok e YouTube Shorts, priorizando
crescimento, monetização, originalidade e retenção de audiência.

## 2. Nicho

Ciência e curiosidades, com três pilares:

- Corpo humano.
- Universo e espaço.
- Mistérios da natureza.

## 3. Duração e formato

- Duração obrigatória do vídeo original: **exatamente 61 segundos**.
- TikTok: versão de 61 s.
- YouTube Shorts: versão de 60 s; a pessoa remove o último segundo no CapCut.
- Resolução: 1080 × 1920.
- Proporção: 9:16.
- Taxa de quadros: 30 fps.

Todos os roteiros e projetos são planejados para essa duração.

## 4. Identidade visual: SCIENCE CINEMATIC (nome provisório)

Paleta:

| Cor            | Hex       |
| -------------- | --------- |
| Preto profundo | `#080B12` |
| Azul elétrico  | `#1769FF` |
| Ciano          | `#00D9FF` |
| Branco         | `#F5F7FA` |
| Cinza          | `#929BAA` |

Estética:

- Animações 3D cinematográficas.
- Simulações científicas.
- Iluminação dramática e volumétrica.
- Profundidade de campo.
- Movimentos de câmera.
- Cenas visualmente impactantes.
- Elementos gráficos modernos.

Preservar as cores naturais dos elementos retratados quando fizer sentido. Não aplicar filtros
azuis indiscriminadamente.

Imagens realistas não são obrigatórias: 3D, animação, ilustração e reconstruções visuais servem.

## 5. Narração

- Voz masculina.
- Grave, natural e expressiva.
- Transmitir autoridade e curiosidade.
- Evitar entonação robótica.

## 6. Direção de edição: RETENTION CINEMATIC (nome provisório)

- Abertura imediata, sem vinheta.
- Gancho forte nos primeiros três segundos.
- Mudanças visuais com propósito narrativo.
- Alternância de enquadramentos e movimentos de câmera.
- Zooms e aproximações pontuais.
- Transições coerentes com a história.
- Legendas sincronizadas.
- Tipografia moderna, branca e em negrito.
- Palavras importantes destacadas em ciano.
- Trilha cinematográfica instrumental.
- Efeitos sonoros discretos e sincronizados.
- A voz permanece em primeiro plano.

## 7. Princípio de retenção

**CURIOSIDADE → EXPECTATIVA → DESCOBERTA → RECOMPENSA.**

Os vídeos despertam interesse genuíno, apresentam informações progressivamente e entregam uma
conclusão satisfatória.

Referência de distribuição dos 61 segundos (flexível; nunca à custa da qualidade da narrativa):

| Tempo   | Parte                     |
| ------- | ------------------------- |
| 0–3 s   | Gancho                    |
| 3–12 s  | Curiosidade e contexto    |
| 12–30 s | Desenvolvimento           |
| 30–45 s | Aprofundamento e surpresa |
| 45–56 s | Revelação principal       |
| 56–61 s | Conclusão                 |

## 8. Regras editoriais

- Não utilizar introduções demoradas.
- Não utilizar suspense artificial.
- Não inventar fatos científicos.
- Não repetir cenas sem necessidade.
- Não utilizar efeitos visuais sem propósito.
- Não prolongar roteiros artificialmente.
- Priorizar informações verificáveis e roteiros originais.

## 9. Ainda não definido (não inventar nem decidir antecipadamente)

- Nome definitivo do canal.
- Logotipo.
- Identidade de marca completa.
- Modelo definitivo de animação.
- Ferramentas externas de geração de imagens e vídeos.
- Pipeline definitivo de produção.

O fluxo atual (`CLAUDE.md` e `ferramentas/`) é provisório até a pessoa definir o pipeline.

## Conflitos conhecidos com a configuração atual

Registrados para não serem seguidos por engano; nada disso foi alterado, por instrução da pessoa.

- **Voz:** `ferramentas/preparar-audio.sh` usa por padrão `pf_dora` (feminina). A única voz
  masculina pt-BR instalada é `pm_alex` (Kokoro), que pode não atingir o "natural, sem entonação
  robótica" exigido.
- **Duração:** o script calcula a duração pela fala (fala + 2,2 s) quando `--duracao` não é
  passado; o padrão do projeto é 61 s fixos. A receita em `CLAUDE.md` cita exemplos de 15 e 30 s.
- **Legendas:** `ferramentas/legendas.mjs` destaca a palavra falada com fundo violeta `#6D4AFF`;
  a direção pede tipografia branca em negrito com palavras importantes em ciano `#00D9FF`.
- **Trilha:** o prompt padrão da música é lo-fi; a direção pede trilha cinematográfica instrumental.
- **Visual de referência:** `teste-15s/` usa paleta noturna azul-marinho e âmbar, ilustração plana
  2D e outro tema (sono), não a SCIENCE CINEMATIC.
- **Processo:** a receita em `CLAUDE.md` diz para mostrar o roteiro e seguir direto; as diretrizes
  pedem evolução por etapas, com decisões da pessoa.
