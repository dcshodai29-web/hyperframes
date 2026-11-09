"""Gera uma trilha instrumental local com MusicGen (facebook/musicgen-small).

Uso: python3 musica.py "<prompt em inglês>" <segundos> <saida.wav>
Gratuito e offline depois do primeiro download (~300 MB, em ~/.cache/huggingface).
"""
import sys

import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

prompt, seconds, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
torch.manual_seed(7)  # mesma entrada, mesma música
torch.set_num_threads(max(1, torch.get_num_threads()))

processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
sr = model.config.audio_encoder.sampling_rate
frame_rate = model.config.audio_encoder.frame_rate  # ~50 tokens por segundo
seed_s = min(seconds, 28.0)
tokens = int(seed_s * frame_rate) + 8

inputs = processor(text=[prompt], padding=True, return_tensors="pt")
with torch.no_grad():
    audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0, max_new_tokens=tokens)
clip = audio[0, 0].cpu().numpy().astype(np.float32)

target = int(seconds * sr)
if clip.shape[0] < target:  # repete com crossfade de 1,5 s
    xf = int(1.5 * sr)
    out_buf = clip.copy()
    while out_buf.shape[0] < target:
        ramp = np.linspace(0, 1, xf, dtype=np.float32)
        head = out_buf[:-xf]
        mix = out_buf[-xf:] * (1 - ramp) + clip[:xf] * ramp
        out_buf = np.concatenate([head, mix, clip[xf:]])
    clip = out_buf
clip = clip[:target]

peak = float(np.max(np.abs(clip))) or 1.0
clip = clip / peak * 0.89  # ~ -1 dBFS de pico
sf.write(out, clip, sr)
print(f"[musica] {out} {clip.shape[0] / sr:.2f}s sr={sr}")
