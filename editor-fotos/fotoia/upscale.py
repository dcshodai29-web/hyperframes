"""Upscale e restauração: Real-ESRGAN / DAT2 via spandrel (em blocos), restauração
de rostos opcional (GFPGAN) e refino de detalhe por difusão (SD1.5 + ControlNet tile)."""

from __future__ import annotations

import cv2
import numpy as np

from . import core, models

_cache = {}

FFHQ_5PT = np.float32(
    [[192.98138, 239.94708], [318.90277, 240.1936], [256.63416, 314.01935], [201.26117, 371.41043], [313.08905, 371.15118]]
)


def _load(key):
    if key not in _cache:
        torch, _ = core.torch_setup()
        import spandrel

        try:
            import spandrel_extra_arches

            spandrel_extra_arches.install()
        except Exception:
            pass
        _cache.clear()
        desc = spandrel.ModelLoader(device="cpu").load_from_file(models.path(key))
        desc.model.eval()
        _cache[key] = desc
    return _cache[key]


def _run(desc, x, dtype):
    torch, _ = core.torch_setup()
    net = desc.model
    with torch.inference_mode():
        y = net.to(dtype)(x.to(dtype))
    return y.float().clamp(0, 1)


def upscale(rgb, model="realesrgan-x4plus", scale=None, tile=320, overlap=24, dtype=None):
    """Amplia com super-resolução. `scale` final arbitrária (padrão: a do modelo).

    Processa em blocos com sobreposição e mistura suave (sem emendas), então a
    RAM não cresce com o tamanho da foto.
    """
    torch, fast = core.torch_setup()
    desc = _load(model)
    s = int(desc.scale)
    # Real-ESRGAN é só convolução: bf16 (AMX) acelera muito sem diferença visível.
    # Transformers de SR (DAT) ficam em float32 por estabilidade numérica.
    dtype = dtype or (fast if "esr" in model else torch.float32)
    h, w = rgb.shape[:2]
    out = np.zeros((h * s, w * s, 3), dtype=np.float32)
    acc = np.zeros((h * s, w * s, 1), dtype=np.float32)
    step = max(16, tile - overlap)
    ys = sorted(set([*range(0, max(1, h - tile + 1), step), max(0, h - tile)]))
    xs = sorted(set([*range(0, max(1, w - tile + 1), step), max(0, w - tile)]))
    total = len(ys) * len(xs)
    with core.Timer(f"upscale {model} {w}x{h} -> {w * s}x{h * s} ({total} blocos)"):
        for y in ys:
            for x in xs:
                patch = rgb[y : y + tile, x : x + tile]
                ph, pw = patch.shape[:2]
                t = torch.from_numpy(np.ascontiguousarray(patch.transpose(2, 0, 1)))[None]
                pad_h, pad_w = (-ph) % 8, (-pw) % 8
                if pad_h or pad_w:
                    t = torch.nn.functional.pad(t, (0, pad_w, 0, pad_h), mode="reflect")
                o = _run(desc, t, dtype)[0, :, : ph * s, : pw * s].numpy().transpose(1, 2, 0)
                wy = _ramp(ph * s, overlap * s, y > 0, y + ph < h)
                wx = _ramp(pw * s, overlap * s, x > 0, x + pw < w)
                wgt = (wy[:, None] * wx[None, :])[..., None]
                out[y * s : (y + ph) * s, x * s : (x + pw) * s] += o * wgt
                acc[y * s : (y + ph) * s, x * s : (x + pw) * s] += wgt
    out /= np.maximum(acc, 1e-6)
    if scale and abs(scale - s) > 1e-3:
        out = core.resize(out, (int(round(w * scale)), int(round(h * scale))))
    return np.clip(out, 0, 1).astype(np.float32)


def _ramp(n, ov, lead, trail):
    wgt = np.ones(n, dtype=np.float32)
    ov = min(ov, n // 2)
    if ov > 0:
        r = np.linspace(0.02, 1, ov, dtype=np.float32)
        if lead:
            wgt[:ov] = r
        if trail:
            wgt[-ov:] = r[::-1]
    return wgt


def upscale_to(rgb, long_side=None, megapixels=None, scale=None, model=None, fidelity=0.0):
    """Atalho: escolhe o modelo e entrega no tamanho pedido.

    fidelity 0..1 mistura de volta as baixas frequências do original ampliado
    (cor e tons idênticos; o modelo contribui só com detalhe fino).
    """
    h, w = rgb.shape[:2]
    if scale is None:
        if long_side:
            scale = long_side / max(h, w)
        elif megapixels:
            scale = (megapixels * 1e6 / (h * w)) ** 0.5
        else:
            scale = 2.0
    if scale <= 1.0:
        return core.resize(rgb, (round(w * scale), round(h * scale)))
    model = model or ("realesrgan-x2plus" if scale <= 2.0 else "realesrgan-x4plus")
    out = upscale(rgb, model, scale=scale)
    if fidelity > 0:
        out = lock_tones(out, rgb, fidelity)
    return out


def lock_tones(up, orig, amount=1.0, sigma_rel=0.004):
    """Mantém cor/tonalidade do original: troca as baixas frequências do upscale pelas dele."""
    H, W = up.shape[:2]
    ref = core.resize(orig, (W, H), "cubic")
    sigma = max(1.5, sigma_rel * max(H, W))
    fixed = up - core.blur(up, sigma) + core.blur(ref, sigma)
    return np.clip(up * (1 - amount) + fixed * amount, 0, 1).astype(np.float32)


# --------------------------------------------------------------------------- rostos


def restore_faces(rgb, strength=0.5, max_faces=6):
    """Restaura rostos com GFPGAN e mistura com o original (strength 0..1).

    Altera identidade se abusar: use só quando o pedido for recuperar um rosto
    degradado; mantenha strength <= 0.6 e confira o resultado.
    """
    torch, _ = core.torch_setup()
    from . import segment

    faces = segment.detect_faces(rgb)[:max_faces]
    if not faces:
        return rgb, 0
    desc = _load("gfpgan")
    out = rgb.copy()
    for *_, lm in faces:
        M, _ = cv2.estimateAffinePartial2D(lm, FFHQ_5PT, method=cv2.LMEDS)
        if M is None:
            continue
        crop = cv2.warpAffine(out, M, (512, 512), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        t = torch.from_numpy(np.ascontiguousarray(crop.transpose(2, 0, 1)))[None]
        with torch.inference_mode():
            r = desc.model.float()(t.float())
        r = r[0] if isinstance(r, (tuple, list)) else r
        if r.min() < -0.2:  # saída em [-1, 1]
            r = (r + 1) / 2
        rest = r.float().clamp(0, 1)[0].numpy().transpose(1, 2, 0)
        mask = np.zeros((512, 512), dtype=np.float32)
        cv2.ellipse(mask, (256, 262), (165, 205), 0, 0, 360, 1.0, -1)
        mask = core.blur(mask, 22) * strength
        Mi = cv2.invertAffineTransform(M)
        h, w = rgb.shape[:2]
        back = cv2.warpAffine(rest, Mi, (w, h), flags=cv2.INTER_LINEAR)
        mback = cv2.warpAffine(mask, Mi, (w, h), flags=cv2.INTER_LINEAR)
        out = core.mix(out, back, mback)
    return out, len(faces)


# --------------------------------------------------------------------------- refino de detalhe por difusão


def refine_detail(rgb, strength=0.3, prompt=None, tile=768, overlap=96, steps=20, cn_scale=1.0, seed=0, mask=None):
    """Recupera microdetalhe/textura com SD1.5 + ControlNet tile (img2img em blocos).

    A ControlNet tile prende a estrutura à imagem original; `strength` (0.15-0.45)
    controla quanto detalhe novo é sintetizado. As baixas frequências do original
    são travadas no final, então cor e luz não mudam.
    """
    torch, dt = core.torch_setup()
    from diffusers import ControlNetModel, DPMSolverMultistepScheduler, StableDiffusionControlNetImg2ImgPipeline

    _cache.clear()
    cn = ControlNetModel.from_single_file(models.path("controlnet-tile"), torch_dtype=dt)
    pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
        models.path("sd15-realistic"), controlnet=cn, torch_dtype=dt, safety_checker=None,
        feature_extractor=None, requires_safety_checker=False,
    )  # fmt: skip
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
    pipe.set_progress_bar_config(disable=True)
    prompt = prompt or "RAW photo, ultra detailed, sharp focus, natural texture, high resolution photograph"
    neg = "blurry, lowres, artifacts, jpeg artifacts, oversharpened, cartoon, painting, deformed, text, watermark"
    h, w = rgb.shape[:2]
    out = np.zeros_like(rgb)
    acc = np.zeros((h, w, 1), dtype=np.float32)
    tile = min(tile, (min(h, w) // 8) * 8) if min(h, w) >= 512 else tile
    step = max(64, tile - overlap)
    ys = sorted(set([*range(0, max(1, h - tile + 1), step), max(0, h - tile)]))
    xs = sorted(set([*range(0, max(1, w - tile + 1), step), max(0, w - tile)]))
    with core.Timer(f"refino de detalhe {w}x{h} ({len(ys) * len(xs)} blocos, força {strength})"):
        for y in ys:
            for x in xs:
                patch = rgb[y : y + tile, x : x + tile]
                ph, pw = patch.shape[:2]
                if mask is not None and mask[y : y + ph, x : x + pw].max() < 0.02:
                    o = patch
                else:
                    gh, gw = (ph // 8) * 8, (pw // 8) * 8
                    pil = core.to_pil(core.resize(patch, (gw, gh)))
                    with torch.inference_mode():
                        r = pipe(
                            prompt=prompt, negative_prompt=neg, image=pil, control_image=pil, strength=strength,
                            num_inference_steps=steps, guidance_scale=5.0, controlnet_conditioning_scale=cn_scale,
                            generator=torch.Generator().manual_seed(seed),
                        ).images[0]  # fmt: skip
                    o = core.resize(core.from_pil(r), (pw, ph))
                wy = _ramp(ph, overlap, y > 0, y + ph < h)
                wx = _ramp(pw, overlap, x > 0, x + pw < w)
                wgt = (wy[:, None] * wx[None, :])[..., None]
                out[y : y + ph, x : x + pw] += o * wgt
                acc[y : y + ph, x : x + pw] += wgt
    out /= np.maximum(acc, 1e-6)
    out = lock_tones(out, rgb, 1.0, sigma_rel=0.006)
    if mask is not None:
        out = core.mix(rgb, out, mask)
    del pipe, cn
    return np.clip(out, 0, 1).astype(np.float32)
