"""Base: E/S de imagens com gestão de cor, espaço linear, máscaras, pastas de trabalho."""

from __future__ import annotations

import io
import json
import os
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageOps

try:  # HEIC/HEIF (iPhone)
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - opcional
    pass

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
ROOT = Path(__file__).resolve().parent.parent
SAIDAS = Path(os.environ.get("FOTOIA_SAIDAS", ROOT / "saidas"))
ENTRADAS = Path(os.environ.get("FOTOIA_ENTRADAS", ROOT / "entradas"))
CACHE = Path(os.environ.get("FOTOIA_CACHE", Path.home() / ".cache" / "fotoia"))

_SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


# --------------------------------------------------------------------------- torch


def torch_setup():
    """Configura o torch para CPU e devolve (torch, dtype rápido).

    Em CPUs com AMX/AVX512-BF16 (Sapphire Rapids+), bfloat16 é 4-8x mais rápido
    que float32; nas demais usamos float32.
    """
    import torch

    torch.set_grad_enabled(False)
    torch.set_num_threads(os.cpu_count() or 4)
    return torch, fast_dtype()


def fast_dtype():
    import torch

    if torch.cuda.is_available():
        return torch.bfloat16
    try:
        flags = Path("/proc/cpuinfo").read_text()
    except OSError:
        flags = ""
    if os.environ.get("FOTOIA_FP32") == "1":
        return torch.float32
    return torch.bfloat16 if ("amx_bf16" in flags or "avx512_bf16" in flags) else torch.float32


def device():
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------------------------------------------------------- E/S


def load_image(path, return_meta=False):
    """Lê qualquer foto (JPEG/PNG/TIFF/WebP/HEIC/RAW) como float32 sRGB [0,1].

    Aplica a orientação EXIF, converte perfis ICC não-sRGB para sRGB e preserva
    16 bits quando existirem. `meta` leva exif/alpha/bits para o salvamento.
    """
    path = Path(path)
    ext = path.suffix.lower()
    meta = {"path": str(path), "exif": None, "alpha": None, "bits": 8, "icc_converted": False}

    if ext in RAW_EXTS:
        import rawpy

        with rawpy.imread(str(path)) as raw:
            arr = raw.postprocess(use_camera_wb=True, output_bps=16, no_auto_bright=False)
        meta["bits"] = 16
        rgb = arr.astype(np.float32) / 65535.0
        return (rgb, meta) if return_meta else rgb

    im = Image.open(path)
    try:
        meta["exif"] = im.getexif()
    except Exception:
        meta["exif"] = None
    icc = im.info.get("icc_profile")

    # 16 bits: o Pillow reduz RGB 16-bit para 8; o OpenCV preserva.
    if ext in {".png", ".tif", ".tiff"}:
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if raw is not None and raw.dtype == np.uint16:
            meta["bits"] = 16
            raw = raw.astype(np.float32) / 65535.0
            if raw.ndim == 2:
                raw = np.repeat(raw[..., None], 3, axis=2)
            if raw.shape[2] == 4:
                meta["alpha"] = raw[..., 3].copy()
            rgb = np.ascontiguousarray(raw[..., :3][..., ::-1])
            rgb = _apply_orientation_array(rgb, meta)
            return (rgb, meta) if return_meta else rgb

    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        meta["alpha"] = np.asarray(im.getchannel("A"), dtype=np.float32) / 255.0
        im = im.convert("RGB")
    elif im.mode != "RGB":
        im = im.convert("RGB")

    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            name = (ImageCms.getProfileDescription(src) or "").lower()
            if "srgb" not in name:
                dst = ImageCms.createProfile("sRGB")
                im = ImageCms.profileToProfile(im, src, dst, outputMode="RGB")
                meta["icc_converted"] = name.strip() or True
        except Exception:
            pass

    rgb = np.asarray(im, dtype=np.float32) / 255.0
    return (rgb, meta) if return_meta else rgb


def _apply_orientation_array(rgb, meta):
    exif = meta.get("exif")
    o = exif.get(0x0112, 1) if exif else 1
    ops = {
        2: lambda a: a[:, ::-1],
        3: lambda a: a[::-1, ::-1],
        4: lambda a: a[::-1],
        5: lambda a: a.transpose(1, 0, 2),
        6: lambda a: np.rot90(a, 3),
        7: lambda a: np.rot90(a, 2).transpose(1, 0, 2),
        8: lambda a: np.rot90(a, 1),
    }
    return np.ascontiguousarray(ops[o](rgb)) if o in ops else rgb


def to_u8(rgb, dither=True):
    """float [0,1] -> uint8 com dither sub-LSB (não altera valores já em 8 bits)."""
    x = np.clip(rgb, 0.0, 1.0).astype(np.float32) * 255.0
    if dither:
        rng = np.random.default_rng(1234)
        n = rng.random(x.shape[:2], dtype=np.float32) - rng.random(x.shape[:2], dtype=np.float32)
        x = x + (n * 0.49)[..., None] if x.ndim == 3 else x + n * 0.49
    return np.clip(np.rint(x), 0, 255).astype(np.uint8)


def save_image(rgb, path, meta=None, alpha=None, quality=95, bits=8, protect=()):
    """Salva em alta qualidade. Recusa sobrescrever originais.

    JPEG: q95 4:4:4. PNG/TIFF: sem perdas (8 ou 16 bits). Embute perfil sRGB e EXIF.
    """
    path = Path(path)
    guard_output(path, protect)
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    exif = None
    if meta and meta.get("exif") is not None:
        exif = meta["exif"]
        try:
            exif[0x0112] = 1  # orientação já aplicada
        except Exception:
            exif = None

    if alpha is not None and ext in {".jpg", ".jpeg"}:
        raise ValueError("JPEG não suporta transparência; use .png ou .webp")

    if bits == 16 and ext in {".png", ".tif", ".tiff"}:
        x = np.clip(rgb, 0, 1)
        arr = np.rint(x * 65535.0).astype(np.uint16)[..., ::-1]
        if alpha is not None:
            a16 = np.rint(np.clip(alpha, 0, 1) * 65535.0).astype(np.uint16)
            arr = np.dstack([arr, a16])
        cv2.imwrite(str(path), arr)
        return path

    im = Image.fromarray(to_u8(rgb))
    if alpha is not None:
        im.putalpha(Image.fromarray(to_u8(alpha, dither=False)))
    kw = {"icc_profile": _SRGB_PROFILE}
    if exif is not None:
        kw["exif"] = exif
    if ext in {".jpg", ".jpeg"}:
        im.save(path, quality=quality, subsampling=0, optimize=True, **kw)
    elif ext == ".webp":
        im.save(path, quality=quality, method=6, **kw)
    elif ext == ".png":
        im.save(path, compress_level=4, **kw)
    else:
        im.save(path, **kw)
    return path


def guard_output(path, protect=()):
    """Garante que a saída não é um original nem está na pasta de entradas."""
    p = Path(path).resolve()
    for src in protect:
        if src and Path(src).resolve() == p:
            raise PermissionError(f"Recusado: a saída sobrescreveria a entrada {src}")
    if p.name.startswith("00_original"):
        raise PermissionError("Recusado: 00_original.* é a cópia intocável da foto original")
    try:
        if ENTRADAS.resolve() in p.parents:
            raise PermissionError("Recusado: a pasta entradas/ é somente leitura para o editor")
    except OSError:
        pass


def load_mask(path, shape=None):
    """Lê máscara (PNG cinza, ou canal alfa de um RGBA) como float32 [0,1]."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        m = np.asarray(im.getchannel("A"), dtype=np.float32) / 255.0
    elif im.mode in ("I;16", "I"):
        m = np.asarray(im, dtype=np.float32) / 65535.0
    else:
        m = np.asarray(im.convert("L"), dtype=np.float32) / 255.0
    if shape is not None and m.shape[:2] != tuple(shape[:2]):
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    return np.clip(m, 0, 1)


def save_mask(mask, path, protect=()):
    path = Path(path)
    guard_output(path, protect)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(to_u8(mask, dither=False)).save(path)
    return path


def to_pil(rgb):
    return Image.fromarray(to_u8(rgb, dither=False))


def from_pil(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0


# --------------------------------------------------------------------------- cor


def srgb_to_linear(x):
    x = np.clip(x, 0, None).astype(np.float32)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(x):
    x = np.clip(x, 0, None).astype(np.float32)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def luminance(lin):
    return (0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]).astype(np.float32)


def rgb_to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)


def lab_to_rgb(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_Lab2RGB), 0, 1)


def parse_color(s):
    """'#rrggbb', 'r,g,b' (0-255) ou nome básico -> np.array float32 sRGB [0,1]."""
    names = {
        "white": "#ffffff", "branco": "#ffffff", "black": "#000000", "preto": "#000000",
        "gray": "#808080", "cinza": "#808080", "warm": "#ffb070", "quente": "#ffb070",
        "cool": "#9cc4ff", "frio": "#9cc4ff", "gold": "#ffd9a0", "dourado": "#ffd9a0",
        "red": "#ff4030", "vermelho": "#ff4030", "blue": "#3070ff", "azul": "#3070ff",
        "teal": "#20c0c0", "orange": "#ff9030", "laranja": "#ff9030", "magenta": "#ff40c0",
        "green": "#40d060", "verde": "#40d060", "purple": "#9050ff", "roxo": "#9050ff",
    }  # fmt: skip
    s = names.get(str(s).lower().strip(), str(s).strip())
    if s.startswith("#"):
        s = s[1:]
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        return np.array([int(s[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0
    parts = [float(v) for v in s.replace(";", ",").split(",")]
    if len(parts) != 3:
        raise ValueError(f"Cor inválida: {s}")
    return np.array(parts, dtype=np.float32) / (255.0 if max(parts) > 1.0 else 1.0)


# --------------------------------------------------------------------------- geometria / filtros


def resize(arr, size, kind="auto"):
    """size=(largura, altura). Área para reduzir, Lanczos para ampliar."""
    w, h = int(size[0]), int(size[1])
    if arr.shape[1] == w and arr.shape[0] == h:
        return arr
    if kind == "auto":
        kind = "area" if (w * h) < (arr.shape[0] * arr.shape[1]) else "lanczos"
    interp = {
        "area": cv2.INTER_AREA, "lanczos": cv2.INTER_LANCZOS4, "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC, "nearest": cv2.INTER_NEAREST,
    }[kind]  # fmt: skip
    out = cv2.resize(arr, (w, h), interpolation=interp)
    return np.clip(out, 0, 1) if kind in ("lanczos", "cubic") else out


def fit_area(w, h, megapixels=1.0, multiple=16, upscale=False):
    """Dimensões com a mesma proporção, ~megapixels, múltiplas de `multiple`."""
    s = (megapixels * 1e6 / (w * h)) ** 0.5
    if not upscale:
        s = min(s, 1.0)
    nw = max(multiple, int(round(w * s / multiple)) * multiple)
    nh = max(multiple, int(round(h * s / multiple)) * multiple)
    return nw, nh


def blur(arr, sigma):
    if sigma <= 0:
        return arr
    return cv2.GaussianBlur(arr, (0, 0), float(sigma), borderType=cv2.BORDER_REFLECT101)


def guided(guide, src, radius, eps=1e-3):
    """Filtro guiado (preserva bordas do guia). guide: HxWx3 ou HxW; src: HxW ou HxWxC."""
    g = np.ascontiguousarray(guide, dtype=np.float32)
    s = np.ascontiguousarray(src, dtype=np.float32)
    return cv2.ximgproc.guidedFilter(g, s, int(max(1, radius)), float(eps))


def feather(mask, px):
    return np.clip(blur(mask.astype(np.float32), px), 0, 1) if px > 0 else mask


def grow(mask, px):
    """Dilata (px>0) ou erode (px<0) uma máscara suave."""
    if px == 0:
        return mask
    k = int(abs(px)) * 2 + 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    f = cv2.dilate if px > 0 else cv2.erode
    return f(mask.astype(np.float32), ker)


def mix(a, b, mask):
    """a onde mask=0, b onde mask=1."""
    m = mask[..., None] if (mask.ndim == 2 and a.ndim == 3) else mask
    return (a * (1.0 - m) + b * m).astype(np.float32)


def bbox(mask, thr=0.05, pad=0):
    ys, xs = np.where(mask > thr)
    if len(xs) == 0:
        return None
    h, w = mask.shape[:2]
    return (
        max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
        min(w, int(xs.max()) + 1 + pad), min(h, int(ys.max()) + 1 + pad),
    )  # fmt: skip


# --------------------------------------------------------------------------- pastas de trabalho


def slug(text):
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in str(text).strip().lower()]
    out = "".join(keep).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out[:48] or "foto"


def new_job(src, name=None):
    """Cria saidas/<data>_<nome>/ com a cópia intocável do original e o registro."""
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(src)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    job = SAIDAS / f"{stamp}_{slug(name or src.stem)}"
    job.mkdir(parents=True, exist_ok=False)
    original = job / f"00_original{src.suffix.lower()}"
    shutil.copy2(src, original)
    os.chmod(original, 0o444)
    reg = {"origem": str(src), "original": original.name, "criado_em": stamp, "etapas": []}
    (job / "registro.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False))
    return job, original


def log_step(out_path, comando, params):
    """Anexa a etapa ao registro.json da pasta de trabalho (se a saída estiver numa)."""
    p = Path(out_path).resolve()
    for d in [p.parent, *p.parents]:
        reg = d / "registro.json"
        if reg.exists():
            try:
                data = json.loads(reg.read_text())
                data.setdefault("etapas", []).append(
                    {"quando": time.strftime("%H:%M:%S"), "comando": comando, "saida": p.name, "params": params}
                )
                reg.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            except Exception:
                pass
            return
        if d == SAIDAS.resolve() or d == d.parent:
            return


class Timer:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        self.t = time.time()
        return self

    def __exit__(self, *a):
        print(f"[fotoia] {self.label}: {time.time() - self.t:.1f}s", flush=True)
