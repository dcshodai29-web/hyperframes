"""FLUX.2 [klein] 4B (Apache-2.0) em CPU: geração, edição por instrução e inpainting.

A RAM (15 GB) não comporta o codificador de texto (8 GB) e o transformer (8 GB)
ao mesmo tempo, então o fluxo é sequencial: codifica o prompt -> libera ->
carrega o transformer. Os embeddings ficam em cache em disco.

O modelo trabalha em ~1 megapixel. As funções devolvem a imagem na resolução
de trabalho; quem chama compõe o resultado sobre o original em resolução cheia
(ver light.py / background.py), preservando os pixels que não devem mudar.
"""

from __future__ import annotations

import gc
import hashlib

import numpy as np

from . import core, models

KEY = "flux2-klein-4b"
_pipe = None


def _emb_file(prompt):
    d = core.CACHE / "emb"
    d.mkdir(parents=True, exist_ok=True)
    return d / (hashlib.sha1(("klein4b|" + prompt).encode()).hexdigest() + ".pt")


def encode(prompt):
    """Embedding do prompt (cache em disco). Libera o transformer se estiver na RAM."""
    global _pipe
    torch, dt = core.torch_setup()
    f = _emb_file(prompt)
    if f.exists():
        return torch.load(f)
    if _pipe is not None:
        _pipe = None
        gc.collect()
    from diffusers import Flux2KleinPipeline

    with core.Timer("codificador de texto"):
        te = Flux2KleinPipeline.from_pretrained(models.path(KEY), transformer=None, vae=None, torch_dtype=dt)
        with torch.inference_mode():
            emb, _ = te.encode_prompt(prompt=prompt)
        emb = emb.clone()
        del te
        gc.collect()
    torch.save(emb, f)
    return emb


def _load():
    global _pipe
    if _pipe is None:
        torch, dt = core.torch_setup()
        from diffusers import Flux2KleinPipeline

        _pipe = Flux2KleinPipeline.from_pretrained(models.path(KEY), text_encoder=None, tokenizer=None, torch_dtype=dt)
        _pipe.set_progress_bar_config(disable=True)
    return _pipe


def unload():
    global _pipe
    _pipe = None
    gc.collect()


def generate(prompt, width=1024, height=1024, steps=4, seed=0):
    """Texto -> imagem (float32 sRGB). Dimensões são ajustadas a múltiplos de 16."""
    torch, _ = core.torch_setup()
    emb = encode(prompt)
    pipe = _load()
    width, height = (int(width) // 16) * 16, (int(height) // 16) * 16
    with core.Timer(f"klein gerar {width}x{height} ({steps} passos)"), torch.inference_mode():
        im = pipe(
            prompt_embeds=emb, width=width, height=height, num_inference_steps=steps, guidance_scale=1.0,
            generator=torch.Generator().manual_seed(int(seed)),
        ).images[0]  # fmt: skip
    return core.from_pil(im)


def edit(images, prompt, megapixels=1.0, steps=4, seed=0, size=None):
    """Edição por instrução. `images`: array ou lista (1ª = base; demais = referências).

    Devolve a imagem editada na resolução de trabalho (mesma proporção da base).
    """
    torch, _ = core.torch_setup()
    if isinstance(images, np.ndarray):
        images = [images]
    base = images[0]
    h, w = base.shape[:2]
    ww, wh = size or core.fit_area(w, h, megapixels, 16)
    pil = [core.to_pil(core.resize(base, (ww, wh)))]
    for ref in images[1:]:
        rw, rh = core.fit_area(ref.shape[1], ref.shape[0], min(megapixels, 1.0), 16)
        pil.append(core.to_pil(core.resize(ref, (rw, rh))))
    emb = encode(prompt)
    pipe = _load()
    with core.Timer(f"klein editar {ww}x{wh} ({steps} passos, {len(pil)} imagem(ns))"), torch.inference_mode():
        im = pipe(
            image=pil if len(pil) > 1 else pil[0], prompt_embeds=emb, width=ww, height=wh,
            num_inference_steps=steps, guidance_scale=1.0, generator=torch.Generator().manual_seed(int(seed)),
        ).images[0]  # fmt: skip
    return core.from_pil(im)


def repaint(rgb, mask, prompt, megapixels=1.0, steps=4, seed=0, strength=1.0, reference=True):
    """Regenera só onde mask=1, com os latentes do resto FIXOS a cada passo (geometria travada).

    Ideal para trocar o cenário mantendo o assunto parado no lugar. A máscara atua em
    blocos de 16 px; a composição fina por alfa fica com quem chama.
    Devolve a imagem na resolução de trabalho.
    """
    torch, _ = core.torch_setup()
    from diffusers import Flux2KleinInpaintPipeline

    h, w = rgb.shape[:2]
    ww, wh = core.fit_area(w, h, megapixels, 16)
    src = core.to_pil(core.resize(rgb, (ww, wh)))
    m = core.to_pil(np.repeat((core.resize(mask, (ww, wh), "linear") > 0.5).astype(np.float32)[..., None], 3, 2))
    emb = encode(prompt)
    pipe = Flux2KleinInpaintPipeline(**_load().components)
    pipe.set_progress_bar_config(disable=True)
    with core.Timer(f"klein repintar {ww}x{wh} ({steps} passos)"), torch.inference_mode():
        im = pipe(
            prompt_embeds=emb, image=src, mask_image=m.convert("L"), image_reference=src if reference else None,
            width=ww, height=wh, strength=strength, num_inference_steps=steps, guidance_scale=1.0,
            generator=torch.Generator().manual_seed(int(seed)),
        ).images[0]  # fmt: skip
    return core.from_pil(im)


def inpaint(rgb, mask, prompt, megapixels=1.0, steps=4, seed=0, context=0.35, feather=None, refs=()):
    """Edição localizada generativa: só a região da máscara muda.

    Recorta a região (com contexto), edita o recorte em resolução total do modelo
    e devolve a imagem inteira com o recorte recomposto por máscara suavizada.
    Fora da máscara os pixels são os originais, bit a bit.
    """
    h, w = rgb.shape[:2]
    box = core.bbox(mask, 0.05)
    if box is None:
        raise ValueError("Máscara vazia")
    x0, y0, x1, y1 = box
    pad = int(max(x1 - x0, y1 - y0) * context) + 16
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    crop = rgb[y0:y1, x0:x1]
    m = mask[y0:y1, x0:x1]
    # regiões pequenas são ampliadas até ~0,45 MP: o modelo rende mal abaixo disso
    ch, cw = crop.shape[:2]
    size = core.fit_area(cw, ch, min(megapixels, max(0.45, cw * ch / 1e6)), 16, upscale=True)
    out_small = edit([crop, *refs], prompt, megapixels=megapixels, steps=steps, seed=seed, size=size)
    out = core.resize(out_small, (x1 - x0, y1 - y0))
    f = feather if feather is not None else max(2.0, 0.006 * max(x1 - x0, y1 - y0))
    soft = core.feather(core.grow(m, int(round(f))), f)
    result = rgb.copy()
    result[y0:y1, x0:x1] = core.mix(crop, out, soft)
    return result
