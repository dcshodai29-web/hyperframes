"""Profundidade monocular (Depth Anything V2) e desfoque de lente por profundidade."""

from __future__ import annotations

import cv2
import numpy as np

from . import core, models

_cache = {}


def estimate(rgb, model="depth-small", max_side=1036):
    """Mapa de profundidade relativo [0,1] (1 = mais perto da câmera)."""
    torch, _ = core.torch_setup()
    if model not in _cache:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        _cache.clear()
        p = models.path(model)
        _cache[model] = (AutoImageProcessor.from_pretrained(p), AutoModelForDepthEstimation.from_pretrained(p).eval())
    proc, net = _cache[model]
    h, w = rgb.shape[:2]
    s = min(1.0, max_side / max(h, w))
    tw, th = max(14, int(round(w * s / 14)) * 14), max(14, int(round(h * s / 14)) * 14)
    small = core.resize(rgb, (tw, th))
    inputs = proc(images=core.to_pil(small), return_tensors="pt", do_resize=False)
    with torch.inference_mode():
        d = net(**inputs).predicted_depth[0].float().numpy()
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    # alinha as bordas do mapa às da imagem
    d = core.guided(rgb, d.astype(np.float32), max(2, round(max(h, w) / 300)), 1e-4)
    return np.clip(d, 0, 1).astype(np.float32)


def _disc(r):
    k = int(np.ceil(r)) * 2 + 1
    yy, xx = np.mgrid[0:k, 0:k].astype(np.float32) - k // 2
    ker = np.clip(r + 0.5 - np.sqrt(xx * xx + yy * yy), 0, 1)
    return ker / ker.sum()


def lens_blur(rgb, depth, focus=None, amount=0.02, alpha=None, layers=8, highlights=0.6):
    """Bokeh por profundidade (kernel em disco, luz linear, realce de altas-luzes).

    focus: profundidade em foco [0,1]; padrão = mediana do assunto (alpha) ou do centro.
    amount: raio máximo do desfoque em fração do lado maior.
    """
    h, w = depth.shape
    if focus is None:
        if alpha is not None and (alpha > 0.5).any():
            focus = float(np.median(depth[alpha > 0.5]))
        else:
            focus = float(np.median(depth[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3]))
    coc = np.abs(depth - focus)
    if alpha is not None:
        coc = coc * (1 - np.clip(alpha, 0, 1))  # assunto sempre nítido
    coc = coc / max(1e-6, coc.max())
    rmax = amount * max(h, w)
    lin = core.srgb_to_linear(rgb)
    lum = core.luminance(lin)[..., None]
    boost = 1.0 + highlights * 6.0 * np.clip(lum - 0.7, 0, None) ** 2  # bokeh "acende" pontos de luz
    src = lin * boost
    if alpha is not None:  # não deixa o assunto vazar para dentro do desfoque
        keep = (1 - np.clip(core.grow(alpha, 2), 0, 1))[..., None]
        fill_w = core.blur(keep[..., 0], rmax)[..., None]
        src_bg = core.blur(src * keep, rmax) / np.maximum(fill_w, 1e-3)
        src = src * keep + src_bg * (1 - keep)
        boost = boost * keep + (1 - keep)
    levels = np.linspace(0, 1, layers + 1)
    stack_c, stack_w = [src], [boost]
    for lv in levels[1:]:
        ker = _disc(max(0.6, lv * rmax))
        stack_c.append(cv2.filter2D(src, -1, ker, borderType=cv2.BORDER_REFLECT101))
        bw = cv2.filter2D(boost, -1, ker, borderType=cv2.BORDER_REFLECT101)
        stack_w.append(bw[..., None] if bw.ndim == 2 else bw)
    idx = np.clip(coc * layers, 0, layers - 1e-4)
    i0 = np.floor(idx).astype(np.int32)
    f = (idx - i0)[..., None]
    out = np.zeros_like(lin)
    for i in range(layers):
        sel = (i0 == i)[..., None]
        if not sel.any():
            continue
        a = stack_c[i] / np.maximum(stack_w[i], 1e-4)
        b = stack_c[i + 1] / np.maximum(stack_w[i + 1], 1e-4)
        out += sel * (a * (1 - f) + b * f)
    res = core.linear_to_srgb(out)
    if alpha is not None:
        res = core.mix(res, rgb, np.clip(alpha, 0, 1))
    return np.clip(res, 0, 1).astype(np.float32)
