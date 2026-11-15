"""Troca de cenário com o assunto original intacto.

Dois caminhos:
- procedural (cor, degradê, fundo infinito de estúdio, imagem fornecida) com
  sombra de contato e reflexo calculados;
- generativo (FLUX.2 klein): o modelo propõe a cena inteira (fundo, sombras,
  luz); o assunto final vem do original em resolução cheia, apenas com a luz
  da nova cena transferida de forma suave.
"""

from __future__ import annotations

import cv2
import numpy as np

from . import core, light, segment

# --------------------------------------------------------------------------- fundos procedurais


def solid(shape, color):
    c = core.parse_color(color)
    return np.broadcast_to(c, (shape[0], shape[1], 3)).astype(np.float32).copy()


def gradient(shape, top, bottom, angle=90.0):
    t = segment.gradient_mask(shape, angle)[..., None]
    a, b = core.srgb_to_linear(core.parse_color(top)), core.srgb_to_linear(core.parse_color(bottom))
    return core.linear_to_srgb(a * (1 - t) + b * t)


def studio(shape, color="#e6e6e8", horizon=0.68, vignette=0.35, spot=0.25, spot_center=(0.5, 0.42)):
    """Fundo infinito de estúdio: parede com foco de luz suave, curva e piso."""
    h, w = shape[:2]
    base = core.srgb_to_linear(core.parse_color(color))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    d = np.sqrt(((u - spot_center[0]) * (w / max(h, w)) * 1.6) ** 2 + ((v - spot_center[1]) * (h / max(h, w)) * 1.6) ** 2)
    wall = 1.0 + spot * np.exp(-((d / 0.45) ** 2)) - vignette * np.clip(d - 0.25, 0, None) ** 1.5
    # piso: um pouco mais claro perto da curva, escurece em direção à câmera
    t = np.clip((v - horizon) / max(1e-3, 1 - horizon), 0, 1)
    floor = 1.03 - 0.10 * t
    k = 1 / (1 + np.exp(-(v - horizon) / 0.035))  # transição suave parede->piso
    lum = wall * (1 - k) + wall * floor * k
    out = base[None, None, :] * lum[..., None]
    return core.linear_to_srgb(np.clip(out, 0, 4))


def fit_cover(img, shape):
    """Redimensiona/recorta uma imagem de fundo para cobrir o quadro."""
    h, w = shape[:2]
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = core.resize(img, (max(w, round(iw * s)), max(h, round(ih * s))))
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return np.ascontiguousarray(r[y0 : y0 + h, x0 : x0 + w])


# --------------------------------------------------------------------------- sombra e reflexo


def _base_row(alpha):
    rows = np.where(alpha.max(axis=1) > 0.5)[0]
    return int(rows.max()) if len(rows) else alpha.shape[0] - 1


def touches_bottom(alpha, margin=0.01):
    h = alpha.shape[0]
    return _base_row(alpha) >= h - 1 - int(h * margin)


def ground_shadow(alpha, direction=20.0, length=0.35, opacity=0.45, softness=1.0, contact=0.6):
    """Mapa de sombra [0,1] no chão: sombra projetada + sombra de contato.

    direction: graus; 0 = sombra cai para a direita, 90 = em direção à câmera,
    -90 = para trás do objeto. length: altura da sombra relativa à do objeto.
    """
    h, w = alpha.shape
    a = np.clip(alpha, 0, 1).astype(np.float32)
    yb = _base_row(a)
    box = core.bbox(a, 0.5)
    if box is None:
        return np.zeros_like(a)
    obj_h = max(8, box[3] - box[1])
    ang = np.deg2rad(direction)
    sx, sy = np.cos(ang) * length, np.sin(ang) * length
    # (x, y) -> (x + sx*(yb - y), yb + sy*(yb - y))
    M = np.float32([[1, -sx, sx * yb], [0, -sy, yb + sy * yb]])
    proj = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    # desfoque cresce com a distância da base: mistura de três níveis
    dist = np.clip(np.abs(np.mgrid[0:h, 0:w][0].astype(np.float32) - yb) / (obj_h * max(0.05, abs(sy)) + 1e-3), 0, 1)
    s0 = max(1.0, obj_h * 0.012 * softness)
    near, mid, far = core.blur(proj, s0), core.blur(proj, s0 * 4), core.blur(proj, s0 * 10)
    cast = np.where(dist < 0.5, near * (1 - dist * 2) + mid * dist * 2, mid * (2 - dist * 2) + far * (dist * 2 - 1))
    cast = cast * (1.0 - 0.55 * dist)
    # sombra de contato: faixa inferior do objeto, achatada e bem escura junto à base
    band = a.copy()
    band[: max(0, yb - int(obj_h * 0.10))] = 0
    Mc = np.float32([[1, 0, 0], [0, -0.25, yb + 0.25 * yb + obj_h * 0.004]])
    con = cv2.warpAffine(band, Mc, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    con = core.blur(con, max(1.0, obj_h * 0.02 * softness))
    con = np.clip(con * 2.2, 0, 1)
    sh = 1 - (1 - cast * opacity) * (1 - con * contact * opacity * 1.4)
    return np.clip(sh, 0, 1).astype(np.float32)


def reflection(rgb, alpha, opacity=0.25, fade=0.35, blur_px=None):
    """Reflexo do assunto num piso brilhante. Devolve (rgb_refletido, alfa_refletido)."""
    h, w = alpha.shape
    yb = _base_row(alpha)
    M = np.float32([[1, 0, 0], [0, -1, 2 * yb + 1]])
    r_rgb = cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    r_a = cv2.warpAffine(alpha, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    box = core.bbox(alpha, 0.5)
    obj_h = max(8, box[3] - box[1]) if box else h
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    falloff = np.clip(1 - (yy - yb) / (obj_h * fade), 0, 1) ** 1.5
    b = blur_px if blur_px is not None else max(0.8, obj_h * 0.006)
    return core.blur(r_rgb, b), core.blur(r_a * falloff * opacity, b)


# --------------------------------------------------------------------------- composição


def light_wrap(fg, alpha, bg, amount=0.15, width=0.01):
    """Luz do fundo 'abraçando' a borda do assunto (integra recorte e cenário)."""
    if amount <= 0:
        return fg
    px = max(1.5, width * max(alpha.shape))
    edge = np.clip(core.blur(1 - alpha, px) * alpha, 0, 1)[..., None] * amount * 2.0
    glow = core.blur(bg, px * 2)
    lin = core.srgb_to_linear(fg) * (1 - edge) + core.srgb_to_linear(glow) * edge
    return core.linear_to_srgb(lin)


def compose(fg, alpha, bg, shadow=None, shadow_color="#000000", refl=None, wrap=0.0, decontaminate=True):
    """Assunto (cores originais) sobre o fundo, em espaço linear."""
    fgc = segment.decontaminate(fg, alpha) if decontaminate else fg
    scene = core.srgb_to_linear(bg)
    if refl is not None:
        r_rgb, r_a = refl
        scene = scene * (1 - r_a[..., None]) + core.srgb_to_linear(r_rgb) * r_a[..., None]
    if shadow is not None:
        sc = core.srgb_to_linear(core.parse_color(shadow_color))
        scene = scene * (1 - shadow[..., None] * (1 - sc))  # multiplica em direção à cor da sombra
    if wrap > 0:
        fgc = light_wrap(fgc, alpha, core.linear_to_srgb(scene), wrap)
    a = alpha[..., None]
    out = core.srgb_to_linear(fgc) * a + scene * (1 - a)
    return np.clip(core.linear_to_srgb(out), 0, 1).astype(np.float32)


def harmonize_classic(fg, alpha, bg, amount=0.25):
    """Aproxima sutilmente a cor/contraste do assunto ao cenário (Reinhard parcial em Lab)."""
    if amount <= 0:
        return fg
    lab_f, lab_b = core.rgb_to_lab(fg), core.rgb_to_lab(bg)
    wf = alpha > 0.5
    wb = alpha < 0.2
    if wf.sum() < 100 or wb.sum() < 100:
        return fg
    out = lab_f.copy()
    for c, k in ((1, amount), (2, amount), (0, amount * 0.3)):
        mf, mb = lab_f[..., c][wf].mean(), lab_b[..., c][wb].mean()
        out[..., c] = lab_f[..., c] + (mb - mf) * k * (0.5 if c == 0 else 1.0)
    return core.mix(fg, core.lab_to_rgb(out), np.clip(alpha, 0, 1))


def replace_procedural(
    rgb, alpha, kind="studio", color="#e6e6e8", color2=None, image=None, shadow=True, shadow_opacity=0.45,
    shadow_direction=20.0, shadow_length=0.3, reflect=0.0, wrap=0.08, harmonize=0.0,
):  # fmt: skip
    """Fundo novo sem IA generativa: cor chapada, degradê, estúdio ou imagem."""
    shape = rgb.shape
    if kind in ("solid", "cor"):
        bg = solid(shape, color)
    elif kind in ("gradient", "degrade"):
        bg = gradient(shape, color, color2 or "#ffffff")
    elif kind in ("studio", "estudio"):
        bg = studio(shape, color)
    elif kind in ("image", "imagem"):
        bg = fit_cover(image, shape)
    else:
        raise ValueError(kind)
    grounded = not touches_bottom(alpha)
    sh = ground_shadow(alpha, shadow_direction, shadow_length, shadow_opacity) if (shadow and grounded) else None
    rf = reflection(rgb, alpha, reflect) if (reflect > 0 and grounded) else None
    fg = harmonize_classic(rgb, alpha, bg, harmonize)
    return compose(fg, alpha, bg, shadow=sh, refl=rf, wrap=wrap)


# --------------------------------------------------------------------------- caminho generativo


def background_prompt(desc, subject="subject"):
    return (
        f"Change the background to {desc}. Keep the {subject} exactly the same: same position, size, shape, "
        f"colors and details. Photorealistic, with natural lighting, shadows and reflections matching the new scene."
    )


def fill_behind(bg, alpha, px=None):
    """Reconstrói o fundo numa faixa em volta do assunto (remove 'fantasmas' da borda)."""
    h, w = alpha.shape
    px = int(px or max(3, round(0.008 * max(h, w))))
    hard = (alpha > 0.03).astype(np.uint8)
    ring = cv2.dilate(hard, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)))
    core_in = cv2.erode((alpha > 0.97).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    region = ((ring > 0) & (core_in == 0)).astype(np.uint8) * 255
    bgr = cv2.cvtColor(core.to_u8(bg, dither=False), cv2.COLOR_RGB2BGR)
    fixed = cv2.inpaint(bgr, region, max(3, px // 2), cv2.INPAINT_TELEA)
    out = cv2.cvtColor(fixed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return core.mix(bg, out, core.feather((region > 0).astype(np.float32), 1.0))


def align_to(proposal, alpha_ref, alpha_prop):
    """Alinha a proposta do modelo à geometria do original (ECC afim sobre os alfas).

    Devolve (proposta alinhada, deslocamento em px, IoU antes do alinhamento).
    """
    a, b = (alpha_ref > 0.5), (alpha_prop > 0.5)
    iou = float((a & b).sum() / max(1, (a | b).sum()))
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5)
        ref, mov = core.blur(alpha_ref.astype(np.float32), 2), core.blur(alpha_prop.astype(np.float32), 2)
        _, warp = cv2.findTransformECC(ref, mov, warp, cv2.MOTION_AFFINE, crit, None, 5)
    except cv2.error:
        return proposal, 0.0, iou
    h, w = alpha_ref.shape
    shift = float(np.hypot(warp[0, 2], warp[1, 2]) + abs(warp[0, 0] - 1) * w + abs(warp[1, 1] - 1) * h)
    if shift < 0.4 or shift > 0.2 * max(h, w):
        return proposal, shift, iou
    out = cv2.warpAffine(
        proposal, warp, (w, h), flags=cv2.INTER_LANCZOS4 + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT
    )
    return np.clip(out, 0, 1), shift, iou


def replace_generative(
    rgb, alpha, desc, subject="subject", megapixels=1.0, seed=0, steps=4, harmonize=0.7, detail=0.02,
    wrap=0.05, prompt=None, proposal=None, upscaler=None,
):  # fmt: skip
    """Cenário novo por IA com o assunto original preservado.

    O modelo repinta só o fundo com os latentes do assunto travados (ele não se
    move nem muda de forma); depois o assunto do original, em resolução cheia, é
    composto por cima.
    harmonize: 0 = assunto idêntico ao original; 1 = recebe toda a luz que o modelo
    pôs nas bordas (sempre só a componente suave — a textura é a original).
    upscaler: função rgb->rgb opcional para dar nitidez ao fundo em fotos grandes.
    Devolve (resultado, proposta do modelo, info).
    """
    from . import flux

    H, W = rgb.shape[:2]
    if proposal is None:
        bgmask = 1 - core.grow((alpha > 0.5).astype(np.float32), -max(2, int(0.003 * max(H, W))))
        proposal = flux.repaint(
            rgb, bgmask, prompt or background_prompt(desc, subject), megapixels=megapixels, steps=steps, seed=seed
        )
    h, w = proposal.shape[:2]
    if upscaler is not None and max(H, W) > 1.4 * max(h, w):
        bg = core.resize(upscaler(proposal), (W, H))
    else:
        bg = core.resize(proposal, (W, H))
    fg = rgb
    if harmonize > 0:
        fg = light.transfer_light(rgb, proposal, alpha=alpha, detail=detail, strength=harmonize, highlights=0.5)
    out = compose(fg, alpha, bg, wrap=wrap)
    return out, proposal, {"trabalho": f"{w}x{h}"}
