"""Exemplo real: manter um elemento translúcido (teia de seda) ao trocar o fundo por branco.

Não é um comando genérico: os limiares e a exclusão manual foram ajustados para UMA foto.
Serve de ponto de partida — copie, ajuste olhando o resultado e rode com o Python do ambiente.
Entradas esperadas na pasta do trabalho: 01_ampliado.png, 02_alfa_auto.png (personagem) e
_m_teia_txt.png (região da teia, de `fotoia mascara --texto "spider web"`).
"""

import sys, glob, numpy as np, cv2
sys.path.insert(0, "/home/user/hyperframes/editor-fotos")
from pathlib import Path
from fotoia import core, qa
job = Path(sorted(glob.glob("/home/user/hyperframes/editor-fotos/saidas/*spider-teia*"))[-1])
img = core.load_image(job/"01_ampliado.png"); H, W = img.shape[:2]
a_char = core.load_mask(job/"02_alfa_auto.png", img.shape)
R = core.load_mask(job/"_m_teia_txt.png", img.shape)
R0 = (R > 0.5).astype(np.float32)
# encosta no corpo (o personagem é composto por cima), sem crescer para o lado da cidade
R = np.maximum(R0, core.grow(R0, int(0.012 * H)) * (core.grow((a_char > 0.5).astype(np.float32), int(0.012 * H)) > 0))
lab = core.rgb_to_lab(img); L = lab[..., 0] / 100.0
warm = np.clip((lab[..., 2] - 12) / 22.0, 0, 1) * np.clip((np.hypot(lab[..., 1], lab[..., 2]) - 18) / 20.0, 0, 1)
# fios = estruturas FINAS e claras (top-hat de raio pequeno rejeita janelas, fachadas e nuvens)
k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
th_f = cv2.morphologyEx(L, cv2.MORPH_TOPHAT, k(5))
th_m = cv2.morphologyEx(L, cv2.MORPH_TOPHAT, k(14))
strand = np.clip(th_f * 9.0, 0, 1) * 0.9 + np.clip(th_m * 4.5, 0, 1) * 0.5
strand = np.clip(strand, 0, 1) * (1 - 0.85 * warm)            # luzes laranja da cidade não são teia
# só onde há trama de verdade: densidade de fios em escala larga
dens_map = core.blur(strand, 0.02 * H)
prior = np.clip((dens_map - 0.07) / 0.10, 0, 1)
strand = strand * prior
veil = np.clip(core.blur(strand, 0.008 * H) * 1.3, 0, 1) * 0.42   # lâmina translúcida de seda
alpha_w = np.clip(core.blur(strand, 0.9) * 1.0 + veil, 0, 1) * core.feather(R, 0.004 * H)
# contraluz forte: a teia se dissolve na luz conforme se afasta do personagem
dist = cv2.distanceTransform((a_char < 0.5).astype(np.uint8), cv2.DIST_L2, 5)
near = 0.50 + 0.50 * np.exp(-dist / (0.16 * H))
alpha_w = alpha_w * near
# limpeza manual: à direita da cabeça, acima da borda superior da rede, só há prédios (janelas viram "fios")
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
sx, sy = W / 1920.0, H / 3840.0
edge = (1685 + np.clip(xx / sx - 806, 0, None) * 0.675) * sy
excl = ((xx > 600 * sx) & (yy < edge)).astype(np.float32)
alpha_w = alpha_w * (1 - core.feather(excl, 10))
core.save_mask(alpha_w, job/"_alfa_teia.png")
# seda em contraluz: cinza-prateado suave, miolo claro onde o fio original brilhava
shade = 0.60 + 0.34 * np.clip((L - 0.35) / 0.55, 0, 1)
web = shade[..., None] * np.array([0.955, 0.975, 1.0], dtype=np.float32)
white = np.float32(0.985)
out = web * alpha_w[..., None] + white * (1 - alpha_w[..., None])
out = out * 0.78 + core.blur(out, 0.0022 * H) * 0.22        # espalhamento da luz na seda
out = np.clip(out, 0, 1).astype(np.float32)
core.save_image(out, job/"_fundo_teia_det.png")
qa.sheet([img, alpha_w, out], ["ampliado", "alfa dos fios", "teia sobre branco (det.)"], job/"_rev_teia.jpg", 1100)
z = lambda a: a[int(.25*H):int(.55*H), 0:int(.6*W)]
qa.sheet([z(img), z(out.astype(np.float32))], ["original", "fios extraidos"], job/"_rev_teia_z.jpg", 800)
