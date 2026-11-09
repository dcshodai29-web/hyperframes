"""Legendas do piloto 01 no estilo RETENTION CINEMATIC.

Branco em negrito, palavras-chave em ciano, palavra a palavra: o grupo aparece com as palavras
ainda em cinza e cada uma acende no instante em que é falada.

Uso (na pasta do projeto): python3 narracao/gerar_legendas.py
Lê narracao/palavras.json (tempos já no relógio do vídeo) e grava compositions/legendas.html.
"""
import json
import re

DURACAO = 61.0
BASE = 640  # distância da borda inferior até a base da legenda (faixa segura do 9:16)
BRANCO, CIANO, CINZA = "#F5F7FA", "#00D9FF", "#929BAA"
CHAVES = ["buraco", "preenche", "três vezes", "sensibilidade", "primeiro segundo",
          "quase metade", "gorila", "versão"]

norm = lambda s: re.sub(r"[^\wà-ú]", "", s.lower())
LIGACAO = {"a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "e", "em", "no",
           "na", "com", "que", "até", "por", "para"}
palavras = json.load(open("narracao/palavras.json", encoding="utf-8"))
# A primeira frase ("Existe um buraco na sua visão.") já está na tela como título do gancho da
# cena 1; legendá-la de novo repetiria o texto. As legendas começam em "Agora mesmo".
PULAR_ATE = next(i for i, p in enumerate(palavras) if re.search(r"[.?!]$", p["text"])) + 1
palavras = palavras[PULAR_ATE:]

# Marca as palavras que fazem parte de uma palavra-chave (inclusive as de duas palavras).
for i in range(len(palavras)):
    for chave in CHAVES:
        partes = chave.split()
        trecho = [norm(p["text"]) for p in palavras[i:i + len(partes)]]
        if trecho == partes:
            for p in palavras[i:i + len(partes)]:
                p["chave"] = True
                p["frase_chave"] = i  # mesma palavra-chave: nunca separar em grupos diferentes

# Grupos: cada oração (trecho até vírgula ou ponto) vira 1 grupo se tiver até 4 palavras; senão é
# repartida em grupos equilibrados de 2 a 4 palavras. Um limite nunca cai depois de palavra de
# ligação nem dentro de uma palavra-chave de duas palavras.
def oracoes(ps):
    atual = []
    for p in ps:
        atual.append(p)
        if re.search(r"[.?!,:;]$", p["text"]):
            yield atual
            atual = []
    if atual:
        yield atual


def corte_ruim(o, k):  # cortar antes do índice k da oração o
    a, b = o[k - 1], o[k]
    mesma_chave = "frase_chave" in a and a.get("frase_chave") == b.get("frase_chave")
    return mesma_chave or norm(a["text"]) in LIGACAO


def repartir(o):
    """Testa todas as divisões da oração em grupos de 1 a 4 palavras e fica com a de menor custo:
    corte depois de palavra de ligação ou dentro de palavra-chave pesa muito; grupo de 1 palavra
    pesa (exceto se a oração inteira tiver 1); grupos perto de 3 palavras são preferidos."""
    n = len(o)
    if n <= 4:
        return [o]
    melhor = None

    def busca(k, cortes):
        nonlocal melhor
        if k == n:
            tamanhos = [b - a for a, b in zip([0] + cortes[:-1], cortes)]
            custo = sum(100 for c in cortes[:-1] if corte_ruim(o, c))
            custo += sum(30 for t in tamanhos if t == 1)
            custo += sum((t - 3) ** 2 for t in tamanhos) + 2 * len(tamanhos)
            if melhor is None or custo < melhor[0]:
                melhor = (custo, cortes[:])
            return
        for t in range(1, 5):
            if k + t <= n:
                busca(k + t, cortes + [k + t])

    busca(0, [])
    limites = [0] + melhor[1]
    return [o[a:b] for a, b in zip(limites, limites[1:])]


grupos = [g for o in oracoes(palavras) for g in repartir(o)]

r3 = lambda x: round(x, 3)
html, js, fim_anterior = [], [], 0.0
for gi, g in enumerate(grupos):
    prox = grupos[gi + 1] if gi + 1 < len(grupos) else None
    inicio = max(0.1, fim_anterior, g[0]["start"] - 0.06)
    fim = min(g[-1]["end"] + 0.35, prox[0]["start"] - 0.04 if prox else DURACAO, DURACAO - 0.05)
    fim = max(fim, inicio + 0.25)
    fim_anterior = fim
    spans = "".join(
        f'<span class="lg-p{" lg-chave" if p.get("chave") else ""}" id="lg-{p["id"]}">{p["text"].upper()}</span>'
        for p in g
    )
    html.append(f'    <div class="lg-grupo" id="lg-g{gi}">{spans}</div>')
    js.append(f'    tl.set("#lg-g{gi}", {{ visibility: "visible" }}, {r3(inicio)});')
    js.append(f'    tl.fromTo("#lg-g{gi}", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.14, ease: "power3.out" }}, {r3(inicio)});')
    for p in g:
        cor = CIANO if p.get("chave") else BRANCO
        js.append(f'    tl.fromTo("#lg-{p["id"]}", {{ color: "{CINZA}" }}, {{ color: "{cor}", duration: 0.08, ease: "power2.out" }}, {r3(p["start"])});')
    js.append(f'    tl.to("#lg-g{gi}", {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {r3(fim - 0.12)});')
    js.append(f'    tl.set("#lg-g{gi}", {{ opacity: 0, visibility: "hidden" }}, {r3(fim)});')

doc = f"""<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      pointer-events: none;
    }}
    .lg-grupo {{
      position: absolute;
      left: 0;
      right: 0;
      margin: 0 auto;
      bottom: {BASE}px;
      width: max-content;
      max-width: 880px;
      padding: 8px 24px 12px;
      border-radius: 18px;
      background: rgba(8, 11, 18, 0.46);
      box-sizing: border-box;
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 4px 18px;
      opacity: 0;
      visibility: hidden;
    }}
    .lg-p {{
      font-family: "Inter", sans-serif;
      font-weight: 900;
      font-size: 64px;
      line-height: 1.08;
      letter-spacing: 0.005em;
      color: {CINZA};
      text-shadow: 0 3px 14px rgba(0, 0, 0, 0.7);
    }}
  </style>
  <div id="root" data-composition-id="legendas" data-width="1080" data-height="1920">
{chr(10).join(html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
    window.__timelines["legendas"] = tl;
  </script>
</template>
"""
open("compositions/legendas.html", "w", encoding="utf-8").write(doc)
print(f"legendas: {len(grupos)} grupos, {len(palavras)} palavras, "
      f"{sum(1 for p in palavras if p.get('chave'))} em ciano")
