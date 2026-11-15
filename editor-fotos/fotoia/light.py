"""Iluminação com preservação: transferência de luz, relighting generativo e
relighting físico (normais da profundidade), rim light e backlight.

Princípio: o modelo generativo só PROPÕE a nova luz em ~1 MP. A imagem final é
o original em resolução cheia multiplicado por um mapa suave de razão de
iluminação — textura, rosto, logotipos e nitidez continuam sendo os originais.
"""

from __future__ import annotations

import cv2
import numpy as np

from . import core

EPS = 0.004


def _masked_blur(x, w, sigma):
    """Desfoque normalizado pelo peso (não mistura fora da máscara)."""
    if w is None:
        return core.blur(x, sigma)
    num = core.blur(x * w[..., None], sigma)
    den = core.blur(w, sigma)[..., None]
    return num / np.maximum(den, 1e-4)


def transfer_light(
    orig, relit, alpha=None, detail=0.012, strength=1.0, chroma=1.0, highlights=0.0, limit=6.0, dark_limit=250.0
):
    """Aplica em `orig` (resolução cheia) a iluminação de `relit` (qualquer resolução).

    detail: escala do que conta como "iluminação", em fração do lado maior
        (menor = segue sombras/brilhos mais finos de `relit`; maior = mais conservador).
    strength: 0..1 intensidade da nova luz.
    chroma: 0 = só luminância; 1 = também a cor da luz.
    highlights: 0..1 soma brilhos especulares/rim novos que a razão suave não captura.
    alpha: restringe a estimativa ao assunto (não deixa o fundo vazar para dentro).
    """
    H, W = orig.shape[:2]
    h, w = relit.shape[:2]
    o_small = core.resize(orig, (w, h))
    a_small = None if alpha is None else np.clip(core.resize(alpha, (w, h), "linear"), 0, 1)
    lo, lr = core.srgb_to_linear(o_small), core.srgb_to_linear(relit)
    sigma = max(1.0, detail * max(h, w))
    wgt = None if a_small is None else np.clip(a_small, 0, 1) ** 2
    bo, br = _masked_blur(lo, wgt, sigma), _masked_blur(lr, wgt, sigma)
    # razão de luminância e razão de cor tratadas à parte: limitar por canal quebra a cor
    # (um canal satura no limite antes dos outros e a pele vira mancha colorida)
    yo, yr = core.luminance(bo) + EPS, core.luminance(br) + EPS
    yl = np.clip(yr / yo, 1.0 / dark_limit, limit)
    tint = np.clip(((br + EPS) / yr[..., None]) / ((bo + EPS) / yo[..., None]), 0.2, 5.0) ** chroma
    tint = tint / np.maximum(core.luminance(tint * (bo + EPS) / yo[..., None])[..., None], 1e-3)
    ratio = yl[..., None] * tint
    # alinha a razão às bordas reais do original (evita halos em contornos)
    ratio = core.guided(o_small, ratio, max(2, int(sigma * 0.75)), 1e-3)
    ratio = np.clip(ratio, 1.0 / (dark_limit * 2.5), limit * 2.5)

    extra = None
    if highlights > 0:
        pred = lo * ratio
        spec = np.clip(core.luminance(lr) - core.luminance(pred), 0, None)
        spec = np.clip(spec - 0.03, 0, None)  # ignora diferenças de textura
        spec = core.blur(spec, 1.2)
        tint = br / np.maximum(core.luminance(br)[..., None], EPS)
        extra = spec[..., None] * np.clip(tint, 0.3, 3.0) * highlights

    ratio_full = cv2.resize(ratio, (W, H), interpolation=cv2.INTER_CUBIC)
    if max(H, W) > 1.3 * max(h, w):  # upsampling guiado pelo original em resolução cheia
        ratio_full = core.guided(orig, ratio_full, max(2, int(round(2.0 * max(H, W) / max(h, w)))), 1e-3)
    ratio_full = np.clip(ratio_full, 1.0 / (dark_limit * 2.5), limit * 2.5)
    lin = core.srgb_to_linear(orig)
    out = lin * ratio_full
    if extra is not None:
        out = out + cv2.resize(extra, (W, H), interpolation=cv2.INTER_CUBIC).clip(0, None)
    out = core.linear_to_srgb(_soft_clip(out))
    if strength < 1.0:
        out = orig * (1 - strength) + out * strength
    return np.clip(out, 0, 1).astype(np.float32)


def _soft_clip(lin, knee=0.8):
    """Compressão suave das altas-luzes (evita estouro chapado depois de clarear)."""
    y = core.luminance(lin)
    over = y > knee
    if not over.any():
        return lin
    yc = np.where(over, knee + (1 - knee) * np.tanh((y - knee) / (1 - knee)), y)
    scale = yc / np.maximum(y, 1e-6)
    return lin * scale[..., None]


# --------------------------------------------------------------------------- relighting generativo

RELIGHT_PRESETS = {
    "estudio": "soft, even professional studio lighting from a large softbox at the front-left, gentle fill light, "
    "clean natural skin tones and true colors, subtle soft shadows",
    "rembrandt": "classic Rembrandt portrait lighting: a single warm key light from 45 degrees at the upper left, "
    "deep soft shadows on the opposite side, dark low-key mood",
    "cinematico": "cinematic lighting: warm tungsten key light from the side, cool teal fill in the shadows, "
    "moody contrast, film still look",
    "rim": "dramatic rim lighting: a strong bright backlight from behind outlining the edges of the subject with a "
    "glowing rim of light, the front softly lit, dark background",
    "backlight": "strong warm backlight from behind the subject, glowing light wrapping around the edges and hair, "
    "soft front fill so the face stays visible",
    "golden": "golden hour sunlight: low warm sun from the side, soft long shadows, warm glow on the highlights",
    "neon": "neon lighting: magenta light from the left and cyan light from the right, dark night ambience",
    "dramatico": "dramatic hard light from a single spotlight above and to the side, strong contrast, deep black shadows",
    "janela": "soft natural window light coming from the left side, gentle falloff, airy bright mood",
    "produto": "high-end commercial product lighting: large softbox overhead, crisp controlled reflections, "
    "a subtle rim light on both edges separating the product from the background",
}


def relight_prompt(desc, keep_background=True):
    desc = RELIGHT_PRESETS.get(str(desc).lower().strip(), desc)
    tail = (
        " Keep the subject, pose, framing, colors of objects and every detail exactly the same."
        if keep_background
        else " Keep the subject exactly the same."
    )
    return f"Relight this photo with {desc}. Change only the lighting.{tail}"


def relight_generative(rgb, desc, alpha=None, megapixels=1.0, seed=0, steps=4, **kw):
    """Relighting por instrução (FLUX.2 klein) + transferência de luz preservando o original.

    Devolve (resultado em resolução cheia, proposta crua do modelo).
    """
    from . import flux

    proposal = flux.edit(rgb, relight_prompt(desc), megapixels=megapixels, steps=steps, seed=seed)
    out = transfer_light(rgb, proposal, alpha=None, **kw)
    return out, proposal


# --------------------------------------------------------------------------- relighting físico (determinístico)


def normals_from_depth(depth, strength=1.0):
    """Normais (x direita, y cima, z câmera) a partir de um mapa de profundidade [0,1] (1 = perto)."""
    h, w = depth.shape
    d = core.blur(depth.astype(np.float32), max(1.0, max(h, w) / 600))
    scale = strength * max(h, w) / 6.0
    gx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3) * scale
    gy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3) * scale
    n = np.dstack([-gx, gy, np.ones_like(d)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def light_vector(direction, elevation=0.35):
    """'left', 'right', 'top', 'bottom', 'top-left', 'front', 'back-left'… ou ângulo em graus (0=direita, 90=cima)."""
    names = {
        "right": 0, "direita": 0, "top-right": 45, "top": 90, "cima": 90, "top-left": 135, "left": 180,
        "esquerda": 180, "bottom-left": 225, "bottom": 270, "baixo": 270, "bottom-right": 315,
    }  # fmt: skip
    s = str(direction).lower().strip()
    back = s.startswith("back")
    s = s.replace("back-", "").replace("back", "").strip() or "top"
    if s == "front":
        v = np.array([0, 0, 1.0])
    else:
        ang = np.deg2rad(names[s] if s in names else float(s))
        z = -0.6 if back else elevation
        v = np.array([np.cos(ang), np.sin(ang), z])
    return (v / np.linalg.norm(v)).astype(np.float32)


def shade(rgb, normals, direction="top-left", intensity=0.6, color="#ffffff", ambient=0.55, alpha=None, softness=0.5):
    """Luz direcional sobre as normais. Preserva textura (multiplicativo, em linear)."""
    L = light_vector(direction)
    ndl = (normals @ L).astype(np.float32)
    lam = np.clip((ndl + softness) / (1 + softness), 0, 1)  # wrap lighting
    c = core.srgb_to_linear(core.parse_color(color))
    gain = ambient + intensity * 1.6 * lam[..., None] * c
    lin = core.srgb_to_linear(rgb)
    out = core.linear_to_srgb(_soft_clip(lin * gain))
    if alpha is not None:
        out = core.mix(rgb, out, alpha)
    return np.clip(out, 0, 1).astype(np.float32)


def rim_light(rgb, alpha, normals=None, direction="back-left", color="#fff2e0", intensity=0.8, width=0.012, wrap=0.5):
    """Luz de recorte (rim/backlight) na borda do assunto voltada para a luz.

    Determinístico: usa a silhueta (alfa) e, se houver, as normais. Soma luz em
    espaço linear, modulada pela luminância local (não chapa sobre a textura).
    """
    h, w = alpha.shape
    px = max(1.5, width * max(h, w))
    L = light_vector(direction)
    a = np.clip(alpha, 0, 1).astype(np.float32)
    # normal 2D da silhueta: aponta para fora do assunto
    soft = core.blur(a, px)
    gx = -cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy) + 1e-6
    l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6)
    facing = (gx / mag) * l2[0] + (gy / mag) * l2[1]
    facing = np.clip((facing + wrap) / (1 + wrap), 0, 1)
    # faixa interna junto à borda: 1 na borda, 0 a ~2*px para dentro
    inner = np.clip((a - core.blur(a, px * 1.3)) * 3.0, 0, 1) * a
    rim = inner * facing
    if normals is not None:  # reforça onde a superfície realmente vira de lado
        graze = 1.0 - np.clip(normals[..., 2], 0, 1)
        rim = rim * (0.5 + 0.9 * graze)
    rim = core.blur(rim, max(0.8, px * 0.25))
    lin = core.srgb_to_linear(rgb)
    c = core.srgb_to_linear(core.parse_color(color))
    lum = core.luminance(lin)[..., None]
    add = rim[..., None] * c * intensity * (0.35 + 0.9 * np.sqrt(np.clip(lum, 0, 1)))
    glow = core.blur(rim, px * 2.5)[..., None] * c * intensity * 0.12 * a[..., None]
    out = core.linear_to_srgb(_soft_clip(lin + add + glow))
    return np.clip(out, 0, 1).astype(np.float32)


# --------------------------------------------------------------------------- contraluz em estúdio claro


def local_thickness(mask, dist=None, levels=9):
    """Meia-espessura local do assunto (raio do maior disco inscrito que cobre cada pixel)."""
    H, W = mask.shape
    sc = min(1.0, 512.0 / max(H, W))
    small = cv2.resize(mask.astype(np.uint8), (max(1, round(W * sc)), max(1, round(H * sc))), interpolation=cv2.INTER_NEAREST)
    dmax = float(cv2.distanceTransform(small, cv2.DIST_L2, 5).max())
    T = small.astype(np.float32) * 1.5
    if dmax > 2:
        for r in np.geomspace(2.0, dmax, levels):
            k = int(r) * 2 + 1
            opened = cv2.morphologyEx(small, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            T[opened > 0] = r
    T = cv2.resize(core.blur(T, 1.5), (W, H), interpolation=cv2.INTER_LINEAR) / sc
    return np.maximum(T, dist if dist is not None else 0).astype(np.float32)


def backlit(
    rgb, alpha, bg="#fbfbfb", rim=4.2, rim_width=0.0045, glow=0.55, haze=0.09, darken=-0.4, contrast=0.33,
    dodge_burn=0.65, clarity=0.4, texture=0.45, saturation=0.08, add=0.10, rim_color="#ffffff", top_bias=0.5,
):  # fmt: skip
    """Assunto em contraluz sobre fundo claro de estúdio (high-key), tudo determinístico.

    Os pixels do assunto são os originais: ganham definição (dodge & burn,
    claridade, textura, contraste), o miolo escurece um pouco para dar volume, e a
    borda acende com um rim calculado pela distância à silhueta — ganho
    multiplicativo (mantém a cor do material) mais um termo aditivo tingido pela
    cor local (acende também bordas que estavam em sombra). Uma névoa suave entra
    do contorno para dentro.

    bg: cor (ex. "#fbfbfb") ou imagem HxWx3 já sem o assunto.
    top_bias: 0 = rim uniforme; 1 = bem mais forte no alto do quadro.
    """
    from . import background
    from . import enhance as e

    H, W = rgb.shape[:2]
    L = max(H, W)
    # corta a franja de alfa muito baixo: sobre branco ela vira um contorno fantasma em volta do assunto
    a = np.clip((np.clip(alpha, 0, 1).astype(np.float32) - 0.10) / 0.88, 0, 1)
    from . import segment as _seg

    a = _seg.fill_small_holes(a)  # um furo de poucos px no matte vira clarão sob o rim
    if isinstance(bg, str):
        base_bg = core.srgb_to_linear(core.parse_color(bg))
        box = core.bbox(a, 0.5) or (0, 0, W, H)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        d2 = ((xx - cx) / L) ** 2 + ((yy - cy) / L) ** 2
        hot = 1.0 + 0.06 * np.exp(-d2 / 0.18)  # a fonte de luz fica atrás do assunto
        bg = core.linear_to_srgb(np.clip(base_bg[None, None, :] * hot[..., None], 0, 1))
    d = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    T = local_thickness(a > 0.5, d)  # meia-espessura local: dedos e braços recebem faixas mais estreitas
    inner = np.clip(d / np.maximum(0.45 * T, 1.0), 0, 1)
    inner = core.blur(inner * inner * (3 - 2 * inner), max(1.0, 0.004 * L)) * a
    s = e.dodge_burn(rgb, dodge_burn, radius=0.022) if dodge_burn else rgb
    s = e.clarity(s, clarity) if clarity else s
    s = e.texture(s, texture) if texture else s
    s = e.contrast(s, contrast) if contrast else s
    s = e.exposure(s, darken, mask=inner) if darken else s
    from . import segment

    # ilumina a CAMADA do assunto e só depois compõe: assim a franja antialiasada da borda
    # acende junto com o rim e se funde ao fundo (sem fio colorido por fora do brilho)
    lin = core.srgb_to_linear(segment.decontaminate(s, a))
    rows = np.mgrid[0:H, 0:W][0].astype(np.float32) / H
    top = np.clip(1.0 + top_bias * (0.5 - rows), 1 - top_bias * 0.55, 1 + top_bias * 0.5)[..., None]
    w_thin = np.minimum(rim_width * L, 0.16 * T)
    w_soft = np.minimum(rim_width * L * 4.5, 0.32 * T)
    r_thin = np.exp(-d / np.maximum(w_thin, 0.7))[..., None]
    r_soft = np.exp(-d / np.maximum(w_soft, 1.0))[..., None]
    local = _masked_blur(lin, a, 0.012 * L)
    # materiais claros estouram com o mesmo ganho que acende os escuros: compensa pela luminância local
    k = (1.0 / (1.0 + 7.0 * core.luminance(local)))[..., None]
    c = core.srgb_to_linear(core.parse_color(rim_color))
    lin = lin * (1 + (r_thin * rim + r_soft * rim * 0.28) * top * k) + r_thin * top * k * (local * rim * 0.9 + add) * c
    wrap = np.exp(-d / np.maximum(w_thin * 0.55, 0.6)) * glow
    veil = np.exp(-d / np.maximum(np.minimum(0.045 * L, 0.28 * T), 1.0)) * top[..., 0] * haze
    v = np.clip(wrap + veil, 0, 0.9)[..., None]
    lin = lin * (1 - v) + v * c
    lin = lin * a[..., None] + core.srgb_to_linear(bg) * (1 - a[..., None])
    out = core.linear_to_srgb(_soft_clip(lin, 0.9))
    if saturation:
        out = e.saturation(out, saturation, mask=a)
    return np.clip(out, 0, 1).astype(np.float32)
