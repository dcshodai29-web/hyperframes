"""Ajustes fotográficos clássicos (determinísticos): exposição, contraste, cor,
nitidez, textura, ruído, gradação e acabamento. Todos aceitam máscara."""

from __future__ import annotations

import cv2
import numpy as np

from . import core


def _masked(orig, out, mask):
    out = np.clip(out, 0, 1).astype(np.float32)
    return out if mask is None else core.mix(orig, out, np.clip(mask, 0, 1))


# --------------------------------------------------------------------------- tom


def exposure(rgb, ev=0.0, mask=None):
    """Exposição em stops, em luz linear, com rolagem suave das altas-luzes."""
    from .light import _soft_clip

    lin = core.srgb_to_linear(rgb) * (2.0**ev)
    return _masked(rgb, core.linear_to_srgb(_soft_clip(lin)), mask)


def contrast(rgb, amount=0.0, pivot=0.45, mask=None):
    """Curva em S na luminância (amount -1..1), preservando matiz e saturação."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    k = 1.0 + 2.5 * abs(amount)
    s = 1 / (1 + np.exp(-k * 4 * (L - pivot)))
    s0, s1 = 1 / (1 + np.exp(k * 4 * pivot)), 1 / (1 + np.exp(-k * 4 * (1 - pivot)))
    s = (s - s0) / (s1 - s0)
    t = min(1.0, abs(amount))
    if amount >= 0:
        Ln = L * (1 - t) + s * t
    else:
        inv = np.clip(2 * L - s, 0, 1)
        Ln = L * (1 - t) + inv * t
    lab[..., 0] = np.clip(Ln, 0, 1) * 100.0
    gain = 1 + 0.25 * amount  # o contraste em Lab dessatura um pouco: compensa
    lab[..., 1:] *= gain
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def levels(rgb, black=0.0, white=1.0, gamma=1.0, mask=None):
    x = np.clip((rgb - black) / max(1e-4, white - black), 0, 1) ** (1.0 / gamma)
    return _masked(rgb, x, mask)


def auto_levels(rgb, clip_low=0.3, clip_high=0.3, mask=None):
    L = core.rgb_to_lab(rgb)[..., 0] / 100.0
    lo, hi = np.percentile(L, clip_low), np.percentile(L, 100 - clip_high)
    lab = core.rgb_to_lab(rgb)
    lab[..., 0] = np.clip((L - lo) / max(1e-3, hi - lo), 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def shadows_highlights(rgb, shadows=0.0, highlights=0.0, radius=0.03, mask=None):
    """Recupera sombras (+) e altas-luzes (-) localmente, sem halos (base por filtro guiado)."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    r = max(4, int(radius * max(rgb.shape[:2])))
    base = core.guided(L, L, r, 0.01)
    sh_w = np.clip(1 - base / 0.5, 0, 1) ** 1.5
    hl_w = np.clip((base - 0.5) / 0.5, 0, 1) ** 1.5
    Ln = L + shadows * 0.45 * sh_w * (1 - L) * (L + 0.08) * 4 + highlights * 0.45 * hl_w * L * (1.05 - L) * 4
    lab[..., 0] = np.clip(Ln, 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)


# --------------------------------------------------------------------------- cor


def white_balance(rgb, temp=0.0, tint=0.0, mask=None):
    """temp >0 esquenta, <0 esfria; tint >0 magenta, <0 verde (-1..1)."""
    lin = core.srgb_to_linear(rgb)
    g = np.array([1 + 0.35 * temp + 0.12 * tint, 1 - 0.18 * tint, 1 - 0.35 * temp + 0.12 * tint], dtype=np.float32)
    g = g / (0.2126 * g[0] + 0.7152 * g[1] + 0.0722 * g[2])
    return _masked(rgb, core.linear_to_srgb(lin * g), mask)


def auto_white_balance(rgb, strength=1.0, mask=None):
    """Neutraliza dominante de cor usando os pixels quase neutros de brilho médio."""
    lab = core.rgb_to_lab(rgb)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    sel = (L > 25) & (L < 92) & (np.hypot(a, b) < 22)
    if sel.sum() < 500:
        sel = (L > 20) & (L < 95)
    lab[..., 1] -= float(np.median(a[sel])) * strength
    lab[..., 2] -= float(np.median(b[sel])) * strength
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def saturation(rgb, sat=0.0, vibrance=0.0, mask=None):
    """sat: uniforme. vibrance: reforça mais as cores apagadas e protege tons de pele."""
    lab = core.rgb_to_lab(rgb)
    c = np.hypot(lab[..., 1], lab[..., 2])
    gain = 1 + sat
    if vibrance:
        gain = gain * (1 + vibrance * (1 - np.clip(c / 70.0, 0, 1)))
    lab[..., 1] *= gain
    lab[..., 2] *= gain
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def hue_shift(rgb, degrees=0.0, mask=None):
    hsv = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv[..., 0] = (hsv[..., 0] + degrees) % 360
    return _masked(rgb, cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB), mask)


def recolor(rgb, color, mask, keep_shading=1.0):
    """Troca a cor de uma região mantendo luz, sombra e textura (Lab: muda a/b, ajusta L)."""
    target = core.rgb_to_lab(core.parse_color(color)[None, None, :])[0, 0]
    lab = core.rgb_to_lab(rgb)
    sel = mask > 0.5
    if not sel.any():
        return rgb
    Lm = float(np.median(lab[..., 0][sel]))
    out = lab.copy()
    out[..., 0] = np.clip(lab[..., 0] + (target[0] - Lm) * (1 - 0.35 * keep_shading), 0, 100)
    out[..., 1], out[..., 2] = target[1], target[2]
    # sombras ficam menos saturadas, como no tecido/material real
    k = np.clip(out[..., 0] / max(1.0, target[0]), 0.25, 1.3)
    out[..., 1] *= k
    out[..., 2] *= k
    return _masked(rgb, core.lab_to_rgb(out), mask)


GRADES = {
    "teal-orange": dict(shadows="#0e3a46", highlights="#ffb070", balance=0.0, amount=0.22),
    "quente": dict(shadows="#3a2414", highlights="#ffd9a8", balance=0.1, amount=0.18),
    "frio": dict(shadows="#14263a", highlights="#cfe4ff", balance=0.0, amount=0.18),
    "cinema": dict(shadows="#10202c", highlights="#ffe2bd", balance=-0.1, amount=0.20),
    "noir": dict(shadows="#101418", highlights="#f2f2ee", balance=0.0, amount=0.10),
    "pastel": dict(shadows="#3b3550", highlights="#ffeede", balance=0.2, amount=0.15),
}


def split_tone(rgb, shadows="#0e3a46", highlights="#ffb070", balance=0.0, amount=0.2, mask=None):
    """Tonalização dividida (sombras/altas-luzes) preservando a luminância."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    w_h = np.clip((L - 0.5 + balance * 0.5) * 2 + 0.5, 0, 1)
    s_lab = core.rgb_to_lab(core.parse_color(shadows)[None, None, :])[0, 0]
    h_lab = core.rgb_to_lab(core.parse_color(highlights)[None, None, :])[0, 0]
    mid = 1 - np.abs(L - 0.5) * 1.2
    for c in (1, 2):
        tint = s_lab[c] * (1 - w_h) + h_lab[c] * w_h
        lab[..., c] += tint * amount * np.clip(mid + 0.4, 0, 1)
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def grade(rgb, name="teal-orange", amount=None, mask=None):
    g = dict(GRADES[name])
    if amount is not None:
        g["amount"] = amount
    out = split_tone(rgb, **g)
    if name == "noir":
        lab = core.rgb_to_lab(out)
        lab[..., 1:] *= 0.08
        out = core.lab_to_rgb(lab)
    return _masked(rgb, out, mask)


def apply_lut(rgb, cube_path, amount=1.0, mask=None):
    """Aplica uma LUT 3D .cube (interpolação trilinear)."""
    size, table = None, []
    for line in open(cube_path):
        p = line.strip().split()
        if not p or p[0].startswith("#"):
            continue
        if p[0] == "LUT_3D_SIZE":
            size = int(p[1])
        elif len(p) == 3 and p[0].replace(".", "").replace("-", "").replace("e", "").isdigit():
            table.append([float(v) for v in p])
    lut = np.asarray(table, dtype=np.float32).reshape(size, size, size, 3)  # índice [b, g, r]
    x = np.clip(rgb, 0, 1) * (size - 1)
    i0 = np.floor(x).astype(np.int32)
    i1 = np.minimum(i0 + 1, size - 1)
    f = x - i0
    out = np.zeros_like(rgb)
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                ib = i1[..., 2] if db else i0[..., 2]
                ig = i1[..., 1] if dg else i0[..., 1]
                ir = i1[..., 0] if dr else i0[..., 0]
                wgt = (
                    (f[..., 2] if db else 1 - f[..., 2])
                    * (f[..., 1] if dg else 1 - f[..., 1])
                    * (f[..., 0] if dr else 1 - f[..., 0])
                )
                out += lut[ib, ig, ir] * wgt[..., None]
    return _masked(rgb, rgb * (1 - amount) + out * amount, mask)


# --------------------------------------------------------------------------- detalhe


def clarity(rgb, amount=0.3, radius=0.03, mask=None):
    """Contraste local de raio largo nos meios-tons (volume, definição de formas)."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    r = max(4, int(radius * max(rgb.shape[:2])))
    base = core.guided(L, L, r, 0.02)
    mid = 1 - np.abs(L - 0.5) * 2
    lab[..., 0] = np.clip(L + (L - base) * amount * 2.2 * (0.35 + 0.65 * np.clip(mid, 0, 1)), 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def texture(rgb, amount=0.3, radius=0.004, mask=None):
    """Realça microtextura (frequência média-alta) sem endurecer bordas grandes."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    s = max(0.8, radius * max(rgb.shape[:2]))
    band = core.blur(L, s * 0.35) - core.blur(L, s * 1.6)
    band = band * (1 - np.clip(np.abs(band) / 0.12, 0, 1))  # atenua bordas fortes (sem halos)
    lab[..., 0] = np.clip(L + band * amount * 3.0, 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def sharpen(rgb, amount=0.6, radius=1.0, threshold=0.008, mask=None):
    """Nitidez de saída (unsharp na luminância, com limiar para não amplificar ruído)."""
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    d = L - core.blur(L, radius)
    d = np.sign(d) * np.clip(np.abs(d) - threshold, 0, None)
    d = np.clip(d, -0.08, 0.08)  # limita halos
    lab[..., 0] = np.clip(L + d * amount * 1.6, 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)


def denoise(rgb, luma=0.3, chroma=0.6, mask=None):
    """Redução de ruído: forte na crominância, moderada na luminância (preserva detalhe)."""
    u8 = core.to_u8(rgb, dither=False)
    out = cv2.fastNlMeansDenoisingColored(u8, None, max(0.1, luma * 10), max(0.1, chroma * 14), 5, 15)
    return _masked(rgb, out.astype(np.float32) / 255.0, mask)


def dehaze(rgb, amount=0.5, mask=None):
    """Remove névoa (dark channel prior simplificado)."""
    h, w = rgb.shape[:2]
    k = max(7, int(0.012 * max(h, w)) | 1)
    dark = cv2.erode(rgb.min(axis=2), np.ones((k, k), np.uint8))
    idx = np.argsort(dark.ravel())[-max(10, dark.size // 1000) :]
    A = np.maximum(rgb.reshape(-1, 3)[idx].mean(axis=0), 0.5)
    t = 1 - amount * 0.95 * cv2.erode((rgb / A).min(axis=2), np.ones((k, k), np.uint8))
    t = np.clip(core.guided(rgb, t.astype(np.float32), k * 3, 1e-3), 0.15, 1)[..., None]
    return _masked(rgb, (rgb - A) / t + A, mask)


# --------------------------------------------------------------------------- acabamento


def haze(rgb, amount=0.2, color="#ffffff", mask=None):
    """Atmosfera/névoa suave: véu luminoso de baixo contraste (ponderado pela máscara)."""
    c = core.srgb_to_linear(core.parse_color(color))
    lin = core.srgb_to_linear(rgb)
    veil = amount if mask is None else amount * np.clip(mask, 0, 1)[..., None]
    return np.clip(core.linear_to_srgb(lin * (1 - veil) + c * veil), 0, 1).astype(np.float32)


def bloom(rgb, amount=0.3, threshold=0.75, radius=0.03, mask=None):
    """Brilho difuso das altas-luzes (glow), em luz linear."""
    lin = core.srgb_to_linear(rgb)
    lum = core.luminance(lin)
    bright = lin * np.clip((lum - threshold) / max(1e-3, 1 - threshold), 0, 1)[..., None]
    s = radius * max(rgb.shape[:2])
    glow = core.blur(bright, s * 0.35) * 0.5 + core.blur(bright, s) * 0.35 + core.blur(bright, s * 2.5) * 0.25
    out = 1 - (1 - np.clip(lin, 0, 1)) * (1 - np.clip(glow * amount * 2.0, 0, 1))  # screen
    return _masked(rgb, core.linear_to_srgb(out), mask)


def vignette(rgb, amount=0.25, midpoint=0.6, mask=None):
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    v = 1 - amount * np.clip((d - midpoint * 0.5) / (1 - midpoint * 0.5), 0, 1) ** 2
    return _masked(rgb, core.linear_to_srgb(core.srgb_to_linear(rgb) * v[..., None]), mask)


def grain(rgb, amount=0.15, size=1.0, seed=7, mask=None):
    """Grão de filme (luminância, mais visível nos meios-tons)."""
    h, w = rgb.shape[:2]
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((int(h / size) + 1, int(w / size) + 1)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) if size != 1.0 else n[:h, :w]
    L = core.rgb_to_lab(rgb)[..., 0] / 100.0
    wgt = 0.35 + 0.65 * (1 - np.abs(L - 0.5) * 2)
    return _masked(rgb, rgb + (n * wgt * amount * 0.08)[..., None], mask)


def dodge_burn(rgb, amount=0.3, radius=0.02, mask=None):
    """Dodge & burn automático: aprofunda sombras de forma e levanta os volumes.

    Acentua o relevo já existente (músculos, dobras, relevo de produto) sem inventar forma.
    """
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    s = max(2.0, radius * max(rgb.shape[:2]))
    form = core.blur(L, s * 0.5) - core.blur(L, s * 2.5)  # relevo de escala média
    form = np.tanh(form / 0.08) * 0.08
    lab[..., 0] = np.clip(L + form * amount * 2.5, 0, 1) * 100
    return _masked(rgb, core.lab_to_rgb(lab), mask)
