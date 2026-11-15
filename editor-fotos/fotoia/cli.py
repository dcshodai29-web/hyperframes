"""CLI do fotoia: cada comando lê arquivo(s) e grava um arquivo novo.

    fotoia <comando> ENTRADA SAIDA [opções]

Nenhum comando sobrescreve a entrada. Use `fotoia job FOTO` para abrir uma
pasta de trabalho em saidas/ com a cópia intocável do original.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from . import core


def _img(path):
    return core.load_image(path, return_meta=True)


def _mask(path, shape):
    return None if not path else core.load_mask(path, shape)


def _save(args, rgb, meta, alpha=None, extra=None):
    out = core.save_image(rgb, args.saida, meta=meta, alpha=alpha, quality=args.qualidade, protect=[args.entrada])
    params = {k: v for k, v in vars(args).items() if k not in ("func", "entrada", "saida") and v is not None}
    if extra:
        params["info"] = extra
    core.log_step(out, args.cmd, params)
    print(f"[fotoia] salvo: {out}" + (f"  {json.dumps(extra, ensure_ascii=False)}" if extra else ""))


def _pts(s):
    return [tuple(float(v) for v in p.split(",")) for p in s.split(";") if p.strip()] if s else None


# --------------------------------------------------------------------------- comandos


def cmd_job(a):
    job, original = core.new_job(a.entrada, a.nome)
    print(json.dumps({"pasta": str(job), "original": str(original)}, ensure_ascii=False))


def cmd_analisar(a):
    from . import qa, segment

    rgb = core.load_image(a.entrada)
    rep = qa.analyze(rgb)
    if not a.sem_rostos:
        rep["rostos"] = [dict(x=round(f[0]), y=round(f[1]), w=round(f[2]), h=round(f[3])) for f in segment.detect_faces(rgb)]
    print(json.dumps(rep, indent=2, ensure_ascii=False))


def cmd_recortar(a):
    """Alfa do assunto principal -> máscara PNG (e opcionalmente o recorte RGBA)."""
    from . import segment

    rgb, meta = _img(a.entrada)
    alpha = segment.matte_subject(rgb, a.modelo)
    core.save_mask(alpha, a.saida, protect=[a.entrada])
    if a.rgba:
        core.save_image(segment.decontaminate(rgb, alpha), a.rgba, alpha=alpha, protect=[a.entrada])
    core.log_step(a.saida, a.cmd, {"modelo": a.modelo, "cobertura": round(float(alpha.mean()), 4)})
    print(f"[fotoia] alfa salvo: {a.saida} (cobertura {alpha.mean():.1%})")


def cmd_mascara(a):
    """Máscara por texto, ponto, caixa, partes do rosto, luminosidade ou degradê."""
    from . import segment

    rgb, _ = _img(a.entrada)
    info = {}
    if a.texto:
        m, det = segment.segment_text(rgb, a.texto, a.limiar)
        info["deteccoes"] = [dict(rotulo=d[2], score=round(d[1], 2), caixa=[round(v) for v in d[0]]) for d in det]
    elif a.pontos or a.caixas:
        neg = _pts(a.pontos_neg) or []
        pos = _pts(a.pontos) or []
        m = segment.sam(rgb, points=(pos + neg) or None, labels=[1] * len(pos) + [0] * len(neg), boxes=_pts(a.caixas))
    elif a.rosto:
        m = segment.face_mask(rgb, a.rosto)
    elif a.luminosidade:
        lo, hi = (float(v) for v in a.luminosidade.split(","))
        m = segment.luminosity_mask(rgb, lo, hi)
    elif a.degrade is not None:
        m = segment.gradient_mask(rgb.shape, a.degrade)
    elif a.radial:
        cx, cy, r = (float(v) for v in a.radial.split(","))
        m = segment.radial_mask(rgb.shape, (cx, cy), r)
    else:
        sys.exit("Informe --texto, --pontos, --caixas, --rosto, --luminosidade, --degrade ou --radial")
    if not (a.rosto or a.luminosidade or a.degrade is not None or a.radial):
        m = segment.refine_alpha(rgb, core.blur((m > 0.5).astype(np.float32), 0.8))
    for path, op in ((a.unir, "union"), (a.intersectar, "intersect"), (a.subtrair, "subtract")):
        if path:
            m = segment.combine(m, core.load_mask(path, rgb.shape), op)
    if a.crescer:
        m = core.grow(m, a.crescer)
    if a.suavizar:
        m = core.feather(m, a.suavizar)
    if a.inverter:
        m = 1 - m
    core.save_mask(m, a.saida, protect=[a.entrada])
    info["cobertura"] = round(float(m.mean()), 4)
    core.log_step(a.saida, a.cmd, info)
    print(f"[fotoia] máscara salva: {a.saida}  {json.dumps(info, ensure_ascii=False)}")


def cmd_fundo(a):
    from . import background, segment

    rgb, meta = _img(a.entrada)
    alpha = _mask(a.alfa, rgb.shape)
    if alpha is None:
        alpha = segment.matte_subject(rgb)
    info = {}
    if a.prompt:
        up = None
        if a.fundo_nitido:
            from . import upscale

            up = lambda x: upscale.upscale(x, "realesrgan-x2plus")  # noqa: E731
        out, prop, info = background.replace_generative(
            rgb, alpha, a.prompt, subject=a.assunto, megapixels=a.mp, seed=a.seed, harmonize=a.harmonizar, upscaler=up
        )
        if a.proposta:
            core.save_image(prop, a.proposta)
    else:
        image = core.load_image(a.imagem) if a.imagem else None
        kind = "image" if a.imagem else a.tipo
        out = background.replace_procedural(
            rgb, alpha, kind, a.cor, a.cor2, image, shadow=not a.sem_sombra, shadow_opacity=a.sombra,
            shadow_direction=a.sombra_direcao, shadow_length=a.sombra_comprimento, reflect=a.reflexo,
            harmonize=a.harmonizar if a.imagem else 0.0,
        )  # fmt: skip
    _save(a, out, meta, extra=info)


def cmd_reluz(a):
    """Relighting generativo com textura original preservada."""
    from . import flux, light

    rgb, meta = _img(a.entrada)
    alpha = _mask(a.alfa, rgb.shape)
    prompt = a.prompt_cru or light.relight_prompt(a.luz)
    prop = flux.edit(rgb, prompt, megapixels=a.mp, seed=a.seed)
    if a.proposta:
        core.save_image(prop, a.proposta)
    out = light.transfer_light(rgb, prop, alpha=alpha, detail=a.detalhe, strength=a.forca, highlights=a.brilhos)
    if alpha is not None and a.so_assunto:
        out = core.mix(rgb, out, alpha)
    _save(a, out, meta)


def cmd_transferir_luz(a):
    from . import light

    rgb, meta = _img(a.entrada)
    ref = core.load_image(a.referencia)
    alpha = _mask(a.alfa, rgb.shape)
    out = light.transfer_light(rgb, ref, alpha=alpha, detail=a.detalhe, strength=a.forca, highlights=a.brilhos)
    if alpha is not None and a.so_assunto:
        out = core.mix(rgb, out, alpha)
    _save(a, out, meta)


def cmd_luz(a):
    """Luz direcional física (normais da profundidade) e/ou rim light determinístico."""
    from . import depth, light, segment

    rgb, meta = _img(a.entrada)
    alpha = _mask(a.alfa, rgb.shape)
    normals = None
    if a.direcional or a.rim:
        normals = light.normals_from_depth(depth.estimate(rgb))
    out = rgb
    if a.direcional:
        out = light.shade(out, normals, a.direcional, a.intensidade, a.cor, a.ambiente, alpha)
    if a.rim:
        if alpha is None:
            alpha = segment.matte_subject(rgb)
        out = light.rim_light(out, alpha, normals, a.rim, a.cor_rim, a.intensidade_rim, a.largura_rim)
    _save(a, out, meta)


def cmd_contraluz(a):
    """Assunto em contraluz sobre fundo claro de estúdio, com rim e névoa (determinístico)."""
    from . import light, segment

    rgb, meta = _img(a.entrada)
    alpha = _mask(a.alfa, rgb.shape)
    if alpha is None:
        alpha = segment.matte_subject(rgb)
    bg = core.load_image(a.fundo) if a.fundo else a.cor
    out = light.backlit(
        rgb, alpha, bg, rim=a.rim, rim_width=a.largura, glow=a.brilho, haze=a.nevoa, darken=a.escurecer,
        contrast=a.contraste, dodge_burn=a.dodge_burn, clarity=a.claridade, texture=a.textura,
        saturation=a.saturacao, rim_color=a.cor_rim, top_bias=a.topo,
    )  # fmt: skip
    _save(a, out, meta)


def cmd_editar(a):
    """Edição livre por instrução (FLUX.2 klein). Com --mascara, só a região muda."""
    from . import flux, inpaint

    rgb, meta = _img(a.entrada)
    refs = [core.load_image(r) for r in (a.ref or [])]
    mask = _mask(a.mascara, rgb.shape)
    if mask is not None:
        out = inpaint.fill(rgb, mask, a.prompt, megapixels=a.mp, seed=a.seed, refs=refs, mode=a.modo)
    else:
        small = flux.edit([rgb, *refs], a.prompt, megapixels=a.mp, seed=a.seed)
        out = core.resize(small, (rgb.shape[1], rgb.shape[0]))
    _save(a, out, meta)


def cmd_gerar(a):
    from . import flux

    out = flux.generate(a.prompt, a.largura, a.altura, seed=a.seed)
    core.save_image(out, a.saida, quality=a.qualidade)
    core.log_step(a.saida, a.cmd, {"prompt": a.prompt, "seed": a.seed})
    print(f"[fotoia] salvo: {a.saida}")


def cmd_remover(a):
    from . import inpaint

    rgb, meta = _img(a.entrada)
    out = inpaint.remove(rgb, core.load_mask(a.mascara, rgb.shape), grow=a.crescer)
    _save(a, out, meta)


def cmd_ampliar(a):
    from . import upscale

    rgb, meta = _img(a.entrada)
    out = upscale.upscale_to(rgb, a.lado, a.mp, a.escala, a.modelo, a.fidelidade)
    info = {"saida": f"{out.shape[1]}x{out.shape[0]}"}
    if a.rostos:
        out, n = upscale.restore_faces(out, a.rostos)
        info["rostos_restaurados"] = n
    _save(a, out, meta, extra=info)


def cmd_detalhe(a):
    from . import upscale

    rgb, meta = _img(a.entrada)
    out = upscale.refine_detail(rgb, a.forca, a.prompt, seed=a.seed, mask=_mask(a.mascara, rgb.shape))
    _save(a, out, meta)


def cmd_ajustar(a):
    """Ajustes clássicos encadeados na ordem de revelação. --mascara restringe todos."""
    from . import enhance as e

    rgb, meta = _img(a.entrada)
    m = _mask(a.mascara, rgb.shape)
    x = rgb
    if a.auto_wb:
        x = e.auto_white_balance(x, a.auto_wb, m)
    if a.temp or a.tint:
        x = e.white_balance(x, a.temp, a.tint, m)
    if a.reduzir_ruido:
        x = e.denoise(x, a.reduzir_ruido, min(1.0, a.reduzir_ruido * 2), m)
    if a.auto_niveis:
        x = e.auto_levels(x, mask=m)
    if a.exposicao:
        x = e.exposure(x, a.exposicao, m)
    if a.sombras or a.luzes:
        x = e.shadows_highlights(x, a.sombras, a.luzes, mask=m)
    if a.desnevoar:
        x = e.dehaze(x, a.desnevoar, m)
    if a.contraste:
        x = e.contrast(x, a.contraste, mask=m)
    if a.dodge_burn:
        x = e.dodge_burn(x, a.dodge_burn, mask=m)
    if a.claridade:
        x = e.clarity(x, a.claridade, mask=m)
    if a.textura:
        x = e.texture(x, a.textura, mask=m)
    if a.saturacao or a.vibracao:
        x = e.saturation(x, a.saturacao, a.vibracao, m)
    if a.matiz:
        x = e.hue_shift(x, a.matiz, m)
    if a.recolorir:
        if m is None:
            sys.exit("--recolorir exige --mascara")
        x = e.recolor(rgb if x is rgb else x, a.recolorir, m)
    if a.grade:
        x = e.grade(x, a.grade, a.grade_forca, m)
    if a.lut:
        x = e.apply_lut(x, a.lut, mask=m)
    if a.brilho_difuso:
        x = e.bloom(x, a.brilho_difuso, mask=m)
    if a.nevoa:
        x = e.haze(x, a.nevoa, a.nevoa_cor, m)
    if a.nitidez:
        x = e.sharpen(x, a.nitidez, a.nitidez_raio, mask=m)
    if a.vinheta:
        x = e.vignette(x, a.vinheta)
    if a.grao:
        x = e.grain(x, a.grao)
    _save(a, x, meta)


def cmd_retocar(a):
    from . import retouch

    rgb, meta = _img(a.entrada)
    out, info = retouch.portrait(rgb, a.pele, a.olhos, a.dentes, a.olheiras)
    _save(a, out, meta, extra=info)


def cmd_profundidade(a):
    from . import depth

    rgb, _ = _img(a.entrada)
    core.save_mask(depth.estimate(rgb, a.modelo), a.saida, protect=[a.entrada])
    print(f"[fotoia] profundidade salva: {a.saida}")


def cmd_desfoque(a):
    from . import depth

    rgb, meta = _img(a.entrada)
    d = core.load_mask(a.profundidade, rgb.shape) if a.profundidade else depth.estimate(rgb)
    alpha = _mask(a.alfa, rgb.shape)
    if alpha is None and not a.sem_assunto:  # o assunto fica nítido por padrão
        from . import segment

        alpha = segment.matte_subject(rgb)
    out = depth.lens_blur(rgb, d, a.foco, a.quantidade, alpha)
    _save(a, out, meta)


def cmd_compor(a):
    """Compõe ENTRADA (primeiro plano) sobre --fundo usando --alfa."""
    from . import background

    rgb, meta = _img(a.entrada)
    alpha = core.load_mask(a.alfa, rgb.shape)
    bg = background.fit_cover(core.load_image(a.fundo), rgb.shape)
    out = background.compose(rgb, alpha, bg, wrap=a.wrap, decontaminate=not a.sem_descontaminar)
    _save(a, out, meta)


def cmd_reenquadrar(a):
    """Recorta para uma proporção mantendo o assunto, ou expande a tela com IA (--expandir)."""
    from . import compose

    rgb, meta = _img(a.entrada)
    if a.expandir:
        out = compose.outpaint(rgb, a.proporcao, a.prompt, seed=a.seed)
    else:
        out = compose.smart_crop(rgb, a.proporcao, _mask(a.alfa, rgb.shape))
    _save(a, out, meta, extra={"saida": f"{out.shape[1]}x{out.shape[0]}"})


def cmd_conferir(a):
    from . import qa

    o, r = core.load_image(a.entrada), core.load_image(a.resultado)
    print(json.dumps(qa.preservation(o, r, _mask(a.mascara, o.shape)), indent=2, ensure_ascii=False))


def cmd_comparar(a):
    from . import qa

    if a.zoom:
        qa.crop_zoom(a.imagens, [float(v) for v in a.zoom.split(",")], a.saida, a.altura, a.rotulos)
    else:
        qa.sheet(a.imagens, a.rotulos, a.saida, a.altura, a.colunas)
    print(f"[fotoia] comparativo salvo: {a.saida}")


def cmd_modelos(a):
    from . import models

    if a.baixar:
        for k in a.baixar:
            print(k, "->", models.path(k))
    if a.apagar:
        for k in a.apagar:
            models.remove(k)
    rows = models.status()
    for r in rows:
        print(
            f"{'✔' if r['local'] else '·'} {r['modelo']:22s} {r['gb']:6.2f} GB  "
            f"{'comercial ok' if r['comercial'] else 'NÃO COMERCIAL':13s}  {r['uso']}"
        )
    print(f"em disco: {sum(r['gb'] for r in rows if r['local']):.1f} GB · livre: {models.disk_free_gb():.1f} GB")


# --------------------------------------------------------------------------- parser


def build():
    p = argparse.ArgumentParser(prog="fotoia", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, func, help_, io=True, out=True):
        s = sub.add_parser(name, help=help_)
        s.set_defaults(func=func)
        if io:
            s.add_argument("entrada")
            if out:
                s.add_argument("saida")
        s.add_argument("--qualidade", type=int, default=95, help="qualidade JPEG/WebP (padrão 95)")
        return s

    s = add("job", cmd_job, "abre pasta de trabalho em saidas/ com cópia do original", out=False)
    s.add_argument("--nome")

    s = add("analisar", cmd_analisar, "métricas técnicas da foto (JSON)", out=False)
    s.add_argument("--sem-rostos", action="store_true")

    s = add("recortar", cmd_recortar, "alfa do assunto principal (BiRefNet)")
    s.add_argument("--modelo", default="auto", choices=["auto", "birefnet", "birefnet-hr", "birefnet-matting"])
    s.add_argument("--rgba", help="também salva o recorte transparente neste caminho")

    s = add("mascara", cmd_mascara, "máscara por texto/ponto/caixa/rosto/luminosidade/degradê")
    s.add_argument("--texto", help="o que selecionar, em inglês (ex.: 'shirt. hat')")
    s.add_argument("--limiar", type=float, default=0.3)
    s.add_argument("--pontos", help="'x,y;x,y' pontos dentro do objeto")
    s.add_argument("--pontos-neg", help="'x,y;…' pontos a excluir")
    s.add_argument("--caixas", help="'x0,y0,x1,y1;…'")
    s.add_argument("--rosto", help="pele, rosto, olhos, labios, cabelo, roupa…")
    s.add_argument("--luminosidade", help="'min,max' em 0..1")
    s.add_argument("--degrade", type=float, help="ângulo do filtro graduado (90 = de cima p/ baixo)")
    s.add_argument("--radial", help="'cx,cy,raio' relativos (0..1)")
    s.add_argument("--unir"), s.add_argument("--intersectar"), s.add_argument("--subtrair")
    s.add_argument("--crescer", type=int, default=0, help="px (+ dilata, - erode)")
    s.add_argument("--suavizar", type=float, default=0)
    s.add_argument("--inverter", action="store_true")

    s = add("fundo", cmd_fundo, "troca o cenário mantendo o assunto original")
    s.add_argument("--alfa", help="alfa do assunto (se omitido, recorta automaticamente)")
    s.add_argument("--prompt", help="cenário por IA, em inglês (ex.: 'a marble table in a sunlit kitchen')")
    s.add_argument("--assunto", default="subject", help="descrição curta do assunto, em inglês")
    s.add_argument("--tipo", default="studio", choices=["studio", "solid", "gradient"])
    s.add_argument("--cor", default="#e6e6e8"), s.add_argument("--cor2")
    s.add_argument("--imagem", help="usa esta imagem como fundo")
    s.add_argument("--harmonizar", type=float, default=0.7)
    s.add_argument("--sombra", type=float, default=0.45), s.add_argument("--sem-sombra", action="store_true")
    s.add_argument("--sombra-direcao", type=float, default=20.0)
    s.add_argument("--sombra-comprimento", type=float, default=0.3)
    s.add_argument("--reflexo", type=float, default=0.0)
    s.add_argument("--fundo-nitido", action="store_true", help="super-resolução no fundo gerado")
    s.add_argument("--proposta", help="salva a proposta crua do modelo")
    s.add_argument("--mp", type=float, default=1.0), s.add_argument("--seed", type=int, default=0)

    for name, func, h in (("reluz", cmd_reluz, "relighting por IA preservando a textura original"),
                          ("transferir-luz", cmd_transferir_luz, "aplica a luz de --referencia nos pixels da entrada")):  # fmt: skip
        s = add(name, func, h)
        if name == "reluz":
            s.add_argument("--luz", default="estudio", help="preset (estudio, rembrandt, cinematico, rim, backlight, golden, neon, dramatico, janela, produto) ou descrição em inglês")
            s.add_argument("--prompt-cru", help="instrução completa em inglês (ignora --luz)")
            s.add_argument("--proposta"), s.add_argument("--mp", type=float, default=1.0)
            s.add_argument("--seed", type=int, default=0)
        else:
            s.add_argument("--referencia", required=True)
        s.add_argument("--alfa"), s.add_argument("--so-assunto", action="store_true")
        s.add_argument("--detalhe", type=float, default=0.006, help="escala da luz (menor = segue luz mais fina)")
        s.add_argument("--forca", type=float, default=1.0)
        s.add_argument("--brilhos", type=float, default=0.0, help="0..1 transfere especulares/rim novos")

    s = add("luz", cmd_luz, "luz direcional e rim light determinísticos")
    s.add_argument("--alfa")
    s.add_argument("--direcional", help="left, right, top, top-left… ou graus")
    s.add_argument("--intensidade", type=float, default=0.6), s.add_argument("--cor", default="#ffffff")
    s.add_argument("--ambiente", type=float, default=0.55)
    s.add_argument("--rim", help="direção do contraluz: back-left, back-right, back, back-top…")
    s.add_argument("--cor-rim", default="#fff2e0"), s.add_argument("--intensidade-rim", type=float, default=0.8)
    s.add_argument("--largura-rim", type=float, default=0.012)

    s = add("contraluz", cmd_contraluz, "contraluz em estúdio claro: fundo high-key, rim, névoa, volume")
    s.add_argument("--alfa"), s.add_argument("--cor", default="#fbfbfb"), s.add_argument("--fundo")
    for flag, default in (("--rim", 4.2), ("--largura", 0.0045), ("--brilho", 0.55), ("--nevoa", 0.09),
                          ("--escurecer", -0.4), ("--contraste", 0.33), ("--dodge-burn", 0.65), ("--claridade", 0.4),
                          ("--textura", 0.45), ("--saturacao", 0.08), ("--topo", 0.5)):  # fmt: skip
        s.add_argument(flag, type=float, default=default)
    s.add_argument("--cor-rim", default="#ffffff")

    s = add("editar", cmd_editar, "edição por instrução (FLUX.2 klein); com --mascara é localizada")
    s.add_argument("--prompt", required=True), s.add_argument("--mascara")
    s.add_argument("--modo", default="edit", choices=["edit", "repaint"])
    s.add_argument("--ref", action="append", help="imagem de referência (repetível)")
    s.add_argument("--mp", type=float, default=1.0), s.add_argument("--seed", type=int, default=0)

    s = add("gerar", cmd_gerar, "texto -> imagem (FLUX.2 klein)", io=False)
    s.add_argument("saida"), s.add_argument("--prompt", required=True)
    s.add_argument("--largura", type=int, default=1024), s.add_argument("--altura", type=int, default=1024)
    s.add_argument("--seed", type=int, default=0)

    s = add("remover", cmd_remover, "apaga o conteúdo da máscara (LaMa)")
    s.add_argument("--mascara", required=True), s.add_argument("--crescer", type=int)

    s = add("ampliar", cmd_ampliar, "upscale (Real-ESRGAN / DAT2)")
    s.add_argument("--escala", type=float), s.add_argument("--lado", type=int, help="lado maior final em px")
    s.add_argument("--mp", type=float, help="megapixels finais"), s.add_argument("--modelo")
    s.add_argument("--fidelidade", type=float, default=0.0, help="0..1 trava cor/tons do original")
    s.add_argument("--rostos", type=float, default=0.0, help="força da restauração de rostos (GFPGAN)")

    s = add("detalhe", cmd_detalhe, "EXPERIMENTAL: microdetalhe por SD1.5 + ControlNet tile (só em imagem já ampliada)")
    s.add_argument("--forca", type=float, default=0.3), s.add_argument("--prompt"), s.add_argument("--mascara")
    s.add_argument("--seed", type=int, default=0)

    s = add("ajustar", cmd_ajustar, "exposição, cor, contraste, nitidez, gradação (clássico)")
    s.add_argument("--mascara")
    for flag, default in (("--exposicao", 0.0), ("--contraste", 0.0), ("--sombras", 0.0), ("--luzes", 0.0),
                          ("--temp", 0.0), ("--tint", 0.0), ("--saturacao", 0.0), ("--vibracao", 0.0),
                          ("--matiz", 0.0), ("--claridade", 0.0), ("--textura", 0.0), ("--dodge-burn", 0.0),
                          ("--nitidez", 0.0), ("--reduzir-ruido", 0.0), ("--desnevoar", 0.0), ("--auto-wb", 0.0),
                          ("--brilho-difuso", 0.0), ("--nevoa", 0.0), ("--vinheta", 0.0), ("--grao", 0.0)):  # fmt: skip
        s.add_argument(flag, type=float, default=default)
    s.add_argument("--nitidez-raio", type=float, default=1.0), s.add_argument("--nevoa-cor", default="#ffffff")
    s.add_argument("--auto-niveis", action="store_true"), s.add_argument("--recolorir", help="cor alvo p/ a máscara")
    s.add_argument("--grade", help="teal-orange, quente, frio, cinema, noir, pastel")
    s.add_argument("--grade-forca", type=float), s.add_argument("--lut", help="arquivo .cube")

    s = add("retocar", cmd_retocar, "retoque de retrato (pele, olhos, dentes) conservador")
    s.add_argument("--pele", type=float, default=0.5), s.add_argument("--olhos", type=float, default=0.3)
    s.add_argument("--dentes", type=float, default=0.0), s.add_argument("--olheiras", type=float, default=0.0)

    s = add("profundidade", cmd_profundidade, "mapa de profundidade")
    s.add_argument("--modelo", default="depth-small")

    s = add("desfoque", cmd_desfoque, "bokeh por profundidade (assunto nítido)")
    s.add_argument("--alfa"), s.add_argument("--profundidade"), s.add_argument("--foco", type=float)
    s.add_argument("--quantidade", type=float, default=0.02)
    s.add_argument("--sem-assunto", action="store_true", help="não recorta o assunto (desfoque só por profundidade)")

    s = add("compor", cmd_compor, "compõe a entrada sobre um fundo usando um alfa")
    s.add_argument("--alfa", required=True), s.add_argument("--fundo", required=True)
    s.add_argument("--wrap", type=float, default=0.05), s.add_argument("--sem-descontaminar", action="store_true")

    s = add("reenquadrar", cmd_reenquadrar, "recorte inteligente ou expansão de tela por IA")
    s.add_argument("--proporcao", required=True, help="ex.: 4:5, 1:1, 16:9")
    s.add_argument("--alfa"), s.add_argument("--expandir", action="store_true")
    s.add_argument("--prompt", default=""), s.add_argument("--seed", type=int, default=0)

    s = add("conferir", cmd_conferir, "mede a preservação entre original e resultado", out=False)
    s.add_argument("resultado"), s.add_argument("--mascara")

    s = add("comparar", cmd_comparar, "folha lado a lado (ou zoom numa região)", io=False)
    s.add_argument("saida"), s.add_argument("imagens", nargs="+")
    s.add_argument("--rotulos", nargs="*"), s.add_argument("--altura", type=int, default=900)
    s.add_argument("--colunas", type=int), s.add_argument("--zoom", help="'x0,y0,x1,y1' relativos (0..1)")

    s = add("modelos", cmd_modelos, "lista modelos, licenças e espaço; --baixar / --apagar", io=False)
    s.add_argument("--baixar", nargs="*"), s.add_argument("--apagar", nargs="*")
    return p


def main(argv=None):
    args = build().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
