import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// =====================================================================
// Medical Card Premium — 9:16 premium motion graphics over the raw edit.
// Output time t (s). 0–1 s = cover. Video time v = t - COVER.
// Safe zone (TikTok / Reels): x 120–960, y 220–1440, nothing in the
// right-hand button column below y≈900.
// =====================================================================
const COVER = 1.0, VID_END = 30.6, DUR = COVER + VID_END, SRC_FRAMES = 828, FPS = 30;
window.DURATION = DUR;
const W = 1080, H = 1920;

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, b) => clamp((t - a) / (b - a));
const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const inCub = x => x * x * x;
const outCub = x => 1 - Math.pow(1 - x, 3);
const outExpo = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
const outBack = (x, s = 1.5) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
const lerp = (a, b, k) => a + (b - a) * k;
// window: 0 before a, ramps to 1 over dIn, holds, ramps out to 0 ending at b
const win = (t, a, b, dIn = .45, dOut = .3, fin = outExpo) => Math.min(fin(P(t, a, a + dIn)), 1 - ease(P(t, b - dOut, b)));
const $ = id => document.getElementById(id);
const guides = new URLSearchParams(location.search).has('guides');
if (guides) $('guides').style.display = 'block';

// ---------------------------------------------------------------------
// BASE VIDEO: camera moves + frosted masks over the burned-in captions
// ---------------------------------------------------------------------
const base = $('base'), bx = base.getContext('2d');
const blurC = new OffscreenCanvas(W, H), blx = blurC.getContext('2d');
const maskC = new OffscreenCanvas(W, H), mx = maskC.getContext('2d');
const imgCache = new Map();
function frameImg(i) {
  i = clamp(i, 1, SRC_FRAMES);
  if (imgCache.has(i)) return imgCache.get(i);
  const im = new Image(); im.src = `/build/mc/src/${String(i).padStart(4, '0')}.jpg`;
  const pr = im.decode().then(() => im); imgCache.set(i, pr);
  if (imgCache.size > 12) imgCache.delete(imgCache.keys().next().value);
  return pr;
}

// [v0, v1, x0, y0, x1, y1] in source (1080x1920) pixels
const MASKS = [
  [0, 3.62, 60, 1320, 1020, 1660],      // KHAS UNTUK GOLONGAN PROFESIONAL
  [3.38, 8.4, 80, 820, 1000, 1550],     // RM3 JUTA / LIMIT PERLINDUNGAN
  [8.05, 9.98, 110, 160, 970, 350],     // TAK CLAIM?
  [9.5, 11.78, 60, 1100, 1020, 1535],   // BONUS RM2,500 TAHUN
  [11.6, 13.06, 50, 270, 630, 480],     // VAKSIN
  [12.94, 14.62, -60, 195, 600, 440],    // HEALTH SCREENING
  [14.28, 15.75, 150, 995, 730, 1180],  // DAN LAIN-LAIN
  [14.9, 17.85, 140, 1215, 940, 1665],  // BONUS RM2,500 SETAHUN*
  [14.9, 17.85, 140, 1740, 940, 1825],  //   disclaimer
  [17.15, 22.9, 110, 165, 970, 445],    // RM3 JUTA / BILIK VIP / 15 JENIS
  [22.7, 25.45, 140, 165, 940, 315],    // MANFAAT HIBAH
  [23.82, 25.5, 270, 1285, 850, 1705],  // HILANG UPAYA KEKAL
  [25.18, 99, 140, 165, 940, 705],      // end card top
  [25.18, 99, 140, 1255, 940, 1845],    // end card bottom
];
const FULLBLUR_AT = 26.4; // CTA background

function camera(v) {
  // [start, end, s0, s1, fx, fy]
  const shots = [
    [-9, 3.5, 1.03, 1.13, 540, 700],
    [3.5, 8.1, 1.15, 1.03, 540, 900],
    [8.1, 11.7, 1.04, 1.07, 540, 640],
    [11.7, 13.0, 1.04, 1.13, 560, 900],
    [13.0, 14.5, 1.13, 1.04, 520, 860],
    [14.5, 17.75, 1.02, 1.09, 540, 760],
    [17.75, 22.8, 1.03, 1.15, 520, 980],
    [22.8, 25.3, 1.04, 1.12, 540, 1000],
    [25.3, 99, 1.1, 1.22, 540, 900],
  ];
  const sh = shots.find(s => v < s[1]) || shots[shots.length - 1];
  let s = lerp(sh[2], sh[3], ease(P(v, Math.max(sh[0], -1), Math.min(sh[1], 31))));
  // punch-ins on keywords
  s += .09 * outExpo(P(v, 7.96, 8.35)) * (v < 11.7 ? 1 : 0);
  s += .08 * outExpo(P(v, 10.1, 10.4)) * (v < 11.7 ? 1 : 0);
  s += .06 * outExpo(P(v, 15.0, 15.3)) * (v >= 14.5 && v < 17.75 ? 1 : 0);
  // cut "kick": every cut starts slightly zoomed and settles
  for (const c of [3.5, 11.7, 13.0, 14.5]) if (v >= c && v < c + .5) s *= 1 + .07 * (1 - outExpo(P(v, c, c + .5)));
  let fx = sh[4], fy = sh[5];
  if (v < 0) { s = 1.17 + .02 * (v + 1); fx = 540; fy = 835; } // cover framing
  // handheld micro drift
  fx += 6 * Math.sin(v * .9) ; fy += 5 * Math.sin(v * .7 + 1);
  fx = clamp(fx, W / 2 / s, W - W / 2 / s); fy = clamp(fy, H / 2 / s, H - H / 2 / s);
  return { s, fx, fy };
}

async function drawBase(v) {
  const srcV = v < 0 ? 23.6 : Math.min(v, 27.5);
  const img = await frameImg(Math.round(srcV * FPS) + 1);
  const { s, fx, fy } = camera(v);
  bx.setTransform(1, 0, 0, 1, 0, 0); bx.filter = 'none'; bx.globalAlpha = 1;
  bx.fillStyle = '#040d22'; bx.fillRect(0, 0, W, H);
  const T = () => { bx.setTransform(s, 0, 0, s, W / 2 - fx * s, H / 2 - fy * s); };
  T(); bx.filter = 'contrast(1.06) saturate(1.04)'; bx.drawImage(img, 0, 0); bx.filter = 'none';

  // masks
  const act = [];
  for (const m of MASKS) { const a = Math.min(P(srcV, m[0], m[0] + .14), 1 - P(srcV, m[1] - .14, m[1])); if (a > 0) act.push([a, m]); }
  const full = v < 0 ? 0 : ease(P(v, FULLBLUR_AT, FULLBLUR_AT + .7));
  if (act.length || full > 0) {
    blx.setTransform(1, 0, 0, 1, 0, 0); blx.globalCompositeOperation = 'source-over'; blx.clearRect(0, 0, W, H);
    blx.filter = `blur(${full > 0 ? lerp(30, 38, full) : 30}px) saturate(1.1)`; blx.drawImage(img, 0, 0); blx.filter = 'none';
    blx.fillStyle = `rgba(6,18,46,${lerp(.30, .58, full)})`; blx.fillRect(0, 0, W, H);
    mx.setTransform(1, 0, 0, 1, 0, 0); mx.clearRect(0, 0, W, H); mx.filter = 'blur(28px)';
    for (const [a, m] of act) { mx.fillStyle = `rgba(0,0,0,${a})`; mx.fillRect(m[2] - 36, m[3] - 36, m[4] - m[2] + 72, m[5] - m[3] + 72); }
    if (full > 0) { mx.fillStyle = `rgba(0,0,0,${full})`; mx.fillRect(-100, -100, W + 200, H + 200); }
    mx.filter = 'none';
    blx.globalCompositeOperation = 'destination-in'; blx.drawImage(maskC, 0, 0); blx.globalCompositeOperation = 'source-over';
    T(); bx.drawImage(blurC, 0, 0);
  }
  bx.setTransform(1, 0, 0, 1, 0, 0);
}

// ---------------------------------------------------------------------
// THREE.JS
// ---------------------------------------------------------------------
const gl = $('gl');
const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.12;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;
const CAMZ = 40;
const cam = new THREE.PerspectiveCamera(2 * Math.atan(9.6 / CAMZ) * 180 / Math.PI, W / H, .1, 200);
cam.position.set(0, 0, CAMZ);
const px = (x, y, z = 0) => new THREE.Vector3((x - W / 2) / 100, (H / 2 - y) / 100, z);

scene.add(new THREE.HemisphereLight(0xfff1d6, 0x0a1a44, .9));
const key = new THREE.DirectionalLight(0xfff0d8, 3.0); key.position.set(4, 6, 10); scene.add(key);
const rim = new THREE.DirectionalLight(0x6f9cff, 2.2); rim.position.set(-6, 2, -6); scene.add(rim);
const spot = new THREE.PointLight(0xffd9a0, 60, 30); spot.position.set(-4, -3, 8); scene.add(spot);

const M = {
  gold: new THREE.MeshPhysicalMaterial({ color: 0xe0b04f, metalness: 1, roughness: .22, clearcoat: .6, clearcoatRoughness: .2, envMapIntensity: 1.6 }),
  goldSoft: new THREE.MeshPhysicalMaterial({ color: 0xd9a744, metalness: 1, roughness: .38, envMapIntensity: 1.4 }),
  navy: new THREE.MeshPhysicalMaterial({ color: 0x0b1f4a, metalness: .3, roughness: .25, clearcoat: 1, clearcoatRoughness: .05 }),
  ivory: new THREE.MeshPhysicalMaterial({ color: 0xfbf4e2, metalness: 0, roughness: .2, clearcoat: 1, emissive: 0xfff1cf, emissiveIntensity: .12 }),
  holo: new THREE.MeshBasicMaterial({ color: 0xf5d68c, transparent: true, opacity: .8, blending: THREE.AdditiveBlending, depthWrite: false }),
};
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
const goldGrad = (g, x0, y0, x1, y1) => { const gr = g.createLinearGradient(x0, y0, x1, y1);
  [[0, '#8a6420'], [.2, '#f0cf7c'], [.35, '#fff3cc'], [.5, '#d9a947'], [.7, '#9b6e24'], [.85, '#f3d482'], [1, '#b6852f']].forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };
function rrect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
const glowTex = canvasTex(256, 256, (g) => { const r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  r.addColorStop(0, 'rgba(255,240,200,1)'); r.addColorStop(.25, 'rgba(255,205,120,.5)'); r.addColorStop(1, 'rgba(255,170,60,0)'); g.fillStyle = r; g.fillRect(0, 0, 256, 256); });
const glow = (s, op = .7) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false })); m.scale.set(s, s, 1); return m; };

await document.fonts.load('900 80px Play'); await document.fonts.load('italic 900 80px Play'); await document.fonts.load('800 40px Mont'); await document.fonts.load('600 40px Mont');
await document.fonts.ready;

// ---------- medical card ----------
function shieldPath(g, cx, cy, s) {
  g.beginPath(); g.moveTo(cx, cy - s); g.bezierCurveTo(cx + .45 * s, cy - .78 * s, cx + .8 * s, cy - .8 * s, cx + .82 * s, cy - .8 * s);
  g.lineTo(cx + .82 * s, cy - .1 * s); g.bezierCurveTo(cx + .8 * s, cy + .45 * s, cx + .4 * s, cy + .8 * s, cx, cy + s);
  g.bezierCurveTo(cx - .4 * s, cy + .8 * s, cx - .8 * s, cy + .45 * s, cx - .82 * s, cy - .1 * s); g.lineTo(cx - .82 * s, cy - .8 * s);
  g.bezierCurveTo(cx - .8 * s, cy - .8 * s, cx - .45 * s, cy - .78 * s, cx, cy - s); g.closePath();
}
const CW = 6.0, CH = 3.78;
const cardFront = canvasTex(1600, 1008, (g, w, h) => {
  let gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#132c63'); gr.addColorStop(.55, '#081a40'); gr.addColorStop(1, '#030b20');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  const rg = g.createRadialGradient(w * .8, h * .1, 0, w * .8, h * .1, w * .7); rg.addColorStop(0, 'rgba(120,160,255,.28)'); rg.addColorStop(1, 'rgba(120,160,255,0)'); g.fillStyle = rg; g.fillRect(0, 0, w, h);
  g.lineWidth = 2; // guilloche
  for (let k = 0; k < 34; k++) { g.strokeStyle = `rgba(226,184,92,${.05 + .05 * (k % 3 === 0)})`; g.beginPath();
    for (let x = 0; x <= w; x += 8) { const y = h * .62 + k * 9 - 150 + Math.sin(x / 140 + k * .35) * 60 + Math.sin(x / 47 + k) * 8; x ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); }
  // emblem
  shieldPath(g, 150, 160, 70); g.fillStyle = goldGrad(g, 80, 90, 220, 230); g.fill();
  g.fillStyle = '#0b1f4a'; g.fillRect(140, 118, 20, 84); g.fillRect(108, 150, 84, 20);
  g.fillStyle = '#f7e6b8'; g.font = '800 46px Mont'; g.letterSpacing = '10px'; g.fillText('MEDICAL CARD', 250, 150);
  g.font = 'italic 900 92px Play'; g.letterSpacing = '0px'; g.fillStyle = goldGrad(g, 250, 160, 700, 260); g.fillText('Premium', 248, 236);
  // chip
  rrect(g, 110, 380, 190, 145, 26); g.fillStyle = goldGrad(g, 110, 380, 300, 525); g.fill();
  g.strokeStyle = 'rgba(90,60,15,.6)'; g.lineWidth = 4; g.beginPath(); g.moveTo(110, 452); g.lineTo(300, 452); g.moveTo(205, 380); g.lineTo(205, 525);
  g.moveTo(160, 380); g.lineTo(160, 525); g.moveTo(250, 380); g.lineTo(250, 525); g.stroke();
  // contactless
  g.strokeStyle = 'rgba(247,225,160,.8)'; g.lineWidth = 7; g.lineCap = 'round';
  for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(340, 452, 26 + i * 22, -.7, .7); g.stroke(); }
  g.fillStyle = 'rgba(247,230,190,.75)'; g.font = '600 34px Mont'; g.letterSpacing = '8px'; g.fillText('LIMIT TAHUNAN', 110, 690);
  g.font = '900 150px Play'; g.letterSpacing = '0px'; g.fillStyle = goldGrad(g, 110, 700, 1100, 860); g.fillText('RM3,000,000', 104, 840);
  g.fillStyle = 'rgba(247,230,190,.7)'; g.font = '600 32px Mont'; g.letterSpacing = '7px'; g.fillText('GOLONGAN PROFESIONAL', 110, 940);
  g.textAlign = 'right'; g.fillStyle = goldGrad(g, 1300, 900, 1500, 960); g.font = '800 40px Mont'; g.fillText('TAKAFUL', 1500, 940);
  g.strokeStyle = 'rgba(247,225,160,.55)'; g.lineWidth = 4; rrect(g, 12, 12, w - 24, h - 24, 64); g.stroke();
});
const cardBack = canvasTex(800, 504, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#0d2352'); gr.addColorStop(1, '#040c22'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.fillStyle = '#05091a'; g.fillRect(0, 60, w, 80);
  shieldPath(g, w / 2, 320, 80); g.fillStyle = goldGrad(g, w / 2 - 80, 240, w / 2 + 80, 400); g.fill();
  g.fillStyle = '#0b1f4a'; g.fillRect(w / 2 - 11, 275, 22, 90); g.fillRect(w / 2 - 45, 309, 90, 22);
});
function roundedShape(w, h, r) { const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s; }
function normUV(geo, w, h) { const p = geo.attributes.position, uv = geo.attributes.uv; for (let i = 0; i < p.count; i++) uv.setXY(i, p.getX(i) / w + .5, p.getY(i) / h + .5); uv.needsUpdate = true; return geo; }
function makeCard() {
  const g = new THREE.Group(), sh = roundedShape(CW, CH, .28), D = .05, B = .03;
  const body = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: D, bevelEnabled: true, bevelThickness: B, bevelSize: B, bevelSegments: 4, curveSegments: 16 }), M.gold);
  body.position.z = -D / 2; g.add(body);
  const fg = normUV(new THREE.ShapeGeometry(sh, 16), CW, CH);
  const front = new THREE.Mesh(fg, new THREE.MeshPhysicalMaterial({ map: cardFront, roughness: .3, metalness: .25, clearcoat: 1, clearcoatRoughness: .08, envMapIntensity: .9 }));
  front.position.z = D / 2 + B + .003; g.add(front);
  const back = new THREE.Mesh(normUV(new THREE.ShapeGeometry(sh, 16), CW, CH), new THREE.MeshPhysicalMaterial({ map: cardBack, roughness: .35, metalness: .2, clearcoat: 1 }));
  back.rotation.y = Math.PI; back.position.z = -D / 2 - B - .003; g.add(back);
  return g;
}
const card = makeCard(); scene.add(card);
const cardGlow = glow(9, .0); scene.add(cardGlow);

// ---------- shield ----------
function shieldShape(s) { const sh = new THREE.Shape();
  sh.moveTo(0, s); sh.bezierCurveTo(.45 * s, .78 * s, .8 * s, .8 * s, .82 * s, .8 * s); sh.lineTo(.82 * s, .1 * s);
  sh.bezierCurveTo(.8 * s, -.45 * s, .4 * s, -.8 * s, 0, -s); sh.bezierCurveTo(-.4 * s, -.8 * s, -.8 * s, -.45 * s, -.82 * s, .1 * s);
  sh.lineTo(-.82 * s, .8 * s); sh.bezierCurveTo(-.8 * s, .8 * s, -.45 * s, .78 * s, 0, s); return sh; }
function crossShape(a, b) { const s = new THREE.Shape(); s.moveTo(-b, a); s.lineTo(b, a); s.lineTo(b, b); s.lineTo(a, b); s.lineTo(a, -b); s.lineTo(b, -b); s.lineTo(b, -a);
  s.lineTo(-b, -a); s.lineTo(-b, -b); s.lineTo(-a, -b); s.lineTo(-a, b); s.lineTo(-b, b); s.closePath(); return s; }
const shield = new THREE.Group(); scene.add(shield);
{
  const outer = new THREE.Mesh(new THREE.ExtrudeGeometry(shieldShape(2.2), { depth: .35, bevelEnabled: true, bevelThickness: .14, bevelSize: .12, bevelSegments: 6, curveSegments: 32 }), M.gold);
  outer.position.z = -.35; shield.add(outer);
  const inner = new THREE.Mesh(new THREE.ExtrudeGeometry(shieldShape(1.78), { depth: .08, bevelEnabled: true, bevelThickness: .05, bevelSize: .05, bevelSegments: 4, curveSegments: 32 }), M.navy);
  inner.position.z = .1; shield.add(inner);
  const cross = new THREE.Mesh(new THREE.ExtrudeGeometry(crossShape(.95, .3), { depth: .18, bevelEnabled: true, bevelThickness: .07, bevelSize: .06, bevelSegments: 5 }), M.ivory);
  cross.position.set(0, .12, .22); shield.add(cross);
}
const shieldGlow = glow(10, 0); scene.add(shieldGlow);

// holographic rings (platform)
function holoRing(r, w, op) { const m = new THREE.Mesh(new THREE.RingGeometry(r - w, r, 128), M.holo.clone()); m.material.opacity = op; m.rotation.x = -Math.PI / 2 + .28; return m; }
const rings = new THREE.Group(); scene.add(rings);
const ringList = [holoRing(2.6, .035, .9), holoRing(3.1, .015, .6), holoRing(3.7, .05, .35), holoRing(2.0, .012, .7)];
ringList.forEach(r => rings.add(r));
const ticks = new THREE.Group(); rings.add(ticks);
for (let i = 0; i < 60; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(.025, i % 5 ? .12 : .26), M.holo); const a = i / 60 * Math.PI * 2;
  m.position.set(Math.cos(a) * 3.35, 0, Math.sin(a) * 3.35); m.rotation.x = -Math.PI / 2; m.rotation.z = -a; ticks.add(m); }
ticks.rotation.x = .28;

// ---------- coins ----------
const coinFace = canvasTex(512, 512, (g, w) => {
  g.fillStyle = goldGrad(g, 0, 0, w, w); g.fillRect(0, 0, w, w);
  g.strokeStyle = 'rgba(110,75,15,.55)'; g.lineWidth = 14; g.beginPath(); g.arc(256, 256, 200, 0, 7); g.stroke();
  g.fillStyle = 'rgba(105,70,14,.8)'; g.font = '900 170px Play'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('RM', 256, 266);
});
const coinGeo = new THREE.CylinderGeometry(.62, .62, .11, 64);
const coinMats = [M.gold, new THREE.MeshPhysicalMaterial({ map: coinFace, color: 0xffe2a0, metalness: .85, roughness: .42, envMapIntensity: .9 }), null];
coinMats[2] = coinMats[1];
const coins = [];
for (let i = 0; i < 12; i++) { const c = new THREE.Mesh(coinGeo, coinMats); c.visible = false; scene.add(c); coins.push(c); }

// ---------- medical icons ----------
function capsule() { const g = new THREE.Group();
  const a = new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, .5, 40), M.ivory); a.position.y = .25; g.add(a);
  const a2 = new THREE.Mesh(new THREE.SphereGeometry(.3, 40, 20, 0, 6.3, 0, Math.PI / 2), M.ivory); a2.position.y = .5; g.add(a2);
  const b = new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, .5, 40), M.gold); b.position.y = -.25; g.add(b);
  const b2 = new THREE.Mesh(new THREE.SphereGeometry(.3, 40, 20, 0, 6.3, Math.PI / 2, Math.PI / 2), M.gold); b2.position.y = -.5; g.add(b2);
  g.rotation.z = .7; return g; }
function heart() { const s = new THREE.Shape(); s.moveTo(0, -.6); s.bezierCurveTo(-.15, -.4, -.75, -.05, -.62, .35); s.bezierCurveTo(-.5, .7, -.1, .72, 0, .38);
  s.bezierCurveTo(.1, .72, .5, .7, .62, .35); s.bezierCurveTo(.75, -.05, .15, -.4, 0, -.6);
  const m = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: .22, bevelEnabled: true, bevelThickness: .1, bevelSize: .08, bevelSegments: 6, curveSegments: 24 }), M.gold); m.geometry.center(); return m; }
function crossObj() { const m = new THREE.Mesh(new THREE.ExtrudeGeometry(crossShape(.55, .18), { depth: .2, bevelEnabled: true, bevelThickness: .07, bevelSize: .06, bevelSegments: 5 }), M.ivory); m.geometry.center(); return m; }
function dna() { const g = new THREE.Group(); const sg = new THREE.SphereGeometry(.09, 16, 12);
  for (let i = 0; i < 14; i++) { const y = -.75 + i * .115, a = i * .55;
    const p1 = new THREE.Mesh(sg, M.gold); p1.position.set(Math.cos(a) * .32, y, Math.sin(a) * .32); g.add(p1);
    const p2 = new THREE.Mesh(sg, M.ivory); p2.position.set(-Math.cos(a) * .32, y, -Math.sin(a) * .32); g.add(p2);
    if (i % 2 === 0) { const r = new THREE.Mesh(new THREE.CylinderGeometry(.025, .025, .64, 8), M.goldSoft); r.position.y = y; r.rotation.z = Math.PI / 2; r.rotation.y = -a; g.add(r); } }
  return g; }
function stetho() { const g = new THREE.Group();
  const t = new THREE.Mesh(new THREE.TorusGeometry(.42, .06, 16, 48, Math.PI), M.goldSoft); t.rotation.z = Math.PI; t.position.y = .3; g.add(t);
  const d = new THREE.Mesh(new THREE.CylinderGeometry(.24, .24, .12, 40), M.gold); d.rotation.x = Math.PI / 2; d.position.y = -.45; g.add(d);
  const s = new THREE.Mesh(new THREE.CylinderGeometry(.04, .04, .7, 12), M.goldSoft); s.position.y = -.05; g.add(s);
  const di = new THREE.Mesh(new THREE.CylinderGeometry(.17, .17, .13, 40), M.ivory); di.rotation.x = Math.PI / 2; di.position.set(0, -.45, .01); g.add(di);
  return g; }
const icons = [capsule(), heart(), crossObj(), dna(), stetho()];
const iconGroup = new THREE.Group(); scene.add(iconGroup);
icons.forEach(o => { const w = new THREE.Group(); w.add(o); w.add(glow(2.2, .35)); iconGroup.add(w); });

// ---------- gold dust ----------
const NP = 320, pp = new Float32Array(NP * 3), pseed = [];
let sd = 7; const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
for (let i = 0; i < NP; i++) pseed.push([rnd() * 12 - 6, rnd() * 22 - 11, rnd() * 14 - 9, .2 + rnd() * .5, rnd() * 6.28]);
const pgeo = new THREE.BufferGeometry(); pgeo.setAttribute('position', new THREE.BufferAttribute(pp, 3));
const dot = canvasTex(64, 64, g => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, 'rgba(255,245,215,1)'); r.addColorStop(.3, 'rgba(255,214,140,.7)'); r.addColorStop(1, 'rgba(255,190,90,0)'); g.fillStyle = r; g.fillRect(0, 0, 64, 64); });
const pmat = new THREE.PointsMaterial({ size: .16, map: dot, transparent: true, opacity: .7, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true });
const dust = new THREE.Points(pgeo, pmat); scene.add(dust);

// ---------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------
function A(el, { op = 1, x = 0, y = 0, s = 1, blur = 0, rot = 0 } = {}) {
  if (typeof el === 'string') el = $(el);
  el.style.opacity = op; el.style.visibility = op <= .001 ? 'hidden' : 'visible';
  el.style.transform = `translate(${x}px, ${y}px) scale(${s}) rotate(${rot}deg)`;
  el.style.filter = blur > .2 ? `blur(${blur}px)` : 'none';
}
// standard premium entrance: rises, de-blurs, settles; exit fades up with blur
function E(el, t, a, b, o = {}) {
  const dIn = o.dIn ?? .55, dOut = o.dOut ?? .3;
  const pi = outExpo(P(t, a, a + dIn)), po = ease(P(t, b - dOut, b));
  const op = Math.min(pi, 1 - po);
  A(el, { op, y: (1 - pi) * (o.y ?? 50) - po * 30, s: lerp(o.s ?? .94, 1, pi) * lerp(1, .97, po), blur: (1 - pi) * 14 + po * 10, x: o.x ?? 0 });
  return op;
}
// wipe reveal (left → right) for display text
function wipe(el, p) { if (typeof el === 'string') el = $(el); el.style.clipPath = `inset(-30% ${(1 - p) * 100}% -30% -5%)`; }
function sheen(el, t, period = 3.2, off = 0) { if (typeof el === 'string') el = $(el); el.style.backgroundPosition = `${(((t + off) / period) % 1) * -260 + 130}% 0`; }
const fmt = n => Math.round(n).toLocaleString('en-US');
const goldEls = [...document.querySelectorAll('.gold')];
const sheenEls = [...document.querySelectorAll('.glass .sheen')];

// ---------------------------------------------------------------------
// RENDER
// ---------------------------------------------------------------------
window.renderAt = async (t) => {
  const v = t - COVER;
  await drawBase(v);
  goldEls.forEach((el, i) => sheen(el, t, 3.4, i * .37));
  sheenEls.forEach((el, i) => { el.style.left = `${-40 + (((t * .45 + i * .3) % 1.6) / 1.6) * 180}%`; });

  // ---- grade / leaks ----
  const cuts = [0, 3.5, 8.1, 11.7, 13.0, 14.5, 17.6, 22.8, 26.6];
  let leak = 0; for (const c of cuts) leak = Math.max(leak, Math.exp(-Math.pow((v - c) / .14, 2)) * (c === 0 ? 1 : .55));
  A('leak', { op: leak, s: 1 + leak * .2 });
  $('grade').style.opacity = 1;

  // ---- COVER (t 0–1) ----
  {
    const out = ease(P(t, .86, 1.0));
    A('cover', { op: 1 - out, s: 1 + out * .06, blur: out * 10 });
    const breathe = 1 + .012 * Math.sin(t * 6);
    A('cvNum', { s: breathe });
  }

  // ---- S1: roles (v 1.15–2.4), card label (2.5–3.45) ----
  E('roles', v, 1.1, 2.42, { y: 70 });
  [['r1', 1.5], ['r2', 1.65], ['r3', 1.8]].forEach(([id, a]) => { const p = outBack(P(v, a, a + .4)); A(id, { op: clamp(p * 1.4), s: lerp(.6, 1, p), y: (1 - p) * 20 }); });
  E('cardlab', v, 2.55, 3.45, { y: 40 }); wipe('clA', outCub(P(v, 2.5, 2.95))); wipe('clB', outCub(P(v, 2.75, 3.2)));

  // ---- S2: limit (v 3.6–8.25) ----
  E('limitTop', v, 3.75, 8.15, { y: -30 });
  const limOp = E('limit', v, 4.2, 8.15, { y: 60 });
  const cnt = ease(P(v, 4.4, 5.5)); $('limN').innerHTML = `<small>RM</small>${fmt(cnt * 3000000)}`;
  $('limBar').style.width = `${cnt * 100}%`;
  A('limS', { op: P(v, 5.2, 5.6), y: (1 - outCub(P(v, 5.2, 5.6))) * 14 });
  if (limOp > 0) A('limN', { s: 1 + .05 * Math.exp(-Math.pow((v - 5.55) / .12, 2)) });

  // ---- S3: tak claim / bonus ----
  { const p = outBack(P(v, 7.96, 8.3), 2.2), po = ease(P(v, 9.7, 9.98));
    A('tak', { op: Math.min(clamp(p * 2), 1 - po), s: lerp(1.6, 1, p) * (1 - po * .1), blur: (1 - clamp(p)) * 18 + po * 12, rot: (1 - clamp(p)) * -4 });
    const shake = Math.exp(-Math.max(0, v - 8.3) * 7) * (v > 8.3 ? 1 : 0); $('takT').style.transform = `translate(${Math.sin(v * 90) * 10 * shake}px, 0)`; }
  E('bonus', v, 10.05, 11.72, { y: 60, s: .85 });
  A('boK', { op: P(v, 10.45, 10.75) });
  { const c = outExpo(P(v, 10.85, 11.45)); $('boN').innerHTML = `<small>RM</small>${fmt(c * 2500)}`; }

  // ---- S4–S6: uses panel ----
  {
    const op = E('uses', v, 12.62, 16.2, { y: 40 });
    if (op > 0) { const mv = ease(P(v, 14.45, 14.85)); const el = $('uses'); el.style.top = `${lerp(236, 990, mv)}px`; el.style.width = `${lerp(640, 720, mv)}px`; }
    [['u1', 13.85], ['u2', 14.7], ['u3', 15.62]].forEach(([id, a]) => { const p = outExpo(P(v, a, a + .45)); A(id, { op: p > 0 ? .25 + .75 * p : .25, x: (1 - p) * -30 });
      const tk = $(id).querySelector('.tick'); const q = outBack(P(v, a + .15, a + .45)); tk.style.transform = `scale(${q})`; tk.style.background = q > .5 ? 'rgba(226,184,92,.25)' : 'transparent'; });
  }
  E('recap', v, 16.15, 17.8, { y: 50 });
  E('disc1', v, 16.3, 17.8, { y: 10 });

  // ---- S7: rawatan selesa (17.2–20.7) → 15 advanced treatment (20.7–22.85) ----
  E('rawat', v, 17.6, 20.72, { y: 40 }); wipe('raT', outCub(P(v, 18.9, 19.6)));
  A('raT', { op: P(v, 18.9, 19.0) });
  { const op = E('treat', v, 20.7, 22.88, { y: 40, s: .9 });
    if (op > 0) $('trN').textContent = String(Math.max(1, Math.round(outCub(P(v, 20.75, 21.3)) * 15))); }

  // ---- S8: benefits ----
  [['b1', 23.0, 0], ['b2', 24.2, 144], ['b3', 25.62, 288]].forEach(([id, a, y]) => {
    const p = outExpo(P(v, a, a + .55)), po = ease(P(v, 26.35, 26.65));
    const el = $(id); el.style.top = `${y}px`;
    A(el, { op: Math.min(p, 1 - po), x: (1 - p) * -120 + po * 60, blur: (1 - p) * 12 + po * 8, s: lerp(.96, 1, p) });
  });

  // ---- CTA ----
  {
    const k = (a, d = .6) => outExpo(P(v, a, a + d));
    A('cta', { op: P(v, 26.6, 26.75) });
    E('ctK', v, 26.75, 99); E('ctL', v, 26.9, 99); wipe('ctL', outCub(P(v, 26.9, 27.5)));
    E('ctA', v, 27.25, 99, { y: 60 }); wipe('ctA', outCub(P(v, 27.25, 27.8)));
    E('ctB', v, 27.6, 99, { y: 40 });
    const pb = outBack(P(v, 27.95, 28.45));
    const pulse = 1 + .03 * Math.max(0, Math.sin((v - 28.5) * 5.2)) * (v > 28.5 ? 1 : 0);
    A('ctBtn', { op: clamp(pb * 1.5), s: lerp(.6, 1, pb) * pulse });
    sheen('ctBtn', t, 1.8);
    const rp = ((v - 28.5) % 1.2) / 1.2; A('ctRing', { op: v > 28.5 ? (1 - rp) * .9 : 0, s: 1 + rp * .14 });
    E('disc2', v, 28.1, 99, { y: 10 });
  }

  // =================== 3D ===================
  // card
  {
    let vis = false;
    if (v >= 2.3 && v < 3.75) {
      vis = true; const p = outBack(P(v, 2.3, 2.95), 1.2), f = inCub(P(v, 3.38, 3.75));
      const pos = px(lerp(1350, 540, p), lerp(1450, 1015, p), lerp(-6, 0, p));
      pos.z += f * 34; pos.y += f * 2.3;
      card.position.copy(pos); card.scale.setScalar(.95);
      card.rotation.set(lerp(.5, .16, p) * (1 - f), lerp(-2.6, -.32, p) + .12 * Math.sin(v * 2) + f * .32, lerp(.3, -.05, p) * (1 - f));
      cardGlow.position.copy(pos).add(new THREE.Vector3(0, 0, -1)); cardGlow.material.opacity = .45 * p * (1 - f);
    } else if (v >= 26.55) {
      vis = true; const p = outExpo(P(v, 26.6, 27.6));
      const pos = px(540, 600 + 10 * Math.sin(v * 1.6), lerp(-40, 0, p)); card.position.copy(pos); card.scale.setScalar(.98);
      card.rotation.set(.14 + .04 * Math.sin(v * 1.1), lerp(Math.PI * 2.0, -.28, p) + .2 * Math.sin(v * .9), -.04);
      cardGlow.position.copy(pos).add(new THREE.Vector3(0, 0, -1.5)); cardGlow.material.opacity = .55 * p;
    }
    card.visible = vis; cardGlow.visible = vis;
  }
  // shield + rings (S2)
  {
    const vis = v >= 3.55 && v < 8.35; shield.visible = vis; shieldGlow.visible = vis;
    let ringOp = 0;
    if (vis) {
      const p = outBack(P(v, 3.62, 4.4), 1.3), o = inCub(P(v, 7.95, 8.32));
      const pos = px(540, lerp(1500, 770, p) - o * 120, o * 8);
      shield.position.copy(pos); shield.scale.setScalar(lerp(.35, 1, p) * (1 - o * .6));
      shield.rotation.set(.08 + .05 * Math.sin(v * 1.3), lerp(-1.6, 0, p) + .38 * Math.sin((v - 4.4) * 1.1) + o * 4, 0);
      shieldGlow.position.copy(pos).add(new THREE.Vector3(0, 0, -2)); shieldGlow.material.opacity = (.55 + .3 * Math.exp(-Math.pow((v - 4.5) / .2, 2))) * p * (1 - o);
      ringOp = outExpo(P(v, 4.3, 5.0)) * (1 - o);
      rings.position.copy(px(540, 1000)); rings.position.z = -1;
    }
    // CTA: rings around card
    if (v >= 26.6) { ringOp = outExpo(P(v, 27.0, 27.8)) * .8; rings.position.copy(px(540, 830)); rings.position.z = -2; }
    rings.visible = ringOp > 0;
    ringList.forEach((r, i) => { r.material.opacity = ringOp * [.9, .55, .35, .7][i]; r.scale.setScalar(lerp(.4, 1, ringOp) * (1 + .02 * Math.sin(v * 2 + i))); r.rotation.z = v * (i % 2 ? -.25 : .18); });
    ticks.rotation.y = v * .3; ticks.scale.setScalar(lerp(.4, 1, ringOp)); ticks.children.forEach(m => m.material.opacity = ringOp * .7);
  }
  // coins
  {
    coins.forEach(c => c.visible = false);
    const place = (c, x, y, z, s, rx, ry) => { c.visible = true; c.position.copy(px(x, y, z)); c.scale.setScalar(s); c.rotation.set(rx, ry, 0); };
    if (t < 1.0) {
      const L = [[190, 880, -2, .85], [890, 840, -3, .75], [860, 1050, -5, .55], [230, 1080, -6, .5]];
      L.forEach(([x, y, z, s], i) => place(coins[i], x, y + 8 * Math.sin(t * 3 + i), z, s, 1.2 + .3 * Math.sin(i), t * 1.4 + i));
    } else if (v >= 10.1 && v < 11.95) {
      const p = outExpo(P(v, 10.1, 10.7)), o = inCub(P(v, 11.55, 11.95));
      coins.slice(0, 9).forEach((c, i) => { const a = i / 9 * Math.PI * 2 + .5, r = lerp(40, i % 2 ? 480 : 420, p);
        const x = 540 + Math.cos(a) * r, y = 1240 + Math.sin(a) * r * .5 - (v - 10.1) * 40 - o * 1400 * (.6 + (i % 3) * .2);
        place(c, x, y, i % 4 === 0 ? 1 : -3 - (i % 4), lerp(.2, i % 4 === 0 ? .9 : .75, p), 1.1 + v * (1 + i % 3) * .7, v * 2 + i); });
    } else if (v >= 26.9) {
      const p = outExpo(P(v, 27.1, 28.0));
      for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + v * .55; const x = 540 + Math.cos(a) * 430 * p, z = Math.sin(a) * 3 - 2;
        place(coins[i], x, 620 + Math.sin(a) * 190 * p, z, .6 * p, 1.2 + Math.sin(v + i) * .3, v * 1.5 + i); }
    }
  }
  // medical icons orbit (15 advanced treatment)
  {
    const vis = v >= 20.65 && v < 22.95; iconGroup.visible = vis;
    if (vis) {
      const o = ease(P(v, 22.6, 22.92));
      iconGroup.children.forEach((w, i) => { const p = outBack(P(v, 20.8 + i * .12, 21.3 + i * .12), 2); const a = i / 5 * Math.PI * 2 + v * .7;
        w.position.copy(px(540 + Math.cos(a) * 330, 640 + Math.sin(a) * 70, Math.sin(a) * 3));
        w.scale.setScalar(Math.max(0.001, p * (1 - o) * .95)); w.children[0].rotation.set(.3 * Math.sin(v + i), v * 1.4 + i, 0); });
    }
  }
  // dust
  {
    let op = .35; if (t < 1) op = .9; else if (v > 26.6) op = .9; else if (v > 3.6 && v < 8.2) op = .7;
    pmat.opacity = op;
    for (let i = 0; i < NP; i++) { const [x, y, z, sp, ph] = pseed[i];
      pp[i * 3] = x + .3 * Math.sin(t * .6 + ph); pp[i * 3 + 1] = ((y + t * sp + 11) % 22) - 11; pp[i * 3 + 2] = z; }
    pgeo.attributes.position.needsUpdate = true;
  }
  renderer.render(scene, cam);
};

await Promise.all([frameImg(1), frameImg(Math.round(23.6 * FPS) + 1)]);
await window.renderAt(0);
window.ready = true;
