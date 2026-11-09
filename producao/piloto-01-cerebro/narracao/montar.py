"""Narração do piloto 01: pm_alex 0,9x frase a frase, pausas planejadas (amostra B).

Uso (na pasta do projeto): python3 narracao/montar.py
Lê narracao/frases.tsv e narracao/frases/fN.wav; grava narracao/narracao-bruta.wav e
narracao/frases.json (início e fim de cada frase, em segundos, dentro da narração).
"""
import json
import numpy as np
import soundfile as sf

linhas = [l.rstrip("\n").split("\t") for l in open("narracao/frases.tsv", encoding="utf-8")
          if l.strip() and not l.startswith("#")]
partes, mapa, t, sr = [], [], 0.0, None
for i, (cena, exibido, voz, pausa) in enumerate(linhas, 1):
    a, sr = sf.read(f"narracao/frases/f{i}.wav")
    a = a if a.ndim == 1 else a.mean(axis=1)
    lim = 10 ** (-45 / 20) * np.max(np.abs(a))
    idx = np.where(np.abs(a) > lim)[0]
    a = a[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)]
    mapa.append({"cena": int(cena), "texto": exibido, "inicio": round(t, 3), "fim": round(t + len(a) / sr, 3)})
    partes.append(a); t += len(a) / sr
    if i < len(linhas):
        partes.append(np.zeros(int(float(pausa) * sr))); t += float(pausa)
sf.write("narracao/narracao-bruta.wav", np.concatenate(partes), sr)
json.dump(mapa, open("narracao/frases.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"narração: {t:.2f} s, {len(linhas)} frases")
