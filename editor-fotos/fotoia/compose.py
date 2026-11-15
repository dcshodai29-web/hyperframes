"""Composição: recorte inteligente por proporção e expansão de tela (outpainting)."""

from __future__ import annotations

import numpy as np

from . import core


def parse_ratio(s):
    a, b = str(s).replace("x", ":").replace("/", ":").split(":")
    return float(a) / float(b)


def smart_crop(rgb, ratio, alpha=None):
    """Maior recorte na proporção pedida, centrado no assunto (terço superior para retratos)."""
    r = parse_ratio(ratio) if isinstance(ratio, str) else float(ratio)
    h, w = rgb.shape[:2]
    cw, ch = (w, int(round(w / r))) if w / h <= r else (int(round(h * r)), h)
    cw, ch = min(cw, w), min(ch, h)
    if alpha is None:
        from . import segment

        alpha = segment.matte_subject(rgb, "birefnet", refine=False)
    box = core.bbox(alpha, 0.5)
    if box is None:
        cx, cy = w / 2, h / 2
    else:
        cx = (box[0] + box[2]) / 2
        cy = box[1] + (box[3] - box[1]) * (0.42 if (box[3] - box[1]) > (box[2] - box[0]) else 0.5)
    x0 = int(np.clip(cx - cw / 2, 0, w - cw))
    y0 = int(np.clip(cy - ch / 2, 0, h - ch))
    return np.ascontiguousarray(rgb[y0 : y0 + ch, x0 : x0 + cw])


def outpaint(rgb, ratio, prompt="", seed=0, megapixels=1.0):
    """Expande a tela até a proporção pedida; a foto original fica intacta no centro."""
    from . import flux

    r = parse_ratio(ratio) if isinstance(ratio, str) else float(ratio)
    h, w = rgb.shape[:2]
    nw, nh = (int(round(h * r)), h) if w / h < r else (w, int(round(w / r)))
    if (nw, nh) == (w, h):
        return rgb
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    # semente de cor: bordas espelhadas e desfocadas ajudam o modelo a continuar a cena
    canvas = np.pad(rgb, ((y0, nh - h - y0), (x0, nw - w - x0), (0, 0)), mode="reflect")
    canvas = core.blur(canvas, 0.02 * max(nw, nh))
    canvas[y0 : y0 + h, x0 : x0 + w] = rgb
    mask = np.ones((nh, nw), dtype=np.float32)
    inset = max(4, int(0.01 * max(w, h)))
    mask[y0 + inset : y0 + h - inset, x0 + inset : x0 + w - inset] = 0
    instr = "Extend this photo naturally beyond its borders, continuing the same scene, lighting and style."
    if prompt:
        instr += " " + prompt
    small = flux.repaint(canvas, mask, instr, megapixels=megapixels, seed=seed)
    out = core.resize(small, (nw, nh))
    keep = np.zeros((nh, nw), dtype=np.float32)
    keep[y0 : y0 + h, x0 : x0 + w] = 1
    keep = core.feather(core.grow(keep, -inset * 2), inset)
    out = core.mix(out, canvas, keep)
    return np.clip(out, 0, 1).astype(np.float32)
