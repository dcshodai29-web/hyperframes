/* SCIENCE CINEMATIC · biblioteca WebGL do canal (sem dependências).
 *
 * Cada cena desenha a partir do próprio tempo local (onUpdate de um tween GSAP), então todo
 * quadro é uma função pura do tempo: render determinístico, em qualquer ordem.
 *
 * Programas:
 *   olho       macro do olho humano (íris procedural, córnea úmida, buraco, olhar)
 *   retina     túnel de luz pelo olho, fundo de olho natural e camada de fotorreceptores
 *   campos     paisagem e os campos visuais dos dois olhos, com o preenchimento do ponto cego
 *   mosaico    o mundo montado pelo cérebro, em ladrilhos
 *   particulas a informação dos sentidos fluindo para o olho e, filtrada, para o córtex
 */
(function () {
  "use strict";

  const COMUM = `
precision highp float;
uniform vec2 uRes;
uniform float uT;
uniform float uGrao;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p, float oct) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 7; i++) { if (float(i) >= oct) break; v += a * noise(p); p = p * 2.03 + 17.1; a *= 0.5; }
  return v;
}
vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
vec2 fragTopo() { return vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y); }
vec2 rot(vec2 v, float a) { float c = cos(a), s = sin(a); return vec2(c * v.x - s * v.y, s * v.x + c * v.y); }
// poeira fora de foco, na frente da lente (não acompanha o zoom)
vec3 poeira(vec2 frag, float t) {
  vec3 c = vec3(0.0);
  for (int k = 0; k < 3; k++) {
    float cel = 150.0 + float(k) * 70.0;
    vec2 q = frag / cel + vec2(t * (0.05 + 0.03 * float(k)), -t * 0.04);
    vec2 id = floor(q), fq = fract(q);
    vec2 pos = vec2(hash(id + float(k)), hash(id + 7.0 + float(k)));
    float d = length(fq - pos) * cel;
    float raio = 10.0 + 18.0 * hash(id + 3.0);
    float vivo = step(0.72, hash(id + 11.0 + float(k)));
    c += vec3(1.0, 0.92, 0.80) * vivo * (1.0 - smoothstep(raio * 0.6, raio, d));
  }
  return c;
}
float feixes(vec2 frag, float t) {
  vec2 s = frag / uRes;
  float f = pow(max(0.0, cos((s.x * 1.4 + s.y * 0.9) * 9.0 + 1.3)), 6.0);
  return f * smoothstep(1.0, 0.0, s.y) * (0.6 + 0.4 * noise(vec2(s.x * 6.0 + t * 0.15, s.y * 3.0)));
}
vec3 finalizar(vec3 col, vec2 frag, float t) {
  col = aces(col * 1.05);
  col += (hash(frag + floor(t * 30.0) * 13.7) - 0.5) * uGrao;
  return pow(max(col, 0.0), vec3(0.92));
}
`;

  /* ---------- olho ---------- */
  const OLHO =
    COMUM +
    `
uniform vec2 uCentro;   // centro do globo na tela (px)
uniform float uZoom;    // escala do espaço do olho
uniform float uPupila;  // diâmetro relativo da pupila
uniform float uBuraco;  // raio do buraco no espaço do olho (0 = sem buraco)
uniform vec2 uOlhar;    // deslocamento da íris (espaço do olho)
uniform float uPoeira;  // 0..1: poeira e feixes
float fibras(float ang, float rn, float oct) {
  float a2 = ang < 0.0 ? ang + 6.2832 : ang - 6.2832;
  float w = smoothstep(2.6, 3.1416, abs(ang));
  return mix(fbm(vec2(ang * 38.0, rn * 5.0), oct), fbm(vec2(a2 * 38.0, rn * 5.0), oct), 0.5 * w);
}
void main() {
  vec2 frag = fragTopo();
  vec2 p = (frag - uCentro) / uZoom;
  float r = length(p);
  float R = 470.0;
  // a íris gira com o olhar; leve escorço na direção do olhar
  vec2 pi = p - uOlhar;
  float g = length(uOlhar);
  if (g > 1.0) { vec2 d = uOlhar / g; float par = dot(pi, d); pi = pi + d * par * (0.22 * g / R); }
  float ri = length(pi), ang = atan(pi.y, pi.x), rn = ri / R;
  float foco = smoothstep(480.0, 1100.0, r);
  float oct = mix(6.0, 2.0, foco);

  float esfera = clamp(1.0 - pow(r / 1250.0, 2.0), 0.0, 1.0);
  vec3 esclera = vec3(0.70, 0.66, 0.62) * (0.10 + 0.90 * esfera * esfera);
  esclera = mix(esclera, vec3(0.72, 0.42, 0.40) * (0.3 + 0.7 * esfera),
    0.25 * smoothstep(0.55, 0.8, fbm(p * 0.006, 4.0)) * smoothstep(420.0, 900.0, r));
  float sombraLid = smoothstep(-900.0, -380.0, p.y + 60.0 * (fbm(vec2(p.x * 0.004, 1.0), 3.0) - 0.5));
  esclera *= 0.12 + 0.88 * sombraLid;

  float pr = 0.30 * uPupila;
  float f = fibras(ang, rn, oct);
  vec3 interno = vec3(0.62, 0.40, 0.15), meio = vec3(0.32, 0.40, 0.22), fora = vec3(0.18, 0.24, 0.16);
  vec3 iris = mix(interno, meio, smoothstep(pr * 1.25, 0.62, rn));
  iris = mix(iris, fora, smoothstep(0.62, 0.92, rn));
  iris *= 0.45 + 0.95 * f;
  iris += vec3(0.30, 0.20, 0.08) * exp(-pow((rn - pr * 1.55) / 0.035, 2.0)) * (0.5 + f);
  float criptas = smoothstep(0.62, 0.70, fbm(vec2(ang * 9.0, rn * 7.0) + 3.0, 4.0));
  iris *= 1.0 - 0.45 * criptas * smoothstep(pr, pr * 1.8, rn);
  iris *= 1.0 - 0.85 * smoothstep(0.80, 1.0, rn);
  iris *= 0.75 + 0.25 * sombraLid;
  float pupila = 1.0 - smoothstep(pr - 0.012, pr + 0.008, rn);
  iris = mix(iris, vec3(0.01, 0.012, 0.016), pupila);
  float naIris = 1.0 - smoothstep(0.985, 1.005, rn);
  vec3 col = mix(esclera, iris, naIris);

  // key quente pela esquerda, rim azul elétrico pela direita
  col *= 0.55 + 0.6 * smoothstep(650.0, -500.0, p.x);
  col += vec3(0.09, 0.41, 1.0) * 0.10 * smoothstep(300.0, 1000.0, p.x);
  // córnea úmida: reflexo de janela, brilho pontual, anel de refração
  vec2 j = (pi - vec2(-160.0, -200.0)) / vec2(150.0, 98.0);
  float janela = 1.0 - smoothstep(0.75, 1.0, pow(pow(abs(j.x), 4.0) + pow(abs(j.y), 4.0), 0.25));
  janela *= (0.8 + 0.2 * smoothstep(-1.0, 1.0, j.y)) * (1.0 - 0.6 * (1.0 - smoothstep(0.0, 6.0, abs(pi.x + 160.0))) * step(abs(j.y), 1.0));
  float ponto = exp(-pow(length(pi - vec2(200.0, -300.0)) / 20.0, 2.0));
  float corneaR = 1.0 - smoothstep(1.02, 1.06, rn);
  col += vec3(1.0, 0.97, 0.92) * (0.6 * janela + 0.9 * ponto) * corneaR;
  col += vec3(0.85, 0.9, 1.0) * 0.12 * exp(-pow((rn - 1.0) / 0.02, 2.0));
  col += vec3(1.0, 0.96, 0.9) * 0.06 * exp(-pow(length(p - vec2(-520.0, -260.0)) / 260.0, 2.0)) * (1.0 - naIris);
  col += vec3(0.6, 0.75, 1.0) * 0.05 * corneaR * smoothstep(0.4, 1.0, rn);

  // o buraco recorta a imagem, preso ao globo (acompanha o zoom)
  float buraco = (1.0 - smoothstep(uBuraco - 2.0, uBuraco + 1.0, length(p - vec2(330.0, 45.0)))) * step(0.5, uBuraco);
  col = mix(col, vec3(0.0), buraco);

  float fx = feixes(frag, uT);
  col += vec3(1.0, 0.9, 0.75) * 0.05 * fx * (1.0 - buraco) * uPoeira;
  col += 0.10 * poeira(frag, uT) * (0.4 + fx) * uPoeira;
  float vin = smoothstep(1.25, 0.35, length((frag - uRes * vec2(0.5, 0.469)) / (uRes * vec2(0.704, 0.599))));
  col *= 0.25 + 0.75 * vin;
  gl_FragColor = vec4(finalizar(col, frag, uT), 1.0);
}
`;

  /* ---------- retina ---------- */
  const RETINA =
    COMUM +
    `
uniform float uTunel;   // 0..1 presença do túnel
uniform float uLente;   // raio do anel de luz do cristalino (px)
uniform float uRetina;  // 0..1 revelação da retina
uniform vec4 uCam;      // xy: disco na tela, z: zoom, w: rotação
uniform float uRecep;   // 0..1 camada de fotorreceptores
uniform float uAnel;    // 0..1 contorno ciano do disco
uniform float uPulso;   // tempo dos sinais correndo para o nervo
const float DISCO = 110.0;
float vaso(vec2 q, float a0, float curva, float larg, float fase) {
  float r = length(q);
  float a = atan(q.y, q.x);
  float alvo = a0 + curva * (r / 1000.0) + 0.06 * sin(r / 70.0 + fase);
  float da = mod(a - alvo + 3.14159, 6.28318) - 3.14159;
  if (cos(da) < 0.0) return 0.0;
  float d = abs(r * sin(da));
  float w = mix(larg, larg * 0.25, smoothstep(DISCO, 1300.0, r));
  return (1.0 - smoothstep(w * 0.5, w, d)) * smoothstep(DISCO * 0.5, DISCO * 0.9, r);
}
float hexDist(vec2 p) {
  vec2 r = vec2(1.0, 1.7320508), h = r * 0.5;
  vec2 a = mod(p, r) - h, b = mod(p - h, r) - h;
  return dot(a, a) < dot(b, b) ? length(a) : length(b);
}
vec2 hexId(vec2 p) {
  vec2 r = vec2(1.0, 1.7320508), h = r * 0.5;
  vec2 a = mod(p, r) - h, b = mod(p - h, r) - h;
  return dot(a, a) < dot(b, b) ? p - a : p - b;
}
vec3 fundoOlho(vec2 q) {
  float r = length(q);
  vec3 base = vec3(0.80, 0.32, 0.12) * (0.75 + 0.35 * fbm(q * 0.004 + 3.0, 5.0));
  base = mix(base, vec3(0.50, 0.15, 0.07), 0.35 * smoothstep(700.0, 120.0, length(q - vec2(620.0, 30.0))));
  base *= 0.55 + 0.45 * smoothstep(1900.0, 200.0, r);
  float v = 0.0;
  v = max(v, vaso(q, -1.25, 0.95, 22.0, 0.0));
  v = max(v, vaso(q, 1.25, -0.95, 22.0, 1.3));
  v = max(v, vaso(q, -0.60, 0.40, 12.0, 2.1));
  v = max(v, vaso(q, 0.60, -0.40, 12.0, 0.7));
  v = max(v, vaso(q, -2.45, -0.30, 9.0, 1.9));
  v = max(v, vaso(q, 2.45, 0.30, 9.0, 2.6));
  v = max(v, vaso(q, 3.05, 0.05, 7.0, 0.4) * 0.8);
  vec3 cor = mix(base, vec3(0.42, 0.06, 0.04), v * 0.85);
  float disco = 1.0 - smoothstep(DISCO - 6.0, DISCO + 4.0, r);
  vec3 cd = mix(vec3(0.96, 0.80, 0.55), vec3(1.0, 0.95, 0.82), 1.0 - smoothstep(20.0, 55.0, r));
  cd *= 0.85 + 0.15 * fbm(q * 0.02, 3.0);
  cor = mix(cor, cd, disco);
  cor = mix(cor, vec3(0.55, 0.12, 0.07), v * disco * 0.55);
  // sinais (axônios) correndo para o disco
  float pulso = pow(max(0.0, sin(r * 0.03 + uPulso * 9.0)), 12.0) * v * smoothstep(DISCO, 300.0, r) * smoothstep(1100.0, 400.0, r);
  cor += vec3(0.0, 0.85, 1.0) * pulso * 0.5 * uRecep;
  return cor;
}
vec3 tunel(vec2 frag, float t) {
  vec2 d = frag - uRes * vec2(0.5, 0.47);
  float r = length(d) + 1.0, a = atan(d.y, d.x);
  // ruído angular sem costura em ±π (mistura com a volta completa perto da emenda)
  float a2 = a < 0.0 ? a + 6.2832 : a - 6.2832;
  float w = smoothstep(2.6, 3.1416, abs(a));
  float z = log(r) * 3.0 - t * 7.0;
  float n = mix(noise(vec2(a * 14.0, z)), noise(vec2(a2 * 14.0, z)), 0.5 * w);
  float raios = pow(n, 3.0) * smoothstep(40.0, 420.0, r);
  vec3 c = vec3(1.0, 0.86, 0.66) * raios * 0.9 + vec3(0.09, 0.41, 1.0) * 0.18 * raios;
  c += vec3(1.0, 0.95, 0.85) * 0.8 * exp(-pow((r - uLente) / 45.0, 2.0)) * step(1.0, uLente);
  return c * (0.4 + 0.6 * smoothstep(1300.0, 100.0, r));
}
void main() {
  vec2 frag = fragTopo();
  vec2 q = rot(frag - uCam.xy, uCam.w) / uCam.z;
  float r = length(q);
  vec3 ret = fundoOlho(q);
  // fotorreceptores: mosaico hexagonal, os de longe acendem primeiro; nenhum dentro do disco
  float cel = 26.0;
  vec2 hp = q / cel;
  float hd = hexDist(hp);
  vec2 id = hexId(hp);
  float distN = clamp(r / 1400.0, 0.0, 1.0);
  float aparece = smoothstep(0.0, 0.18, uRecep * 1.35 - (1.0 - distN));
  float fora = smoothstep(DISCO * 0.98, DISCO * 1.25, r);
  float ponto = (1.0 - smoothstep(0.16, 0.26, hd)) * aparece * fora;
  float halo = (1.0 - smoothstep(0.0, 0.5, hd)) * aparece * fora * 0.25;
  vec3 corRec = mix(vec3(0.0, 0.85, 1.0), vec3(0.09, 0.41, 1.0), step(0.6, hash(id)));
  float pisca = 0.75 + 0.25 * sin(uT * 3.0 + hash(id + 2.0) * 6.28);
  ret = mix(ret, ret * 0.55, 0.6 * uRecep * fora);
  ret += corRec * (ponto * 1.1 + halo) * pisca;
  // contorno do ponto cego
  float anel = exp(-pow((r - DISCO * 1.12) / 3.0, 2.0)) * uAnel;
  ret += vec3(0.0, 0.85, 1.0) * anel * 1.4 + vec3(0.0, 0.5, 0.7) * exp(-pow((r - DISCO * 1.12) / 18.0, 2.0)) * uAnel * 0.35;

  float revela = 1.0 - smoothstep(uRetina * 1500.0 - 200.0, uRetina * 1500.0, length(frag - uRes * vec2(0.5, 0.47)));
  vec3 col = mix(tunel(frag, uT) * uTunel, ret, revela);
  col += 0.08 * poeira(frag, uT) * (0.3 + 0.7 * revela);
  float vin = smoothstep(1.3, 0.3, length((frag - uRes * vec2(0.5, 0.47)) / (uRes * vec2(0.704, 0.599))));
  col *= 0.3 + 0.7 * vin;
  gl_FragColor = vec4(finalizar(col, frag, uT), 1.0);
}
`;

  /* ---------- paisagem (usada pelos campos visuais e pelo mosaico) ---------- */
  const PAISAGEM = `
const float HORIZ = 0.42;
vec3 paisagem(vec2 uv, float detalhe, float pedra) {
  vec3 c;
  if (uv.y < HORIZ) {
    float k = uv.y / HORIZ;
    vec3 ceu = mix(vec3(0.07, 0.12, 0.30), vec3(0.98, 0.60, 0.30), pow(k, 2.2));
    ceu += vec3(1.0, 0.75, 0.45) * 0.5 * exp(-pow(length((uv - vec2(0.22, HORIZ - 0.01)) * vec2(1.0, 1.6)) / 0.07, 2.0));
    float nuvem = smoothstep(0.55, 0.8, fbm(vec2(uv.x * 4.0, uv.y * 12.0) + 2.0, min(detalhe, 4.0)));
    ceu = mix(ceu, ceu * 1.15 + vec3(0.05, 0.02, 0.0), nuvem * 0.4 * (1.0 - k));
    float morro = HORIZ - 0.035 * fbm(vec2(uv.x * 5.0, 1.7), 4.0) - 0.008;
    c = uv.y > morro ? vec3(0.12, 0.13, 0.19) : ceu;
  } else {
    float dy = max(uv.y - HORIZ, 0.0005);
    float s = (uv.x - 0.5) / dy;
    float fil = fract(s * 1.4);
    float sulco = smoothstep(0.36, 0.42, fil) * (1.0 - smoothstep(0.58, 0.64, fil));
    vec3 terra = vec3(0.30, 0.20, 0.11), planta = vec3(0.24, 0.40, 0.14);
    float folha = fbm(vec2(s * 6.0, 2.0 / dy), detalhe);
    vec3 campo = mix(planta * (0.7 + 0.6 * folha), terra * (0.8 + 0.3 * folha), sulco);
    campo *= 0.65 + 0.5 * smoothstep(0.0, 0.6, dy);
    campo = mix(campo, vec3(0.85, 0.55, 0.35), 0.45 * exp(-dy * 14.0));
    c = campo;
  }
  vec2 dp = (uv - vec2(0.70, 0.515)) * vec2(1.0, 1.9);
  float pe = (1.0 - smoothstep(0.014, 0.017, length(dp))) * pedra;
  vec3 cp = vec3(0.58, 0.56, 0.52) * (0.6 + 0.6 * smoothstep(0.02, -0.02, dp.x + dp.y));
  float sombra = (1.0 - smoothstep(0.012, 0.03, length((uv - vec2(0.708, 0.524)) * vec2(1.0, 3.0)))) * pedra;
  c *= 1.0 - 0.35 * sombra;
  return mix(c, cp, pe);
}
`;

  /* ---------- campos visuais ---------- */
  const CAMPOS =
    COMUM +
    PAISAGEM +
    `
uniform vec4 uPA, uPB;      // retângulos dos painéis (x, y, largura, altura) em px
uniform float uAA, uAB;     // opacidade dos painéis
uniform float uFecharA;     // 0..1: a pálpebra do olho esquerdo fecha de cima para baixo
uniform float uRaio;        // raio do buraco, em larguras de painel
uniform float uFill;        // 0..1 preenchimento do buraco do olho direito
uniform vec2 uGuias;        // x: quanto já foi traçado (0..1), y: opacidade
uniform float uAnel, uBorda, uFantasma, uCobertos;
const vec2 HA = vec2(0.30, 0.47), HB = vec2(0.70, 0.47);
float dentroRet(vec2 uv) { return step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0); }
float bordaRet(vec2 frag, vec4 R) {
  vec2 a = frag - R.xy, b = R.xy + R.zw - frag;
  float e = min(min(a.x, b.x), min(a.y, b.y));
  return (1.0 - smoothstep(1.5, 3.0, abs(e - 1.5))) * step(-3.0, e);
}
void main() {
  vec2 frag = fragTopo();
  vec3 col = vec3(0.031, 0.043, 0.071);
  vec2 uvA = (frag - uPA.xy) / uPA.zw, uvB = (frag - uPB.xy) / uPB.zw;
  float inA = dentroRet(uvA) * step(uFecharA, uvA.y), inB = dentroRet(uvB);
  float dA = length((uvA - HA) * uPA.zw) / uPA.z, dB = length((uvB - HB) * uPB.zw) / uPB.z;
  float furoA = 1.0 - smoothstep(uRaio - 0.002, uRaio, dA);
  float furoB = 1.0 - smoothstep(uRaio - 0.002, uRaio, dB);
  // olho direito (B)
  if (inB > 0.5 && uAB > 0.001) {
    vec3 cB = paisagem(uvB, 5.0, 1.0) * vec3(0.97, 1.0, 1.03);
    float k = dB / uRaio;                           // 0 no centro do buraco, 1 na borda
    vec3 preench = paisagem(uvB, 2.0, 0.0);          // continuação do entorno: sem a pedra, menos detalhe
    float cheio = smoothstep(1.0 - uFill - 0.03, 1.0 - uFill, k) * step(0.001, uFill);
    vec3 furo = mix(vec3(0.0), preench, cheio);
    furo += vec3(0.0, 0.85, 1.0) * 0.5 * exp(-pow((k - (1.0 - uFill)) / 0.05, 2.0)) * step(0.001, uFill) * step(uFill, 0.999);
    // guias tracejadas: horizonte e bordas das fileiras atravessando o buraco
    if (uGuias.y > 0.0) {
      float px = 1.0 / uPB.z;
      float hor = 1.0 - smoothstep(1.2 * px, 2.4 * px, abs(uvB.y - HORIZ));
      float dy = max(uvB.y - HORIZ, 0.0005);
      float s = (uvB.x - 0.5) / dy;
      float fil = fract(s * 1.4);
      float largS = 2.0 * px / dy * 1.4;
      float bordaFil = (1.0 - smoothstep(largS, 2.0 * largS, abs(fil - 0.39))) + (1.0 - smoothstep(largS, 2.0 * largS, abs(fil - 0.61)));
      bordaFil *= step(HORIZ, uvB.y);
      float traco = step(0.45, fract((uvB.x + uvB.y) * 38.0));
      float alcance = step(1.0 - uGuias.x, k);
      furo += vec3(0.0, 0.85, 1.0) * clamp(hor + bordaFil, 0.0, 1.0) * traco * alcance * uGuias.y * 0.9;
    }
    cB = mix(cB, furo, furoB);
    col = mix(col, cB, uAB);
    // contorno ciano: o cérebro amostra a borda
    col += vec3(0.0, 0.85, 1.0) * exp(-pow((dB - uRaio) * uPB.z / 2.0, 2.0)) * uAnel * uAB;
    // onde estava a pedra
    float dpz = length((uvB - vec2(0.70, 0.515)) * uPB.zw) / uPB.z;
    float pont = exp(-pow((dpz - 0.026) * uPB.z / 1.6, 2.0)) * step(0.5, fract(atan(uvB.y - 0.515, uvB.x - 0.70) * 4.0));
    col += vec3(0.75, 0.80, 0.88) * pont * uFantasma;
  }
  // olho esquerdo (A) por cima: onde o A enxerga, ele cobre o buraco do B (e vice-versa)
  if (inA > 0.5 && uAA > 0.001) {
    vec3 cA = paisagem(uvA, 5.0, 1.0) * vec3(1.03, 1.0, 0.97);
    float vis = (1.0 - furoA) * uAA;
    col = mix(col, cA, vis);
  }
  // contornos dos buracos já cobertos pelo outro olho (tracejados)
  float tA = step(0.5, fract(atan(uvA.y - HA.y, uvA.x - HA.x) * 5.0)), tB = step(0.5, fract(atan(uvB.y - HB.y, uvB.x - HB.x) * 5.0));
  col += vec3(0.09, 0.41, 1.0) * exp(-pow((dA - uRaio) * uPA.z / 1.8, 2.0)) * tA * uCobertos * dentroRet(uvA);
  col += vec3(0.0, 0.85, 1.0) * exp(-pow((dB - uRaio) * uPB.z / 1.8, 2.0)) * tB * uCobertos * dentroRet(uvB);
  // bordas dos painéis e ponto de fixação
  col += vec3(0.09, 0.41, 1.0) * bordaRet(frag, uPA) * uBorda * uAA;
  col += vec3(0.0, 0.85, 1.0) * bordaRet(frag, uPB) * uBorda * uAB;
  vec2 cxA = abs(uvA - 0.5) * uPA.zw, cxB = abs(uvB - 0.5) * uPB.zw;
  float cruzA = step(min(cxA.x, cxA.y), 1.2) * step(max(cxA.x, cxA.y), 9.0) * inA;
  float cruzB = step(min(cxB.x, cxB.y), 1.2) * step(max(cxB.x, cxB.y), 9.0) * inB;
  col = mix(col, vec3(0.96), clamp(cruzA * uAA + cruzB * uAB, 0.0, 1.0) * uBorda * 0.9);
  gl_FragColor = vec4(finalizar(col, frag, uT), 1.0);
}
`;

  /* ---------- mosaico ---------- */
  const MOSAICO =
    COMUM +
    PAISAGEM +
    `
uniform vec4 uCerebro;     // centro (xy) e raios (zw) da elipse do cérebro, px
uniform float uChegada;    // 0..1 ladrilhos chegando
uniform float uSel;        // 0..1 seleciona: parte dos ladrilhos é descartada
uniform float uComp;       // 0..1 completa: lacunas são preenchidas
uniform float uMonta;      // 0..1 monta: a peça central encaixa (pulso)
uniform float uResolve;    // 0..1 o mosaico vira imagem contínua
uniform float uAlfa;
void main() {
  vec2 frag = fragTopo();
  vec2 e = (frag - uCerebro.xy) / uCerebro.zw;
  float le = length(e);
  if (le > 1.0 || uAlfa <= 0.0) { gl_FragColor = vec4(0.0); return; }
  float cel = 30.0;
  vec2 p = frag / cel;
  vec2 rr = vec2(1.0, 1.7320508), hh = rr * 0.5;
  vec2 a = mod(p, rr) - hh, b = mod(p - hh, rr) - hh;
  vec2 g = dot(a, a) < dot(b, b) ? a : b;
  vec2 id = p - g;
  vec2 ec = (id * cel - uCerebro.xy) / uCerebro.zw;
  float dc = length(ec);
  float r1 = hash(id * 1.37 + 0.5), r2 = hash(id * 2.11 + 3.3);
  vec2 qa = abs(g);
  float hd = max(dot(qa, vec2(0.8660254, 0.5)), qa.y);
  float aresta = smoothstep(0.40, 0.47, hd);
  float chega = smoothstep(0.0, 0.12, uChegada * 1.25 - r1);
  float descarta = step(r2, 0.30) * smoothstep(0.0, 0.5, uSel * 1.4 - r1 * 0.4);
  float volta = step(r2, 0.30) * smoothstep(0.0, 0.35, uComp * 1.3 - r1 * 0.3);
  float lacuna = step(0.86, r2) * (1.0 - smoothstep(0.0, 0.35, uComp * 1.3 - r1 * 0.3));
  float presente = clamp(chega * (1.0 - descarta) + volta, 0.0, 1.0) * (1.0 - lacuna) * step(dc, 0.97);
  float brilho = chega * (1.0 - smoothstep(0.0, 0.25, uChegada * 1.25 - r1 - 0.12));
  brilho += volta * (1.0 - smoothstep(0.0, 0.6, uComp * 1.3 - r1 * 0.3 - 0.2));
  vec3 corT = paisagem(ec * 0.5 + 0.5, 3.0, 0.0);
  vec3 corP = paisagem(e * 0.5 + 0.5, 5.0, 0.0);
  vec3 col = mix(corT, corP, uResolve);
  col *= 1.0 - 0.65 * aresta * (1.0 - uResolve);
  col = mix(col, vec3(0.0, 0.85, 1.0), clamp(brilho, 0.0, 1.0) * 0.7);
  float centro = 1.0 - smoothstep(0.08, 0.16, dc);
  col += vec3(0.0, 0.85, 1.0) * uMonta * (centro + aresta * 0.6);
  float borda = 1.0 - smoothstep(0.92, 1.0, le);
  float al = presente * borda * uAlfa;
  gl_FragColor = vec4(finalizar(col, frag, uT) * al, al);
}
`;

  /* ---------- partículas (gl.POINTS) ---------- */
  const PART_VS = `
attribute float aId;
uniform vec2 uRes;
uniform float uT;
uniform vec2 uOlho;      // entrada (olho)
uniform vec2 uCortex;    // destino no cérebro
uniform float uFluxo;    // 0..1 intensidade geral
uniform float uFiltro;   // fração que passa pelo gargalo
varying float vA;
varying vec3 vCor;
float h1(float n) { return fract(sin(n * 12.9898) * 43758.5453); }
void main() {
  float r1 = h1(aId), r2 = h1(aId + 17.0), r3 = h1(aId + 41.0), r4 = h1(aId + 77.0);
  float prog = fract(r1 + uT * (0.18 + 0.22 * r2));
  float passa = step(r3, uFiltro);
  vec2 inicio = vec2(uRes.x + 60.0, mix(180.0, uRes.y - 560.0, r4));
  vec2 pos;
  float a;
  if (prog < 0.62) {
    float k = prog / 0.62;
    float kk = k * k * (3.0 - 2.0 * k);
    pos = mix(inicio, uOlho, kk);
    pos.y += sin(k * 6.0 + r1 * 20.0) * 26.0 * (1.0 - k);
    a = mix(0.2, 1.0, k) * (passa > 0.5 ? 1.0 : 1.0 - smoothstep(0.72, 0.98, k));
    vCor = mix(vec3(0.09, 0.41, 1.0), vec3(0.55, 0.82, 1.0), k);
  } else {
    float k = (prog - 0.62) / 0.38;
    vec2 ctrl = vec2(mix(uOlho.x, uCortex.x, 0.55), uOlho.y - 150.0);
    pos = mix(mix(uOlho, ctrl, k), mix(ctrl, uCortex, k), k);
    a = passa * (1.0 - smoothstep(0.85, 1.0, k));
    vCor = vec3(0.0, 0.85, 1.0);
  }
  vA = a * uFluxo;
  vec2 clip = pos / uRes * 2.0 - 1.0;
  gl_Position = vec4(clip.x, -clip.y, 0.0, 1.0);
  gl_PointSize = mix(2.5, 6.0, r2) * (prog < 0.62 ? 1.0 : 1.35);
}
`;
  const PART_FS = `
precision highp float;
varying float vA;
varying vec3 vCor;
void main() {
  float d = length(gl_PointCoord - 0.5);
  float s = (1.0 - smoothstep(0.15, 0.5, d)) * vA;
  gl_FragColor = vec4(vCor * s, s);
}
`;

  const VS_QUAD = "attribute vec2 aPos; void main() { gl_Position = vec4(aPos, 0.0, 1.0); }";

  function compilar(gl, tipo, src) {
    const s = gl.createShader(tipo);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
      throw new Error("GLSL: " + gl.getShaderInfoLog(s));
    return s;
  }
  function programa(gl, vs, fs) {
    const p = gl.createProgram();
    gl.attachShader(p, compilar(gl, gl.VERTEX_SHADER, vs));
    gl.attachShader(p, compilar(gl, gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS))
      throw new Error("link: " + gl.getProgramInfoLog(p));
    const locs = {};
    return {
      p,
      u(nome) {
        if (!(nome in locs)) locs[nome] = gl.getUniformLocation(p, nome);
        return locs[nome];
      },
    };
  }
  function contexto(canvas) {
    const gl = canvas.getContext("webgl", {
      preserveDrawingBuffer: true,
      antialias: false,
      alpha: true,
      premultipliedAlpha: true,
    });
    if (!gl) throw new Error("WebGL indisponível");
    return gl;
  }
  function definir(gl, prog, valores) {
    for (const nome in valores) {
      const v = valores[nome],
        loc = prog.u(nome);
      if (loc === null) continue;
      if (typeof v === "number") gl.uniform1f(loc, v);
      else if (v.length === 2) gl.uniform2f(loc, v[0], v[1]);
      else if (v.length === 3) gl.uniform3f(loc, v[0], v[1], v[2]);
      else if (v.length === 4) gl.uniform4f(loc, v[0], v[1], v[2], v[3]);
    }
  }

  /** Um programa de tela cheia (fragment shader) num canvas. */
  function quadro(canvas, fonte) {
    const gl = contexto(canvas);
    const prog = programa(gl, VS_QUAD, fonte);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog.p, "aPos");
    return {
      gl,
      desenhar(valores, limpar) {
        gl.viewport(0, 0, canvas.width, canvas.height);
        if (limpar) {
          gl.clearColor(0, 0, 0, 0);
          gl.clear(gl.COLOR_BUFFER_BIT);
        }
        gl.useProgram(prog.p);
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        definir(
          gl,
          prog,
          Object.assign({ uRes: [canvas.width, canvas.height], uGrao: 0.022 }, valores),
        );
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      },
    };
  }

  /** Partículas como pontos, desenhadas por cima do que já está no canvas (aditivo). */
  function pontos(gl, n) {
    const prog = programa(gl, PART_VS, PART_FS);
    const ids = new Float32Array(n);
    for (let i = 0; i < n; i++) ids[i] = i;
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, ids, gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog.p, "aId");
    return {
      desenhar(valores) {
        gl.useProgram(prog.p);
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 1, gl.FLOAT, false, 0, 0);
        definir(gl, prog, Object.assign({ uRes: [gl.canvas.width, gl.canvas.height] }, valores));
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE);
        gl.drawArrays(gl.POINTS, 0, n);
        gl.disable(gl.BLEND);
      },
    };
  }

  // Curvas de animação determinísticas para os uniforms.
  const fc = (x) => Math.min(1, Math.max(0, x));
  const suave = (x) => {
    x = fc(x);
    return x * x * (3 - 2 * x);
  };
  const entre = (t, a, b) => suave((t - a) / (b - a));
  const saida3 = (x) => 1 - Math.pow(1 - fc(x), 3);
  const entrada3 = (x) => Math.pow(fc(x), 3);

  /** Um tween que chama `desenhar(tempoLocal)` a cada quadro em que a cena é buscada. */
  function relogio(tl, duracao, desenhar) {
    const estado = { t: 0 };
    tl.to(
      estado,
      { t: duracao, duration: duracao, ease: "none", onUpdate: () => desenhar(estado.t) },
      0,
    );
    desenhar(0);
  }

  window.CienciaGL = {
    fontes: { OLHO, RETINA, CAMPOS, MOSAICO },
    quadro,
    pontos,
    relogio,
    curvas: { fc, suave, entre, saida3, entrada3 },
  };
})();
