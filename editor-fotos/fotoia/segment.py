"""Segmentação e matting: assunto (BiRefNet), ponto/caixa (SAM 2.1), texto
(Grounding DINO + SAM 2.1), rosto (YuNet + face-parsing) e operações de máscara."""

from __future__ import annotations

import cv2
import numpy as np

from . import core, models

_cache = {}


def _free(*keep):
    """Libera modelos carregados (a RAM é curta; um modelo pesado por vez)."""
    import gc

    for k in list(_cache):
        if k not in keep:
            del _cache[k]
    gc.collect()


# --------------------------------------------------------------------------- assunto (BiRefNet)

_BIREF_RES = {"birefnet": 1024, "birefnet-hr": 2048, "birefnet-matting": 2048}


def _birefnet(key):
    if key not in _cache:
        torch, dt = core.torch_setup()
        from transformers import AutoModelForImageSegmentation

        _free()
        m = AutoModelForImageSegmentation.from_pretrained(models.path(key), trust_remote_code=True)
        _patch_deform_conv(m)
        _cache[key] = m.eval().to(dt)
    return _cache[key]


def _patch_deform_conv(model):
    """deform_conv2d não existe em bfloat16 na CPU: roda só essa operação em float32."""
    import sys

    import torch

    mod = sys.modules.get(type(model).__module__)
    orig = getattr(mod, "deform_conv2d", None)
    if orig is None or getattr(orig, "_fotoia", False):
        return

    def f32(v):
        return v.float() if torch.is_tensor(v) else v

    def deform_conv2d(input, offset, weight, bias=None, **kw):
        out = orig(f32(input), f32(offset), f32(weight), f32(bias), **{k: f32(v) for k, v in kw.items()})
        return out.to(input.dtype)

    deform_conv2d._fotoia = True
    mod.deform_conv2d = deform_conv2d


def matte_subject(rgb, model="auto", res=None, refine=True):
    """Alfa do assunto principal. `refine` alinha a borda à imagem em resolução cheia.

    model="auto": BiRefNet 1024 (~25 s) para fotos pequenas, BiRefNet_HR 2048 (~90 s)
    quando o lado maior passa de 1600 px.
    """
    torch, dt = core.torch_setup()
    if model == "auto":
        model = "birefnet-hr" if max(rgb.shape[:2]) > 1600 else "birefnet"
    net = _birefnet(model)
    res = int(res or _BIREF_RES.get(model, 1024))
    h, w = rgb.shape[:2]
    x = core.resize(rgb, (res, res), "area" if max(h, w) > res else "cubic")
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    t = torch.from_numpy(((x - mean) / std).transpose(2, 0, 1)[None]).to(dt)
    with torch.inference_mode():
        pred = net(t)[-1].sigmoid().float()[0, 0].numpy()
    alpha = cv2.resize(pred, (w, h), interpolation=cv2.INTER_LINEAR)
    if refine:
        alpha = refine_alpha(rgb, alpha)
    return np.clip(alpha, 0, 1).astype(np.float32)


def refine_alpha(rgb, alpha, radius=None, eps=1e-4):
    """Refina só a faixa de transição com filtro guiado (preserva miolo e fundo)."""
    h, w = alpha.shape
    r = int(radius or max(2, round(max(h, w) / 700)))
    g = core.guided(rgb, alpha, r, eps)
    band = ((alpha > 0.02) & (alpha < 0.98)).astype(np.float32)
    band = core.feather(core.grow(band, r), r)
    out = alpha * (1 - band) + g * band
    # limpa resíduos: quase-0 -> 0, quase-1 -> 1
    out = np.clip((out - 0.02) / 0.96, 0, 1)
    return out.astype(np.float32)


def decontaminate(rgb, alpha):
    """Estima a cor real do primeiro plano na borda (remove halo do fundo antigo)."""
    from pymatting import estimate_foreground_ml

    h, w = alpha.shape
    box = core.bbox(alpha, 0.01, pad=8)
    if box is None:
        return rgb
    x0, y0, x1, y1 = box
    sub = rgb[y0:y1, x0:x1].astype(np.float64)
    a = alpha[y0:y1, x0:x1].astype(np.float64)
    fg = estimate_foreground_ml(sub, a).astype(np.float32)
    out = rgb.copy()
    # só altera a faixa semitransparente; o interior opaco fica idêntico ao original
    edge = ((a > 0.0) & (a < 0.995)).astype(np.float32)[..., None]
    out[y0:y1, x0:x1] = sub.astype(np.float32) * (1 - edge) + np.clip(fg, 0, 1) * edge
    return out


# --------------------------------------------------------------------------- SAM 2.1


def _sam():
    if "sam2" not in _cache:
        torch, _ = core.torch_setup()
        from transformers import Sam2Model, Sam2Processor

        _free("gdino")
        p = models.path("sam2")
        _cache["sam2"] = (Sam2Processor.from_pretrained(p), Sam2Model.from_pretrained(p).eval())
    return _cache["sam2"]


def sam(rgb, points=None, labels=None, boxes=None, multimask=True):
    """Máscara por pontos e/ou caixas (coordenadas em pixels da imagem).

    points: [(x, y), ...] de um mesmo objeto; labels: 1 = incluir, 0 = excluir.
    boxes: [(x0, y0, x1, y1), ...] — uma máscara por caixa, unidas no retorno.
    """
    torch, _ = core.torch_setup()
    proc, model = _sam()
    pil = core.to_pil(rgb)
    kw = {}
    if boxes:
        kw["input_boxes"] = [[list(map(float, b)) for b in boxes]]
        if points:  # um conjunto de pontos por caixa não é suportado aqui: aplica a todas
            kw["input_points"] = [[[list(map(float, p)) for p in points] for _ in boxes]]
            kw["input_labels"] = [[list(labels or [1] * len(points)) for _ in boxes]]
    elif points:
        kw["input_points"] = [[[list(map(float, p)) for p in points]]]
        kw["input_labels"] = [[list(labels or [1] * len(points))]]
    else:
        raise ValueError("Informe points e/ou boxes")
    inputs = proc(images=pil, return_tensors="pt", **kw)
    with torch.inference_mode():
        out = model(**inputs, multimask_output=multimask)
    masks = proc.post_process_masks(out.pred_masks.cpu(), inputs["original_sizes"], binarize=False)[0]
    scores = out.iou_scores[0].float().numpy()  # [objetos, candidatos]
    masks = masks.float().numpy()  # [objetos, candidatos, H, W] (logits)
    union = np.zeros(rgb.shape[:2], dtype=np.float32)
    for i in range(masks.shape[0]):
        j = int(np.argmax(scores[i]))
        m = 1.0 / (1.0 + np.exp(-np.clip(masks[i, j], -30, 30)))
        union = np.maximum(union, m.astype(np.float32))
    return union


# --------------------------------------------------------------------------- texto -> caixas -> máscara


def _gdino():
    if "gdino" not in _cache:
        torch, _ = core.torch_setup()
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        _free("sam2")
        p = models.path("grounding-dino")
        _cache["gdino"] = (
            AutoProcessor.from_pretrained(p),
            AutoModelForZeroShotObjectDetection.from_pretrained(p).eval(),
        )
    return _cache["gdino"]


def ground(rgb, text, threshold=0.3, text_threshold=0.25, max_boxes=8):
    """Localiza por texto (inglês funciona melhor). Devolve [(caixa, score, rótulo)]."""
    torch, _ = core.torch_setup()
    proc, model = _gdino()
    pil = core.to_pil(rgb)
    query = ". ".join(s.strip().lower() for s in text.replace(";", ".").split(".") if s.strip()) + "."
    inputs = proc(images=pil, text=query, return_tensors="pt")
    with torch.inference_mode():
        out = model(**inputs)
    res = proc.post_process_grounded_object_detection(
        out, inputs.input_ids, threshold=threshold, text_threshold=text_threshold, target_sizes=[pil.size[::-1]]
    )[0]
    labels = res.get("text_labels", res.get("labels"))
    found = [
        (tuple(float(v) for v in b), float(s), str(lab))
        for b, s, lab in zip(res["boxes"].tolist(), res["scores"].tolist(), labels)
    ]
    found.sort(key=lambda r: -r[1])
    return found[:max_boxes]


def segment_text(rgb, text, threshold=0.3, max_boxes=8):
    """Máscara de tudo o que corresponde ao texto. Devolve (máscara, detecções)."""
    det = ground(rgb, text, threshold=threshold, max_boxes=max_boxes)
    if not det:
        return np.zeros(rgb.shape[:2], dtype=np.float32), det
    mask = sam(rgb, boxes=[d[0] for d in det], multimask=True)
    return mask, det


# --------------------------------------------------------------------------- rostos


def detect_faces(rgb, score=0.6):
    """[(x, y, w, h, score, landmarks 5x2)] em pixels da imagem original."""
    h, w = rgb.shape[:2]
    s = min(1.0, 1280.0 / max(h, w))
    small = core.resize(rgb, (round(w * s), round(h * s)), "area") if s < 1 else rgb
    bgr = cv2.cvtColor(core.to_u8(small, dither=False), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(models.path("yunet"), "", (bgr.shape[1], bgr.shape[0]), score, 0.3, 50)
    _, faces = det.detect(bgr)
    out = []
    if faces is not None:
        for f in faces:
            x, y, fw, fh = (f[:4] / s).tolist()
            lm = (f[4:14].reshape(5, 2) / s).astype(np.float32)
            out.append((x, y, fw, fh, float(f[14]), lm))
    out.sort(key=lambda f: -f[2] * f[3])
    return out


FACE_LABELS = {
    "background": 0, "skin": 1, "nose": 2, "glasses": 3, "l_eye": 4, "r_eye": 5, "l_brow": 6, "r_brow": 7,
    "l_ear": 8, "r_ear": 9, "mouth": 10, "u_lip": 11, "l_lip": 12, "hair": 13, "hat": 14, "earring": 15,
    "necklace": 16, "neck": 17, "cloth": 18,
}  # fmt: skip
FACE_GROUPS = {
    "pele": ["skin", "nose", "neck", "l_ear", "r_ear"],
    "rosto": ["skin", "nose", "l_eye", "r_eye", "l_brow", "r_brow", "mouth", "u_lip", "l_lip"],
    "olhos": ["l_eye", "r_eye"],
    "sobrancelhas": ["l_brow", "r_brow"],
    "labios": ["u_lip", "l_lip"],
    "boca": ["mouth"],
    "cabelo": ["hair"],
    "roupa": ["cloth"],
    "acessorios": ["glasses", "earring", "necklace", "hat"],
}


def _faceparser():
    if "faceparse" not in _cache:
        torch, _ = core.torch_setup()
        from transformers import SegformerForSemanticSegmentation

        _free("sam2", "gdino")
        _cache["faceparse"] = SegformerForSemanticSegmentation.from_pretrained(models.path("face-parsing")).eval()
    return _cache["faceparse"]


def face_parse(rgb, faces=None, pad=0.6):
    """Mapa de probabilidades por classe (19 x H x W), fundindo todos os rostos."""
    torch, _ = core.torch_setup()
    net = _faceparser()
    h, w = rgb.shape[:2]
    faces = detect_faces(rgb) if faces is None else faces
    probs = np.zeros((19, h, w), dtype=np.float32)
    probs[0] = 1.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    boxes = []
    for x, y, fw, fh, *_ in faces:
        side = max(fw, fh) * (1 + 2 * pad)
        cx, cy = x + fw / 2, y + fh / 2 - fh * 0.05
        boxes.append((int(max(0, cx - side / 2)), int(max(0, cy - side / 2)),
                      int(min(w, cx + side / 2)), int(min(h, cy + side / 2))))  # fmt: skip
    if not boxes:  # close-up extremo: o detector falha, mas o parser entende a imagem inteira
        boxes = [(0, 0, w, h)]
    for x0, y0, x1, y1 in boxes:
        if x1 - x0 < 16 or y1 - y0 < 16:
            continue
        crop = core.resize(rgb[y0:y1, x0:x1], (512, 512))
        t = torch.from_numpy(((crop - mean) / std).transpose(2, 0, 1)[None])
        with torch.inference_mode():
            logits = net(pixel_values=t).logits
            logits = torch.nn.functional.interpolate(logits, size=(y1 - y0, x1 - x0), mode="bilinear")
            p = logits.softmax(1)[0].numpy()
        region = probs[:, y0:y1, x0:x1]
        take = p[0] < region[0]  # onde este rosto tem menos "fundo"
        region[:, take] = p[:, take]
    return probs


def face_mask(rgb, parts="pele", probs=None):
    """Máscara de partes do rosto: nomes de FACE_GROUPS ou rótulos de FACE_LABELS."""
    probs = face_parse(rgb) if probs is None else probs
    names = []
    for p in (parts if isinstance(parts, (list, tuple)) else str(parts).split(",")):
        p = p.strip().lower()
        names += FACE_GROUPS.get(p, [p])
    m = np.zeros(probs.shape[1:], dtype=np.float32)
    for n in names:
        if n not in FACE_LABELS:
            raise KeyError(f"Parte desconhecida: {n}. Use {list(FACE_GROUPS)} ou {list(FACE_LABELS)}")
        m += probs[FACE_LABELS[n]]
    return np.clip(m, 0, 1)


# --------------------------------------------------------------------------- máscaras utilitárias


def combine(a, b, op="union"):
    if op in ("union", "uniao", "+"):
        return np.maximum(a, b)
    if op in ("intersect", "intersecao", "*"):
        return np.minimum(a, b)
    if op in ("subtract", "subtrair", "-"):
        return np.clip(a - b, 0, 1)
    raise ValueError(op)


def box_mask(shape, box, feather=0):
    m = np.zeros(shape[:2], dtype=np.float32)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    m[max(0, y0) : y1, max(0, x0) : x1] = 1.0
    return core.feather(m, feather)


def gradient_mask(shape, angle=90.0, start=0.0, end=1.0):
    """Degradê linear (filtro graduado). angle=90: de cima (0) para baixo (1)."""
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(angle)
    t = (xx / max(1, w - 1)) * np.cos(a) + (yy / max(1, h - 1)) * np.sin(a)
    t = (t - t.min()) / max(1e-6, t.max() - t.min())
    return np.clip((t - start) / max(1e-6, end - start), 0, 1).astype(np.float32)


def radial_mask(shape, center=(0.5, 0.5), radius=0.5, softness=0.5):
    """Máscara elíptica suave (filtro radial). center/radius relativos à imagem."""
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - center[0]) / radius) ** 2 + ((yy / h - center[1]) / radius) ** 2)
    return np.clip((1.0 - d) / max(1e-6, softness), 0, 1).astype(np.float32)


def luminosity_mask(rgb, lo=0.0, hi=1.0, soft=0.1):
    """Máscara de luminosidade (ex.: só altas-luzes lo=0.7, só sombras hi=0.3)."""
    lum = core.rgb_to_lab(rgb)[..., 0] / 100.0
    a = np.clip((lum - (lo - soft)) / max(1e-6, soft), 0, 1)
    b = np.clip(((hi + soft) - lum) / max(1e-6, soft), 0, 1)
    return (a * b).astype(np.float32)
