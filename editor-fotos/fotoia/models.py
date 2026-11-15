"""Registro de modelos: origem, licença, tamanho e download sob demanda.

Nada é baixado na importação. `path(key)` baixa na primeira vez (Hugging Face
ou release do GitHub) e devolve o caminho local. `status()` mostra o que está
em disco. Licenças marcadas `comercial=False` exigem atenção em trabalho pago.
"""

from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path

from .core import CACHE

WEIGHTS = CACHE / "pesos"

# kind: "hf" (snapshot, com patterns) | "hf_file" (um arquivo) | "url" (download direto)
REGISTRY = {
    # ---- edição generativa
    "flux2-klein-4b": dict(
        kind="hf", repo="black-forest-labs/FLUX.2-klein-4B",
        patterns=["model_index.json", "transformer/*", "text_encoder/*", "tokenizer/*", "vae/*", "scheduler/*"],
        gb=16.0, licenca="Apache-2.0", comercial=True,
        uso="edição por instrução, geração de cenários, inpainting generativo, multi-referência",
    ),
    "sd15-realistic": dict(
        kind="hf", repo="stablediffusionapi/realistic-vision-v51",
        patterns=[
            "model_index.json", "scheduler/*", "tokenizer/*", "text_encoder/config.json",
            "text_encoder/model.safetensors", "unet/config.json", "unet/diffusion_pytorch_model.safetensors",
            "vae/config.json", "vae/diffusion_pytorch_model.safetensors",
        ],
        gb=2.1, licenca="CreativeML OpenRAIL-M", comercial=True,
        uso="base SD1.5 fotorrealista para o refino de detalhe (ControlNet tile)",
    ),
    "controlnet-tile": dict(
        kind="hf_file", repo="comfyanonymous/ControlNet-v1-1_fp16_safetensors",
        file="control_v11f1e_sd15_tile_fp16.safetensors",
        gb=0.72, licenca="OpenRAIL", comercial=True,
        uso="ControlNet tile: recuperação de detalhe/textura fiel à estrutura",
    ),
    # ---- segmentação / matting
    "birefnet": dict(
        kind="hf", repo="ZhengPeng7/BiRefNet", patterns=["*.json", "*.py", "model.safetensors"],
        gb=0.44, licenca="MIT", comercial=True, uso="recorte de assunto (1024px), uso geral",
    ),
    "birefnet-hr": dict(
        kind="hf", repo="ZhengPeng7/BiRefNet_HR", patterns=["*.json", "*.py", "model.safetensors"],
        gb=0.44, licenca="MIT", comercial=True, uso="recorte de assunto em alta resolução (2048px)",
    ),
    "birefnet-matting": dict(
        kind="hf", repo="ZhengPeng7/BiRefNet_HR-matting", patterns=["*.json", "*.py", "model.safetensors"],
        gb=0.44, licenca="MIT", comercial=True, uso="alfa suave para cabelo, pelos e transparências",
    ),
    "sam2": dict(
        kind="hf", repo="facebook/sam2.1-hiera-large", patterns=["*.json", "model.safetensors"],
        gb=0.9, licenca="Apache-2.0", comercial=True, uso="segmentação por ponto/caixa (SAM 2.1 Large)",
    ),
    "grounding-dino": dict(
        kind="hf", repo="IDEA-Research/grounding-dino-base", patterns=["*.json", "*.txt", "model.safetensors"],
        gb=0.93, licenca="Apache-2.0", comercial=True, uso="localizar objetos por texto (caixas para o SAM 2)",
    ),
    "face-parsing": dict(
        kind="hf", repo="jonathandinu/face-parsing", patterns=["*.json", "model.safetensors"],
        gb=0.34, licenca="não declarada (treinado em CelebAMask-HQ, uso de pesquisa)", comercial=False,
        uso="máscaras de pele/cabelo/olhos/lábios para retoque",
    ),
    "yunet": dict(
        kind="hf_file", repo="opencv/face_detection_yunet", file="face_detection_yunet_2023mar.onnx",
        gb=0.001, licenca="MIT", comercial=True, uso="detecção de rostos",
    ),
    # ---- profundidade
    "depth-small": dict(
        kind="hf", repo="depth-anything/Depth-Anything-V2-Small-hf", patterns=["*.json", "model.safetensors"],
        gb=0.1, licenca="Apache-2.0", comercial=True, uso="profundidade (rápido, uso comercial livre)",
    ),
    "depth-large": dict(
        kind="hf", repo="depth-anything/Depth-Anything-V2-Large-hf", patterns=["*.json", "model.safetensors"],
        gb=1.34, licenca="CC-BY-NC-4.0", comercial=False, uso="profundidade de máxima qualidade (não comercial)",
    ),
    # ---- inpainting / remoção
    "lama": dict(
        kind="hf_file", repo="fashn-ai/LaMa", file="big-lama.pt",
        gb=0.2, licenca="Apache-2.0", comercial=True, uso="remoção de objetos e limpeza (não generativo)",
    ),
    # ---- upscale / restauração
    "realesrgan-x4plus": dict(
        kind="url", url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        gb=0.067, licenca="BSD-3", comercial=True, scale=4, uso="upscale 4x de fotos (padrão)",
    ),
    "realesrgan-x2plus": dict(
        kind="url", url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        gb=0.067, licenca="BSD-3", comercial=True, scale=2, uso="upscale 2x de fotos",
    ),
    "realesr-general-x4v3": dict(
        kind="url", url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
        gb=0.005, licenca="BSD-3", comercial=True, scale=4, uso="upscale 4x rápido (rascunho, imagens grandes)",
    ),
    "nomos2-dat2": dict(
        kind="hf_file", repo="Phips/4xNomos2_hq_dat2", file="4xNomos2_hq_dat2.safetensors",
        gb=0.14, licenca="CC-BY-4.0", comercial=True, scale=4,
        uso="upscale 4x de máxima fidelidade para fotos limpas (lento em CPU)",
    ),
    "gfpgan": dict(
        kind="url", url="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        gb=0.35, licenca="Apache-2.0", comercial=True, uso="restauração de rostos (só quando pedido)",
    ),
}


def _hf_env():
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def path(key):
    """Caminho local do modelo, baixando se necessário."""
    if key not in REGISTRY:
        raise KeyError(f"Modelo desconhecido: {key}. Disponíveis: {', '.join(REGISTRY)}")
    m = REGISTRY[key]
    _hf_env()
    if m["kind"] == "hf":
        from huggingface_hub import snapshot_download

        return snapshot_download(m["repo"], allow_patterns=m.get("patterns"))
    if m["kind"] == "hf_file":
        from huggingface_hub import hf_hub_download

        return hf_hub_download(m["repo"], m["file"])
    if m["kind"] == "url":
        WEIGHTS.mkdir(parents=True, exist_ok=True)
        dst = WEIGHTS / m["url"].rsplit("/", 1)[-1]
        if not dst.exists():
            print(f"[fotoia] baixando {key} ({m['gb']} GB)…", flush=True)
            tmp = dst.with_suffix(dst.suffix + ".part")
            req = urllib.request.Request(m["url"], headers={"User-Agent": "fotoia"})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, length=1 << 20)
            tmp.rename(dst)
        return str(dst)
    raise ValueError(m["kind"])


def is_local(key):
    m = REGISTRY[key]
    if m["kind"] == "url":
        return (WEIGHTS / m["url"].rsplit("/", 1)[-1]).exists()
    try:
        from huggingface_hub import scan_cache_dir

        repos = {r.repo_id: r for r in scan_cache_dir().repos}
    except Exception:
        return False
    r = repos.get(m["repo"])
    if r is None:
        return False
    if m["kind"] == "hf_file":
        return any(f.file_name == m["file"] for rev in r.revisions for f in rev.files)
    return r.size_on_disk > 0


def remove(key):
    """Apaga um modelo do disco (ele volta a ser baixado quando necessário)."""
    m = REGISTRY[key]
    if m["kind"] == "url":
        p = WEIGHTS / m["url"].rsplit("/", 1)[-1]
        if p.exists():
            p.unlink()
        return
    from huggingface_hub import scan_cache_dir

    info = scan_cache_dir()
    revs = [rev.commit_hash for r in info.repos if r.repo_id == m["repo"] for rev in r.revisions]
    if revs:
        info.delete_revisions(*revs).execute()


def status():
    rows = []
    for k, m in REGISTRY.items():
        rows.append(
            dict(modelo=k, local=is_local(k), gb=m["gb"], licenca=m["licenca"], comercial=m["comercial"], uso=m["uso"])
        )
    return rows


def disk_free_gb(where=None):
    return shutil.disk_usage(where or Path.home()).free / 1e9
