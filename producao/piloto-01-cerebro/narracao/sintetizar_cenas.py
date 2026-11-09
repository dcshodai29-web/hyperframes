"""Narração do piloto 01, versão fluida: uma passada do Kokoro por cena.

Por que por cena: o Kokoro só divide o texto acima de 510 fonemas, então cada cena sai numa
passada só e o modelo entona as frases dela como um trecho contínuo, em vez de ler frase a frase.
O ponto fraco é que as frases de uma cena ficam coladas (o modelo deixa ~0,1 s); o passo
`pausas` alonga só as pausas de fim de frase, com o tempo de cada palavra medido pelo whisper.

Uso (na pasta do projeto):
  python3 narracao/sintetizar_cenas.py sintetizar   # narracao/cenas/cN-bruta.flac
  (transcrever cada cN-bruta.flac com `hyperframes transcribe`, ver refazer-audio.sh)
  python3 narracao/sintetizar_cenas.py pausas       # narracao/narracao-bruta.wav e palavras.json
"""

import json
import re
import sys
import difflib

import numpy as np
import soundfile as sf

VOZ = "pm_alex"
# Velocidade por cena: gancho e fecho um pouco mais lentos, desenvolvimento mais fluente.
VELOCIDADE = {1: 0.86, 2: 0.88, 3: 0.89, 4: 0.90, 5: 0.88, 6: 0.89, 7: 0.86, 8: 0.84}
# Pausa depois do fim de cada frase dentro da cena (s), variada para não soar mecânica.
PAUSA_FRASE = {1: [0.42], 3: [0.36], 4: [0.30, 0.38], 6: [0.40], 7: [0.33], 8: [0.46, 0.40]}
# Respiração entre uma cena e a seguinte (s).
PAUSA_CENA = {1: 0.72, 2: 0.62, 3: 0.70, 4: 0.66, 5: 0.74, 6: 0.82, 7: 0.70}
INICIO_NO_VIDEO = 0.10

norm = lambda s: re.sub(r"\W", "", s.lower())


def ler_frases():
    linhas = [l.rstrip("\n").split("\t") for l in open("narracao/frases.tsv", encoding="utf-8")
              if l.strip() and not l.startswith("#")]
    cenas = {}
    for cena, exibido, voz, _pausa in linhas:
        c = cenas.setdefault(int(cena), {"exibido": [], "voz": []})
        c["exibido"].append(exibido)
        c["voz"].append(voz)
    return cenas


def sintetizar():
    from kokoro_onnx import Kokoro

    k = Kokoro("/root/.cache/hyperframes/tts/models/kokoro-v1.0.onnx",
               "/root/.cache/hyperframes/tts/voices/voices-v1.0.bin")
    for n, c in ler_frases().items():
        texto = " ".join(c["voz"])
        audio, sr = k.create(texto, voice=VOZ, speed=VELOCIDADE[n], lang="pt-br")
        sf.write(f"narracao/cenas/c{n}-bruta.flac", audio, sr)
        print(f"cena {n}: {len(audio) / sr:.2f} s · {texto}")


def rms_quadros(a, sr, passo=0.01):
    n = int(passo * sr)
    m = len(a) // n * n
    return np.sqrt((a[:m].reshape(-1, n) ** 2).mean(1) + 1e-12), n


def alongar_pausa(a, sr, fim_palavra, inicio_prox, alvo):
    """Troca o silêncio entre duas frases por `alvo` segundos, cortando no trecho mais quieto."""
    rms, n = rms_quadros(a, sr)
    quieto = rms <= rms.max() * 10 ** (-38 / 20)
    i0 = max(0, int((fim_palavra - 0.08) / 0.01))
    i1 = min(len(rms) - 1, int((inicio_prox + 0.08) / 0.01))
    if i1 <= i0:
        i1 = i0 + 1
    janela = np.arange(i0, i1 + 1)
    calmos = janela[quieto[janela]]
    if len(calmos):
        # o maior trecho quieto contínuo dentro da janela
        grupos = np.split(calmos, np.where(np.diff(calmos) != 1)[0] + 1)
        g = max(grupos, key=len)
        ini, fim = g[0] * n, (g[-1] + 1) * n
    else:
        meio = janela[np.argmin(rms[janela])] * n
        ini, fim = meio, meio
    atual = (fim - ini) / sr
    silencio = np.zeros(int(alvo * sr), dtype=a.dtype)
    rampa = int(0.008 * sr)
    esq, dir_ = a[:ini].copy(), a[fim:].copy()
    if len(esq) > rampa:
        esq[-rampa:] *= np.linspace(1, 0, rampa)
    if len(dir_) > rampa:
        dir_[:rampa] *= np.linspace(0, 1, rampa)
    return np.concatenate([esq, silencio, dir_]), ini / sr, alvo - atual


def alinhar(exibido, whisper):
    alvo = " ".join(exibido).split()
    w = [x for x in whisper if re.search(r"\w", x["text"])]
    sm = difflib.SequenceMatcher(None, [norm(s) for s in alvo], [norm(x["text"]) for x in w],
                                 autojunk=False)
    tempos, difs = [None] * len(alvo), []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            difs.append((" ".join(alvo[i1:i2]), " ".join(x["text"] for x in w[j1:j2])))
        if j2 > j1:
            a0, b0 = w[j1]["start"], w[j2 - 1]["end"]
            tot = sum(len(alvo[k]) for k in range(i1, i2)) or 1
            t = a0
            for k in range(i1, i2):
                d = (b0 - a0) * len(alvo[k]) / tot
                tempos[k] = [t, t + d]
                t += d
    for k in range(len(alvo)):  # palavra sem par (whisper engoliu): entre as vizinhas
        if tempos[k] is None:
            ant = tempos[k - 1][1] if k > 0 and tempos[k - 1] else 0.0
            prox = next((tempos[j][0] for j in range(k + 1, len(alvo)) if tempos[j]), ant + 0.3)
            tempos[k] = [ant, max(ant + 0.05, prox)]
    return alvo, tempos, difs


def pausas():
    cenas = ler_frases()
    partes, palavras, mapa, t_global = [], [], {}, 0.0
    sr = None
    for n, c in cenas.items():
        a, sr = sf.read(f"narracao/cenas/c{n}-bruta.flac")
        a = a if a.ndim == 1 else a.mean(axis=1)
        whisper = json.load(open(f"narracao/cenas/c{n}-transcript.json", encoding="utf-8"))
        alvo, tempos, difs = alinhar(c["exibido"], whisper)
        if difs:
            print(f"  cena {n}: diferenças de escrita do whisper {difs}")
        # índices das palavras que fecham frase (exceto a última da cena)
        fins = [i for i, w in enumerate(alvo[:-1]) if re.search(r"[.?!…]$", w)]
        alvos = PAUSA_FRASE.get(n, [])
        for j, i in enumerate(reversed(fins)):  # de trás para frente: os tempos anteriores não mudam
            alvo_s = alvos[len(fins) - 1 - j] if len(alvos) == len(fins) else 0.36
            a, corte, delta = alongar_pausa(a, sr, tempos[i][1], tempos[i + 1][0], alvo_s)
            for k in range(i + 1, len(alvo)):
                tempos[k] = [tempos[k][0] + delta, tempos[k][1] + delta]
        sf.write(f"narracao/cenas/c{n}.flac", a, sr)
        dur = len(a) / sr
        mapa[n] = [round(t_global + INICIO_NO_VIDEO, 3), round(t_global + dur + INICIO_NO_VIDEO, 3)]
        for w, (s, e) in zip(alvo, tempos):
            palavras.append({"text": w, "start": round(t_global + s + INICIO_NO_VIDEO, 3),
                             "end": round(t_global + min(e, dur) + INICIO_NO_VIDEO, 3), "cena": n})
        partes.append(a)
        t_global += dur
        if n in PAUSA_CENA:
            partes.append(np.zeros(int(PAUSA_CENA[n] * sr)))
            t_global += PAUSA_CENA[n]
    for k, p in enumerate(palavras):
        p["id"] = f"w{k}"
    sf.write("narracao/narracao-bruta.wav", np.concatenate(partes), sr)
    json.dump(palavras, open("narracao/palavras.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"fala": mapa}, open("narracao/cenas-fala.json", "w"), indent=1)
    total = palavras[-1]["end"]
    print(f"narração: {t_global:.2f} s · fala termina em {total:.2f} s no vídeo · "
          f"{len(palavras)} palavras · {len(palavras) / (t_global):.2f} palavras/s")


if __name__ == "__main__":
    {"sintetizar": sintetizar, "pausas": pausas}[sys.argv[1]]()
