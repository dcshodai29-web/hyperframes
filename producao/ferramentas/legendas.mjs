#!/usr/bin/env node
// Gera compositions/legendas.html (legendas palavra a palavra, estilo destaque)
// a partir do transcript.json do `hyperframes transcribe`.
//
// Uso: node legendas.mjs <transcript.json> <saida.html> --offset 0.3 --duracao 15
//        [--largura 1080 --altura 1920 --base 640 --cor "#6D4AFF" --palavras 3]
//
// Cada grupo (até 3 palavras) e cada palavra são escritos no HTML com id estável,
// para o Studio conseguir editar; o timeline só anima o que já está na página.

import { readFileSync, writeFileSync } from "node:fs";

const argv = process.argv.slice(2);
const flag = (name, def) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : def;
};
const [entrada, saida] = argv.filter(
  (a, i) => !a.startsWith("--") && !argv[i - 1]?.startsWith("--"),
);
if (!entrada || !saida) {
  console.error("uso: node legendas.mjs <transcript.json> <saida.html> --offset 0.3 --duracao 15");
  process.exit(1);
}

const offset = Number(flag("offset", "0"));
const duracao = Number(flag("duracao", "15"));
const largura = Number(flag("largura", "1080"));
const altura = Number(flag("altura", "1920"));
const base = Number(flag("base", "640")); // distância da borda inferior até a base da legenda
const cor = flag("cor", "#6D4AFF"); // texto branco sobre ele: contraste 5,6:1
const maxPalavras = Number(flag("palavras", "3"));

const escape = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const r3 = (n) => Math.round(n * 1000) / 1000;

// Remove tokens que não são palavras (♪, �, vazios) e desloca pelo início da narração.
const palavras = JSON.parse(readFileSync(entrada, "utf8"))
  .filter((w) => typeof w.text === "string" && /[\p{L}\p{N}]/u.test(w.text))
  .map((w) => ({ text: w.text.trim(), start: w.start + offset, end: w.end + offset }));

// Agrupa: quebra em pontuação, pausa >= 150 ms ou no limite de palavras.
const grupos = [];
let atual = [];
palavras.forEach((w, i) => {
  atual.push(w);
  const prox = palavras[i + 1];
  const pontuacao = /[.?!,:;]$/.test(w.text);
  const pausa = prox ? prox.start - w.end >= 0.15 : true;
  if (!prox || pontuacao || pausa || atual.length >= maxPalavras) {
    grupos.push(atual);
    atual = [];
  }
});

let fimAnterior = 0;
const blocos = grupos.map((g, gi) => {
  const prox = grupos[gi + 1];
  const inicio = Math.max(0.1, fimAnterior, g[0].start - 0.05);
  const fimIdeal = g[g.length - 1].end + 0.35;
  const fim = Math.min(fimIdeal, prox ? prox[0].start - 0.03 : duracao - 0.05, duracao - 0.05);
  fimAnterior = fim;
  return { palavras: g, inicio: r3(inicio), fim: r3(Math.max(fim, inicio + 0.2)) };
});

let wi = 0;
const html = blocos
  .map((b, gi) => {
    const spans = b.palavras
      .map((w) => {
        const id = `lg-w${wi++}`;
        return `      <span class="lg-palavra" id="${id}"><span class="lg-fundo" id="${id}-f"></span><span class="lg-texto" id="${id}-t">${escape(w.text.toUpperCase())}</span></span>`;
      })
      .join("\n");
    return `    <div class="lg-grupo" id="lg-g${gi}">\n${spans}\n    </div>`;
  })
  .join("\n");

wi = 0;
const tweens = blocos
  .map((b, gi) => {
    const linhas = [
      `    tl.set("#lg-g${gi}", { visibility: "visible" }, ${b.inicio});`,
      `    tl.fromTo("#lg-g${gi}", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.16, ease: "power3.out" }, ${b.inicio});`,
    ];
    b.palavras.forEach((w) => {
      const id = `lg-w${wi++}`;
      const s = r3(w.start);
      // A saída do destaque nunca começa antes da entrada terminar (0.14 s).
      const e = r3(Math.max(s + 0.15, Math.min(w.end, b.fim - 0.14)));
      linhas.push(
        `    tl.fromTo("#${id}-f", { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 0.14, ease: "power3.out" }, ${s});`,
        `    tl.to("#${id}-f", { opacity: 0, duration: 0.1, ease: "power2.in" }, ${e});`,
      );
    });
    linhas.push(
      `    tl.to("#lg-g${gi}", { opacity: 0, duration: 0.12, ease: "power2.in" }, ${r3(b.fim - 0.12)});`,
      `    tl.set("#lg-g${gi}", { opacity: 0, visibility: "hidden" }, ${b.fim});`,
    );
    return linhas.join("\n");
  })
  .join("\n");

const doc = `<template>
  <style>
    #root {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }
    .lg-grupo {
      position: absolute;
      left: 0;
      bottom: ${base}px;
      width: ${largura}px;
      padding: 0 110px;
      box-sizing: border-box;
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      align-items: flex-end;
      gap: 6px 10px;
      overflow: visible;
      opacity: 0;
      visibility: hidden;
    }
    .lg-palavra {
      position: relative;
      display: inline-block;
      padding: 6px 14px 10px;
      font-family: "Inter", sans-serif;
      font-weight: 900;
      font-size: 66px;
      line-height: 1;
      letter-spacing: 0.01em;
      text-shadow: 0 4px 16px rgba(0, 0, 0, 0.55);
    }
    .lg-fundo {
      position: absolute;
      inset: 0;
      border-radius: 12px;
      background: ${cor};
      transform-origin: 0% 50%;
      opacity: 0;
    }
    .lg-texto {
      position: relative;
      color: #ffffff;
    }
  </style>
  <div id="root" data-composition-id="legendas" data-width="${largura}" data-height="${altura}">
${html}
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
${tweens}
    window.__timelines["legendas"] = tl;
  </script>
</template>
`;

writeFileSync(saida, doc);
console.log(`[legendas] ${blocos.length} grupos, ${palavras.length} palavras → ${saida}`);
