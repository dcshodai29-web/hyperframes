"""Retoque de retrato conservador: uniformiza a pele sem apagar poros, realça
olhos e clareia dentes. Identidade e traços não são alterados."""

from __future__ import annotations

import numpy as np

from . import core, segment


def skin_smooth(rgb, skin, amount=0.5, scale=None):
    """Separação de frequências: suaviza manchas de escala média e mantém o poro.

    low  (forma/luz)  -> intacta
    mid  (manchas, vermelhidão irregular, pequenas sombras) -> atenuada
    high (poros, pelos, textura fina) -> intacta
    """
    h, w = rgb.shape[:2]
    box = core.bbox(skin, 0.3)
    if box is None:
        return rgb
    face = max(box[2] - box[0], box[3] - box[1])
    s = scale or max(1.5, face / 180.0)
    fine = core.blur(rgb, s)  # abaixo disso é textura fina
    coarse = core.guided(rgb, rgb, int(s * 7), 0.004)  # forma, preservando contornos
    mid = fine - coarse
    out = rgb - mid * np.clip(amount, 0, 1) * 0.85
    m = core.feather(skin, max(1.0, s * 1.5))
    return core.mix(rgb, np.clip(out, 0, 1), m)


def even_tone(rgb, skin, amount=0.3):
    """Aproxima a cor da pele da sua mediana local (reduz vermelhidão/manchas de cor)."""
    lab = core.rgb_to_lab(rgb)
    sel = skin > 0.6
    if sel.sum() < 200:
        return rgb
    box = core.bbox(skin, 0.3)
    s = max(4.0, max(box[2] - box[0], box[3] - box[1]) / 25.0)
    out = lab.copy()
    for c in (1, 2):
        local = core.blur(lab[..., c] * skin, s) / np.maximum(core.blur(skin, s), 1e-3)
        out[..., c] = lab[..., c] + (local - lab[..., c]) * amount
    return core.mix(rgb, core.lab_to_rgb(out), core.feather(skin, 2.0))


def eyes(rgb, mask, amount=0.3):
    """Mais vida nos olhos: contraste local e nitidez, sem mudar a cor da íris."""
    from . import enhance

    m = core.feather(core.grow(mask, 1), 1.5)
    x = enhance.clarity(rgb, amount * 0.9, radius=0.006)
    x = enhance.sharpen(x, amount * 1.2, 0.8)
    return core.mix(rgb, x, m)


def teeth(rgb, mouth, amount=0.3):
    """Clareia dentes: reduz o amarelo e levanta um pouco a luminosidade só nos pixels claros da boca."""
    lab = core.rgb_to_lab(rgb)
    bright = np.clip((lab[..., 0] - 45) / 25.0, 0, 1) * np.clip(1 - (lab[..., 1] - 8) / 14.0, 0, 1)
    m = core.feather(mouth * bright, 1.0)
    out = lab.copy()
    out[..., 2] = lab[..., 2] - np.clip(lab[..., 2], 0, None) * 0.6 * amount
    out[..., 0] = np.clip(lab[..., 0] + 7 * amount, 0, 100)
    return core.mix(rgb, core.lab_to_rgb(out), m)


def under_eyes(rgb, probs, amount=0.3):
    """Suaviza olheiras: clareia levemente a faixa logo abaixo dos olhos."""
    eye = np.clip(probs[segment.FACE_LABELS["l_eye"]] + probs[segment.FACE_LABELS["r_eye"]], 0, 1)
    box = core.bbox(eye, 0.3)
    if box is None:
        return rgb
    eh = max(4, box[3] - box[1])
    shifted = np.roll(core.grow(eye, int(eh * 0.5)), int(eh * 0.9), axis=0)
    skin = segment.face_mask(rgb, "skin", probs)
    m = core.feather(np.clip(shifted - core.grow(eye, 2), 0, 1) * skin, eh * 0.35)
    lab = core.rgb_to_lab(rgb)
    out = lab.copy()
    out[..., 0] = np.clip(lab[..., 0] + 9 * amount, 0, 100)
    out[..., 2] = lab[..., 2] + 2.5 * amount  # olheira é azulada: aquece um pouco
    return core.mix(rgb, core.lab_to_rgb(out), m)


def portrait(rgb, skin=0.5, eye=0.3, teeth_amt=0.0, dark_circles=0.0):
    """Retoque completo. Devolve (resultado, info)."""
    faces = segment.detect_faces(rgb)
    probs = segment.face_parse(rgb, faces)
    skin_m = segment.face_mask(rgb, ["skin", "nose", "neck"], probs)
    protect = segment.face_mask(rgb, ["l_eye", "r_eye", "l_brow", "r_brow", "u_lip", "l_lip", "mouth", "hair"], probs)
    skin_m = np.clip(skin_m - core.grow(protect, 2), 0, 1)
    out = rgb
    if skin > 0 and skin_m.mean() > 1e-4:
        out = skin_smooth(out, skin_m, skin)
        out = even_tone(out, skin_m, skin * 0.5)
    if dark_circles > 0:
        out = under_eyes(out, probs, dark_circles)
    if eye > 0:
        out = eyes(out, segment.face_mask(rgb, "olhos", probs), eye)
    if teeth_amt > 0:
        out = teeth(out, segment.face_mask(rgb, "boca", probs), teeth_amt)
    return np.clip(out, 0, 1).astype(np.float32), {"rostos": len(faces), "pele_%": round(float(skin_m.mean() * 100), 1)}
