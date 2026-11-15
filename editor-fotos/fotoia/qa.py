"""Controle de qualidade: análise da foto, verificação de preservação e comparativos."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import core


def analyze(rgb):
    """Métricas objetivas para orientar a edição (o olhar do agente decide o resto)."""
    h, w = rgb.shape[:2]
    lab = core.rgb_to_lab(rgb)
    L = lab[..., 0] / 100.0
    gray = (L * 255).astype(np.uint8)
    small = cv2.resize(gray, (min(w, 1024), int(h * min(w, 1024) / w)), interpolation=cv2.INTER_AREA)
    neutral = (np.hypot(lab[..., 1], lab[..., 2]) < 18) & (L > 0.25) & (L < 0.92)
    hp = small.astype(np.float32) - cv2.GaussianBlur(small.astype(np.float32), (0, 0), 1.5)
    flat = cv2.Laplacian(small, cv2.CV_32F)
    rep = {
        "largura": w, "altura": h, "megapixels": round(w * h / 1e6, 2), "proporcao": round(w / h, 4),
        "luminancia_media": round(float(L.mean()), 3),
        "p1_p50_p99": [round(float(np.percentile(L, p)), 3) for p in (1, 50, 99)],
        "sombras_cortadas_%": round(float((rgb.max(axis=2) < 0.012).mean() * 100), 2),
        "luzes_estouradas_%": round(float((rgb.min(axis=2) > 0.988).mean() * 100), 2),
        "contraste_p5_p95": round(float(np.percentile(L, 95) - np.percentile(L, 5)), 3),
        "nitidez_laplaciano": round(float(flat.var()), 1),
        "ruido_estimado": round(float(np.median(np.abs(hp)) / 0.6745 / 255), 4),
        "saturacao_media": round(float(np.hypot(lab[..., 1], lab[..., 2]).mean()), 1),
        "dominante_ab": [round(float(lab[..., 1][neutral].mean()), 1), round(float(lab[..., 2][neutral].mean()), 1)]
        if neutral.sum() > 500 else None,
    }  # fmt: skip
    notes = []
    if rep["luminancia_media"] < 0.3:
        notes.append("subexposta")
    if rep["luminancia_media"] > 0.72:
        notes.append("clara/high-key")
    if rep["contraste_p5_p95"] < 0.45:
        notes.append("baixo contraste")
    if rep["luzes_estouradas_%"] > 2:
        notes.append("altas-luzes estouradas")
    if rep["nitidez_laplaciano"] < 60:
        notes.append("suave/desfocada")
    if rep["ruido_estimado"] > 0.012:
        notes.append("ruidosa")
    if rep["dominante_ab"] and max(abs(v) for v in rep["dominante_ab"]) > 6:
        notes.append("dominante de cor")
    if max(w, h) < 1600:
        notes.append("baixa resolução (considere upscale)")
    rep["observacoes"] = notes
    return rep


def preservation(original, result, mask=None):
    """Quanto a região protegida mudou. Compara em resolução do original.

    - diff_medio: diferença absoluta média (0-255) — inclui mudanças de luz.
    - estrutura: correlação dos detalhes finos (1.0 = textura idêntica). É a
      métrica que importa quando a luz mudou de propósito.
    """
    h, w = original.shape[:2]
    res = core.resize(result, (w, h)) if result.shape[:2] != (h, w) else result
    m = np.ones((h, w), dtype=bool) if mask is None else (core.grow(mask, -3) > 0.9)
    if m.sum() < 50:
        return {"erro": "máscara vazia"}
    d = np.abs(original - res).mean(axis=2) * 255
    La, Lb = core.rgb_to_lab(original)[..., 0], core.rgb_to_lab(res)[..., 0]
    ha, hb = La - core.blur(La, 2.0), Lb - core.blur(Lb, 2.0)
    a, b = ha[m], hb[m]
    corr = float((a * b).mean() / max(1e-6, np.sqrt((a * a).mean() * (b * b).mean())))
    return {
        "diff_medio": round(float(d[m].mean()), 2),
        "diff_p99": round(float(np.percentile(d[m], 99)), 2),
        "pixels_identicos_%": round(float((d[m] < 1.0).mean() * 100), 1),
        "estrutura": round(corr, 4),
        "ganho_detalhe": round(float(np.sqrt((b * b).mean() / max(1e-9, (a * a).mean()))), 3),
    }


def sheet(images, labels=None, out=None, height=900, cols=None):
    """Folha de comparação lado a lado (para revisão do agente e do cliente)."""
    tiles = []
    for i, im in enumerate(images):
        arr = core.load_image(im) if not isinstance(im, np.ndarray) else im
        if arr.ndim == 2:
            arr = np.repeat(arr[..., None], 3, 2)
        s = height / arr.shape[0]
        pil = core.to_pil(core.resize(arr, (max(1, round(arr.shape[1] * s)), height)))
        if labels:
            d = ImageDraw.Draw(pil)
            d.rectangle([0, 0, 14 + 9 * len(labels[i]), 30], fill=(0, 0, 0))
            d.text((7, 8), labels[i], fill=(255, 255, 255))
        tiles.append(pil)
    cols = cols or len(tiles)
    rows = (len(tiles) + cols - 1) // cols
    cw = max(t.width for t in tiles)
    canvas = Image.new("RGB", (cols * cw + (cols - 1) * 8, rows * height + (rows - 1) * 8), (24, 24, 24))
    for i, t in enumerate(tiles):
        canvas.paste(t, ((i % cols) * (cw + 8) + (cw - t.width) // 2, (i // cols) * (height + 8)))
    if out:
        canvas.save(out, quality=90)
    return canvas


def crop_zoom(images, box, out=None, height=700, labels=None):
    """Recorte ampliado da mesma região em várias versões (conferir bordas e textura)."""
    crops = []
    for im in images:
        arr = core.load_image(im) if not isinstance(im, np.ndarray) else im
        H, W = arr.shape[:2]
        x0, y0, x1, y1 = [int(round(v * (W if i % 2 == 0 else H))) if 0 <= v <= 1 else int(v) for i, v in enumerate(box)]
        crops.append(arr[y0:y1, x0:x1])
    return sheet(crops, labels, out, height)
