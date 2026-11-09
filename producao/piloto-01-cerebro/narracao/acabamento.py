"""Acabamento da narração: um ambiente de sala bem discreto antes da equalização.

A voz sintética sai seca e "digital"; um pouco de sala (reflexões curtas, cauda de ~0,25 s,
bem abaixo da voz) faz soar gravada. Depois, `refazer-audio.sh` equaliza, comprime e normaliza.

Uso (na pasta do projeto): python3 narracao/acabamento.py
Lê narracao/narracao-bruta.wav e grava narracao/narracao-sala.wav.
"""

import numpy as np
import soundfile as sf

MOLHADO = 0.07   # nível da sala em relação à voz (~ -23 dB): sente-se, não se ouve
RT60 = 0.24      # segundos até a cauda cair 60 dB
PRE_DELAY = 0.012

x, sr = sf.read("narracao/narracao-bruta.wav")
x = x if x.ndim == 1 else x.mean(axis=1)

# Resposta ao impulso sintética e determinística: reflexões iniciais + cauda exponencial filtrada.
rng = np.random.default_rng(7)
n = int(0.5 * sr)
t = np.arange(n) / sr
cauda = rng.standard_normal(n) * np.exp(-6.9 * t / RT60)
# passa-baixas simples (média móvel) para a cauda não chiar
k = max(1, int(sr / 4500))
cauda = np.convolve(cauda, np.ones(k) / k, mode="same")
ir = np.zeros(n + int(PRE_DELAY * sr))
ir[int(PRE_DELAY * sr):] = cauda
for atraso, ganho in ((0.007, 0.5), (0.013, 0.35), (0.021, 0.25)):
    ir[int(atraso * sr)] += ganho
ir /= np.sqrt((ir ** 2).sum())

# convolução por FFT
m = len(x) + len(ir) - 1
tam = 1 << (m - 1).bit_length()
sala = np.fft.irfft(np.fft.rfft(x, tam) * np.fft.rfft(ir, tam), tam)[:len(x)]
sala *= np.sqrt((x ** 2).mean()) / max(np.sqrt((sala ** 2).mean()), 1e-9)
y = x + MOLHADO * sala
y /= max(1.0, np.abs(y).max() / 0.98)
sf.write("narracao/narracao-sala.wav", y.astype(np.float32), sr)
print(f"sala aplicada: {len(y) / sr:.2f} s, molhado {MOLHADO}, RT60 {RT60} s")
