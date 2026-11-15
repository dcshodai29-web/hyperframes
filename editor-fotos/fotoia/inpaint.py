"""Remoção e preenchimento: LaMa (limpo, não generativo) e FLUX.2 klein (generativo)."""

from __future__ import annotations

import numpy as np

from . import core, models

_lama = None


def _load_lama():
    global _lama
    if _lama is None:
        torch, _ = core.torch_setup()
        _lama = torch.jit.load(models.path("lama"), map_location="cpu").eval()
    return _lama


def remove(rgb, mask, grow=None, feather=None, max_side=1536, context=0.6):
    """Apaga o que está na máscara e reconstrói o fundo (LaMa).

    Trabalha num recorte com contexto e devolve a foto inteira; fora da máscara
    (dilatada/suavizada) os pixels são os originais.
    """
    torch, _ = core.torch_setup()
    h, w = rgb.shape[:2]
    g = int(grow if grow is not None else max(3, round(0.006 * max(h, w))))
    m = core.grow((mask > 0.3).astype(np.float32), g)
    box = core.bbox(m, 0.5)
    if box is None:
        return rgb
    x0, y0, x1, y1 = box
    pad = int(max(x1 - x0, y1 - y0) * context) + 32
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    crop, cm = rgb[y0:y1, x0:x1], m[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    s = min(1.0, max_side / max(ch, cw))
    tw, th = max(8, int(round(cw * s / 8)) * 8), max(8, int(round(ch * s / 8)) * 8)
    ci = core.resize(crop, (tw, th))
    mi = (core.resize(cm, (tw, th), "linear") > 0.3).astype(np.float32)
    net = _load_lama()
    with core.Timer(f"LaMa {tw}x{th}"), torch.inference_mode():
        t_img = torch.from_numpy(np.ascontiguousarray(ci.transpose(2, 0, 1)))[None]
        t_m = torch.from_numpy(mi)[None, None]
        res = net(t_img, t_m)[0].clamp(0, 1).numpy().transpose(1, 2, 0)
    res = core.resize(res, (cw, ch))
    f = feather if feather is not None else max(1.5, g * 0.5)
    soft = core.feather(cm, f)
    out = rgb.copy()
    out[y0:y1, x0:x1] = core.mix(crop, res, soft)
    return out


def fill(rgb, mask, prompt, megapixels=1.0, seed=0, steps=4, refs=(), mode="edit"):
    """Preenchimento generativo guiado por texto dentro da máscara (FLUX.2 klein).

    mode="edit": instrução sobre o recorte (ex.: "change the shirt to red silk"), depois
        recompõe por máscara. Melhor para alterar algo que já existe.
    mode="repaint": regenera a região do zero com o entorno fixo (ex.: "a vase of
        flowers on the table"). Melhor para adicionar/substituir conteúdo.
    """
    from . import flux

    if mode == "edit":
        return flux.inpaint(rgb, mask, prompt, megapixels=megapixels, steps=steps, seed=seed, refs=refs)
    h, w = rgb.shape[:2]
    box = core.bbox(mask, 0.05)
    if box is None:
        raise ValueError("Máscara vazia")
    x0, y0, x1, y1 = box
    pad = int(max(x1 - x0, y1 - y0) * 0.6) + 32
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    crop, m = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    res = flux.repaint(crop, core.grow(m, 4), prompt, megapixels=megapixels, steps=steps, seed=seed)
    res = core.resize(res, (x1 - x0, y1 - y0))
    f = max(2.0, 0.006 * max(x1 - x0, y1 - y0))
    soft = core.feather(core.grow(m, int(round(f))), f)
    out = rgb.copy()
    out[y0:y1, x0:x1] = core.mix(crop, res, soft)
    return out
