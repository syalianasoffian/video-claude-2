import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

await Promise.all(['500', '600', '700', '800', '900'].map(w => document.fonts.load(w + ' 40px Mont')).concat([document.fonts.load('italic 600 40px Play')]));
// ---------- helpers ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, b) => clamp((t - a) / (b - a));
const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const outExpo = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
const outCubic = x => 1 - Math.pow(1 - x, 3);
const outBack = (x, s = 1.6) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
const lerp = (a, b, k) => a + (b - a) * k;
const $ = id => document.getElementById(id);
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const fmt = n => 'RM' + Math.round(n).toLocaleString('en-US');

const W = 1080, H = 1920, FPS = 30, COVER = 1.0, DUR = 31.0;
const O = s => s + COVER;               // raw-footage seconds -> output seconds
const guides = new URLSearchParams(location.search).has('guides');
if (guides) $('guides').style.display = 'block';

// ---------- key cues (output seconds) ----------
const C = {
  peguam: O(.66), card: O(3.5), juta: O(4.64), caruman: O(6.54), rm217: O(7.28),
  cut1: O(10.0), menarik: O(10.38), tanpa: O(11.3), ganjaran: O(13.46), cut2: O(14.95), vaks: O(16.28),
  cut3: O(17.0), periksa: O(17.36), banyak: O(18.74), cut4: O(20.0), lengkap: O(20.14), kehamilan: O(21.26),
  hibah: O(22.88), hilang: O(23.56), n15: O(25.06), berminat: O(27.4), klik: O(28.24), end: DUR,
};

// ---------- three.js ----------
const canvas = $('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.1;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;
// 1 world unit = 100 px on the z=0 plane
const FOV = 24, DIST = (H / 200) / Math.tan(FOV / 2 * Math.PI / 180);
const camera = new THREE.PerspectiveCamera(FOV, W / H, .1, 200); camera.position.set(0, 0, DIST);
const px = (x, y, z = 0) => new THREE.Vector3((x - W / 2) / 100, (H / 2 - y) / 100, z);

scene.add(new THREE.HemisphereLight(0xfff2dc, 0x0a1a44, 1.0));
const key = new THREE.DirectionalLight(0xfff0d6, 3.0); key.position.set(4, 6, 8); scene.add(key);
const rimA = new THREE.PointLight(0x5a8cff, 60, 20); rimA.position.set(-5, 2, -2); scene.add(rimA);
const rimB = new THREE.PointLight(0xffd28a, 50, 20); rimB.position.set(5, -3, 3); scene.add(rimB);

const M = {
  gold: new THREE.MeshPhysicalMaterial({ color: 0xf0c068, metalness: 1, roughness: .2, clearcoat: .7, clearcoatRoughness: .1, envMapIntensity: 1.6 }),
  goldDark: new THREE.MeshPhysicalMaterial({ color: 0xb88a3c, metalness: 1, roughness: .32, envMapIntensity: 1.3 }),
  navy: new THREE.MeshPhysicalMaterial({ color: 0x0d2458, metalness: .35, roughness: .25, clearcoat: 1, clearcoatRoughness: .06, envMapIntensity: 1.2 }),
  pearl: new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: .05, roughness: .2, clearcoat: 1, sheen: .5, envMapIntensity: 1.2 }),
  silver: new THREE.MeshPhysicalMaterial({ color: 0xe8edf5, metalness: 1, roughness: .15 }),
  glass: new THREE.MeshPhysicalMaterial({ color: 0xdfe9ff, metalness: 0, roughness: .05, transparent: true, opacity: .28, clearcoat: 1, depthWrite: false, side: THREE.DoubleSide, envMapIntensity: 2 }),
  liquid: new THREE.MeshPhysicalMaterial({ color: 0x9fd2ff, emissive: 0x2a6bd8, emissiveIntensity: .5, roughness: .1, transparent: true, opacity: .85 }),
  holo: new THREE.MeshBasicMaterial({ color: 0xffd48a, transparent: true, opacity: .9, blending: THREE.AdditiveBlending, depthWrite: false }),
  holoGlass: new THREE.MeshBasicMaterial({ color: 0x5a86d8, transparent: true, opacity: .16, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
  window: new THREE.MeshBasicMaterial({ color: 0xffe3a8, transparent: true, opacity: .85, blending: THREE.AdditiveBlending, depthWrite: false }),
};
const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
const glowTex = canvasTex(256, 256, (g) => { const r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  r.addColorStop(0, 'rgba(255,240,200,1)'); r.addColorStop(.2, 'rgba(255,200,110,.55)'); r.addColorStop(1, 'rgba(255,170,60,0)'); g.fillStyle = r; g.fillRect(0, 0, 256, 256); });
const glow = (s, op = .7) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false })); m.scale.set(s, s, 1); m.userData.op = op; return m; };
const ring = (r, tube, mat) => new THREE.Mesh(new THREE.TorusGeometry(r, tube, 16, 160), mat);

// holographic pedestal (rings + glow) placed under an object
function pedestal(r) {
  const g = new THREE.Group();
  const r1 = ring(r, .018, M.holo); r1.rotation.x = Math.PI / 2; g.add(r1);
  const r2 = ring(r * .72, .008, M.holo.clone()); r2.material.opacity = .5; r2.rotation.x = Math.PI / 2; g.add(r2);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(r, 96), M.holoGlass); disc.rotation.x = -Math.PI / 2; g.add(disc);
  const gl = glow(r * 3.2, .45); gl.position.y = .05; g.add(gl);
  // light beam
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(r * .95, r, 1.6, 64, 1, true),
    new THREE.MeshBasicMaterial({ map: canvasTex(4, 128, (g, w, h) => { const l = g.createLinearGradient(0, 0, 0, h); l.addColorStop(0, 'rgba(255,210,130,0)'); l.addColorStop(1, 'rgba(255,210,130,.35)'); g.fillStyle = l; g.fillRect(0, 0, w, h); }),
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  beam.position.y = .8; g.add(beam);
  return g;
}

// ---------- objects ----------
function shieldShape(s = 1) {
  const sh = new THREE.Shape();
  sh.moveTo(0, 1.45 * s); sh.quadraticCurveTo(.65 * s, 1.18 * s, 1.18 * s, 1.2 * s); sh.lineTo(1.18 * s, .15 * s);
  sh.quadraticCurveTo(1.12 * s, -.95 * s, 0, -1.5 * s); sh.quadraticCurveTo(-1.12 * s, -.95 * s, -1.18 * s, .15 * s);
  sh.lineTo(-1.18 * s, 1.2 * s); sh.quadraticCurveTo(-.65 * s, 1.18 * s, 0, 1.45 * s); return sh;
}
function crossShape(a, b) { const s = new THREE.Shape(); s.moveTo(-b, a); s.lineTo(b, a); s.lineTo(b, b); s.lineTo(a, b); s.lineTo(a, -b); s.lineTo(b, -b);
  s.lineTo(b, -a); s.lineTo(-b, -a); s.lineTo(-b, -b); s.lineTo(-a, -b); s.lineTo(-a, b); s.lineTo(-b, b); s.closePath(); return s; }
function makeShield() {
  const g = new THREE.Group();
  const outer = new THREE.Mesh(new THREE.ExtrudeGeometry(shieldShape(1), { depth: .26, bevelEnabled: true, bevelThickness: .1, bevelSize: .08, bevelSegments: 6, curveSegments: 48 }), M.gold);
  outer.position.z = -.13; g.add(outer);
  const inner = new THREE.Mesh(new THREE.ExtrudeGeometry(shieldShape(.82), { depth: .1, bevelEnabled: true, bevelThickness: .04, bevelSize: .03, bevelSegments: 4, curveSegments: 48 }), M.navy);
  inner.position.set(0, -.02, .18); g.add(inner);
  const cr = new THREE.Mesh(new THREE.ExtrudeGeometry(crossShape(.56, .18), { depth: .12, bevelEnabled: true, bevelThickness: .04, bevelSize: .035, bevelSegments: 4 }), M.pearl);
  cr.position.set(0, .08, .3); g.add(cr);
  return g;
}
function cardTexture() {
  return canvasTex(1024, 640, (g, w, h) => {
    const bg = g.createLinearGradient(0, 0, w, h); bg.addColorStop(0, '#16336f'); bg.addColorStop(.55, '#0a1d48'); bg.addColorStop(1, '#050f2a');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(240,200,110,.18)'; g.lineWidth = 2;
    for (let i = 0; i < 14; i++) { g.beginPath(); g.arc(880, 120, 80 + i * 38, 0, Math.PI * 2); g.stroke(); }
    const gold = g.createLinearGradient(0, 0, 0, h); gold.addColorStop(0, '#fff1c8'); gold.addColorStop(.5, '#e3b860'); gold.addColorStop(1, '#a8782f');
    // chip
    g.fillStyle = gold; g.beginPath(); g.roundRect(80, 220, 150, 112, 18); g.fill();
    g.strokeStyle = 'rgba(80,50,10,.6)'; g.lineWidth = 3; g.beginPath(); g.moveTo(80, 276); g.lineTo(230, 276); g.moveTo(155, 220); g.lineTo(155, 332); g.stroke();
    // cross emblem
    g.fillStyle = gold; g.beginPath(); g.roundRect(830, 70, 44, 130, 8); g.fill(); g.beginPath(); g.roundRect(787, 113, 130, 44, 8); g.fill();
    g.fillStyle = gold; g.font = '800 60px Mont'; g.fillText('MEDICAL CARD', 80, 140);
    g.font = '600 30px Mont'; g.fillStyle = 'rgba(255,240,210,.85)'; g.fillText('P R E M I U M', 84, 186);
    g.font = '700 44px Mont'; g.fillStyle = '#f7f4ec'; g.fillText('LIMIT  RM3,000,000', 80, 470);
    g.font = '600 30px Mont'; g.fillStyle = 'rgba(255,240,210,.7)'; g.fillText('TAHUNAN  ·  PERLINDUNGAN PERUBATAN', 80, 530);
    g.strokeStyle = gold; g.lineWidth = 8; g.beginPath(); g.roundRect(8, 8, w - 16, h - 16, 40); g.stroke();
  });
}
function makeCard() {
  const g = new THREE.Group(), w = 3.2, h = 2.0, r = .2;
  const s = new THREE.Shape(); s.moveTo(-w / 2 + r, -h / 2); s.lineTo(w / 2 - r, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
  s.lineTo(w / 2, h / 2 - r); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); s.lineTo(-w / 2 + r, h / 2); s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
  s.lineTo(-w / 2, -h / 2 + r); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  const body = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: .06, bevelEnabled: true, bevelThickness: .02, bevelSize: .02, bevelSegments: 3, curveSegments: 24 }), M.gold);
  body.position.z = -.03; g.add(body);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(w - .06, h - .06), new THREE.MeshPhysicalMaterial({ map: cardTexture(), roughness: .25, metalness: .3, clearcoat: 1, clearcoatRoughness: .05, envMapIntensity: .8 }));
  face.position.z = .056; g.add(face);
  return g;
}
const coinTex = canvasTex(512, 512, (g) => {
  const r = g.createRadialGradient(200, 180, 20, 256, 256, 256); r.addColorStop(0, '#fff3cf'); r.addColorStop(.55, '#e3b860'); r.addColorStop(1, '#8f6526');
  g.fillStyle = r; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(90,60,15,.55)'; g.lineWidth = 14; g.beginPath(); g.arc(256, 256, 205, 0, Math.PI * 2); g.stroke();
  g.fillStyle = 'rgba(90,60,15,.75)'; g.font = '900 170px Mont'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('RM', 256, 266);
});
const coinGeo = new THREE.CylinderGeometry(.5, .5, .1, 64);
const coinMats = [M.goldDark, new THREE.MeshPhysicalMaterial({ map: coinTex, metalness: .85, roughness: .25, clearcoat: .6 }), new THREE.MeshPhysicalMaterial({ map: coinTex, metalness: .85, roughness: .25, clearcoat: .6 })];
function makeCoin() { const m = new THREE.Mesh(coinGeo, coinMats); return m; }
function makeGift() {
  const g = new THREE.Group();
  const box = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.2, 1.4), M.navy); box.position.y = .6; g.add(box);
  const rb1 = new THREE.Mesh(new THREE.BoxGeometry(.24, 1.22, 1.42), M.gold); rb1.position.y = .6; g.add(rb1);
  const rb2 = new THREE.Mesh(new THREE.BoxGeometry(1.42, 1.22, .24), M.gold); rb2.position.y = .6; g.add(rb2);
  const lid = new THREE.Group(); lid.position.y = 1.2; g.add(lid); g.userData.lid = lid;
  const lb = new THREE.Mesh(new THREE.BoxGeometry(1.56, .3, 1.56), M.navy); lb.position.y = .15; lid.add(lb);
  const l1 = new THREE.Mesh(new THREE.BoxGeometry(.26, .32, 1.58), M.gold); l1.position.y = .15; lid.add(l1);
  const l2 = new THREE.Mesh(new THREE.BoxGeometry(1.58, .32, .26), M.gold); l2.position.y = .15; lid.add(l2);
  for (const s of [-1, 1]) { const b = new THREE.Mesh(new THREE.TorusGeometry(.26, .08, 16, 48), M.gold); b.position.set(s * .26, .5, 0); b.rotation.set(0, 0, s * .5); b.scale.set(1, .75, 1); lid.add(b); }
  const knot = new THREE.Mesh(new THREE.SphereGeometry(.12, 24, 16), M.gold); knot.position.y = .42; lid.add(knot);
  return g;
}
function makeSyringe() {
  const g = new THREE.Group();
  const barrel = new THREE.Mesh(new THREE.CylinderGeometry(.26, .26, 2.0, 48, 1, true), M.glass); g.add(barrel);
  const liq = new THREE.Mesh(new THREE.CylinderGeometry(.22, .22, 1.2, 48), M.liquid); liq.position.y = -.38; g.add(liq);
  const stopper = new THREE.Mesh(new THREE.CylinderGeometry(.23, .23, .14, 48), M.navy); stopper.position.y = .3; g.add(stopper);
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(.06, .06, 1.1, 16), M.pearl); rod.position.y = .9; g.add(rod);
  const thumb = new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, .07, 48), M.gold); thumb.position.y = 1.45; g.add(thumb);
  const flange = new THREE.Mesh(new THREE.BoxGeometry(.95, .07, .3), M.gold); flange.position.y = 1.0; g.add(flange);
  const tip = new THREE.Mesh(new THREE.CylinderGeometry(.08, .26, .22, 32), M.gold); tip.position.y = -1.11; g.add(tip);
  const needle = new THREE.Mesh(new THREE.CylinderGeometry(.018, .018, .9, 12), M.silver); needle.position.y = -1.65; g.add(needle);
  for (let i = 0; i < 5; i++) { const m = new THREE.Mesh(new THREE.TorusGeometry(.262, .007, 6, 48), M.holo); m.rotation.x = Math.PI / 2; m.position.y = -.8 + i * .3; g.add(m); }
  return g;
}
function makeHeart() {
  const s = new THREE.Shape(); s.moveTo(0, -1.0); s.bezierCurveTo(-.3, -.7, -1.15, -.25, -1.1, .35); s.bezierCurveTo(-1.05, .9, -.35, 1.05, 0, .55);
  s.bezierCurveTo(.35, 1.05, 1.05, .9, 1.1, .35); s.bezierCurveTo(1.15, -.25, .3, -.7, 0, -1.0);
  const g = new THREE.Group();
  const h = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: .35, bevelEnabled: true, bevelThickness: .18, bevelSize: .14, bevelSegments: 10, curveSegments: 48 }), M.gold); h.position.z = -.17; g.add(h);
  // ECG line
  const pts = [[-1.6, 0], [-.6, 0], [-.4, .35], [-.2, -.6], [.05, .9], [.3, -.3], [.45, 0], [1.6, 0]].map(([x, y]) => new THREE.Vector3(x, y * .6, .45));
  const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, false, 'catmullrom', .05), 160, .035, 8), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  g.add(tube); g.userData.ecg = tube;
  return g;
}
function makeHospital() {
  const g = new THREE.Group();
  const blocks = [[0, 1.1, 0, 1.5, 2.2, 1.0], [-1.25, .65, .1, 1.0, 1.3, .9], [1.25, .65, .1, 1.0, 1.3, .9]];
  for (const [x, y, z, w, h, d] of blocks) {
    const geo = new THREE.BoxGeometry(w, h, d);
    const m = new THREE.Mesh(geo, M.holoGlass); m.position.set(x, y, z); g.add(m);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0xffd48a, transparent: true, opacity: .95, blending: THREE.AdditiveBlending }));
    e.position.copy(m.position); g.add(e);
    const cols = Math.round(w / .3), rows = Math.round(h / .34);
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows - 1; j++) {
      const win = new THREE.Mesh(new THREE.PlaneGeometry(.14, .16), M.window); win.position.set(x - w / 2 + (i + .5) * w / cols, y - h / 2 + .25 + j * .34, z + d / 2 + .01); g.add(win);
    }
  }
  const sign = new THREE.Mesh(new THREE.ExtrudeGeometry(crossShape(.38, .12), { depth: .1, bevelEnabled: true, bevelThickness: .03, bevelSize: .03, bevelSegments: 3 }), M.gold);
  sign.position.set(0, 2.75, 0); g.add(sign); g.userData.sign = sign;
  return g;
}

// object wrappers: root (screen position) > spin > obj
function holder(obj, x, y, scale, ped = 0) {
  const root = new THREE.Group(), spin = new THREE.Group(); root.add(spin); spin.add(obj); scene.add(root);
  root.position.copy(px(x, y)); root.userData = { base: px(x, y), scale };
  if (ped) { const p = pedestal(ped); p.position.y = -1.45; root.add(p); root.userData.ped = p; }
  root.visible = false; return { root, spin, obj };
}
const shield = holder(makeShield(), 235, 985, .58, 1.1);
const card = holder(makeCard(), 815, 990, .5);
const gift = holder(makeGift(), 845, 1005, .5, 1.15);
const syringe = holder(makeSyringe(), 850, 960, .5);
const heart = holder(makeHeart(), 850, 960, .5, 1.0);
const hosp = holder(makeHospital(), 860, 1030, .4, 1.6);
const ctaShield = holder(makeShield(), 885, 1030, .42);
const coverShield = holder(makeShield(), 850, 860, .6, 1.1);
gift.root.userData.ped.position.y = -.05; hosp.root.userData.ped.position.y = -.05;
heart.root.userData.ped.position.y = -1.45;

// floating coins (caruman + ganjaran burst)
const coins = []; for (let i = 0; i < 9; i++) { const c = makeCoin(); scene.add(c); c.visible = false;
  coins.push({ m: c, x: 760 + rnd() * 200, y: 1000 + rnd() * 70, ph: rnd() * 6.28, sp: .5 + rnd(), z: rnd() * 2 - 1, s: .55 + rnd() * .5 }); }
const stack = new THREE.Group(); scene.add(stack); stack.position.copy(px(870, 1035));
const stackCoins = []; for (let i = 0; i < 7; i++) { const c = makeCoin(); c.position.y = i * .11; c.rotation.y = i * .7; stack.add(c); stackCoins.push(c); }
const burst = []; for (let i = 0; i < 14; i++) { const c = makeCoin(); scene.add(c); c.visible = false;
  const a = rnd() * Math.PI * 2; burst.push({ m: c, vx: Math.cos(a) * (1.5 + rnd() * 2), vy: 3 + rnd() * 3.5, vz: rnd() * 2, rx: rnd() * 8, s: .35 + rnd() * .25 }); }

// gold dust particles
const dustN = 160, dustPos = new Float32Array(dustN * 3), dustSeed = [];
for (let i = 0; i < dustN; i++) dustSeed.push([rnd() * 12 - 6, rnd() * 20 - 10, rnd() * 6 - 4, rnd(), .2 + rnd() * .6]);
const dustGeo = new THREE.BufferGeometry(); dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ map: glowTex, size: .14, transparent: true, opacity: .8, blending: THREE.AdditiveBlending, depthWrite: false, color: 0xffd48a }));
scene.add(dust);

// generic animate-in/out for a holder
function showObj(h, t, a, b, { spinRate = .6, bob = .08, tiltX = 0, fromX = 0, fromY = 0, rotIn = 2.2 } = {}) {
  const kin = P(t, a, a + .8), kout = P(t, b - .45, b);
  if (t < a || t > b) { h.root.visible = false; return 0; }
  h.root.visible = true;
  const s = h.root.userData.scale * outBack(kin, 1.4) * (1 - ease(kout));
  h.root.scale.setScalar(Math.max(1e-4, s));
  const base = h.root.userData.base;
  h.root.position.set(base.x + fromX * (1 - outExpo(kin)) + ease(kout) * fromX * .4, base.y + fromY * (1 - outExpo(kin)) + Math.sin(t * 1.7) * bob, base.z);
  h.spin.rotation.set(tiltX + Math.sin(t * 1.3) * .08, (1 - outExpo(kin)) * rotIn + Math.sin(t * spinRate) * .45, Math.sin(t * .9) * .05);
  if (h.root.userData.ped) { const p = h.root.userData.ped; p.children[0].rotation.z = t * .8; p.children[1].rotation.z = -t * 1.3; }
  return kin * (1 - kout);
}

// ---------- DOM ----------
const frame = $('frame'), bframe = $('bframe'), cam = $('cam'), blurcam = $('blurcam');
const pad = n => String(n).padStart(4, '0');
const fidx = t => clamp(Math.round((t - COVER) * FPS) + 1, 1, 900);
async function setFrame(i) {
  const src = `/build/mc/frames/${pad(i)}.jpg`, bsrc = `/build/mc/blur/${pad(i)}.jpg`;
  if (frame.dataset.i == i) return; frame.dataset.i = i;
  frame.src = src; bframe.src = bsrc; await Promise.all([frame.decode(), bframe.decode()]);
}

// section chip
const SECS = [[O(.2), C.juta + .9, '01', 'PERLINDUNGAN'], [C.caruman - .1, C.cut1, '02', 'CARUMAN'], [C.cut1 + .2, C.cut4, '03', 'GANJARAN'], [C.cut4 + .1, C.berminat, '04', 'MANFAAT'], [C.berminat + .1, DUR + 1, '05', 'DAFTAR']];
$('sec').innerHTML = SECS.map(s => `<div class="c"><div class="d"></div><span class="n">${s[2]}</span>${s[3]}</div>`).join('');
const secEls = [...$('sec').children];

// panels
function panel(el, t, a, b) {
  const kin = P(t, a, a + .7), kout = P(t, b - .35, b);
  if (t < a || t > b) { el.style.opacity = 0; el.style.visibility = 'hidden'; return 0; }
  el.style.visibility = 'visible';
  const ki = outExpo(kin), ko = ease(kout);
  el.style.opacity = Math.min(1, kin * 4) * (1 - ko);
  el.style.transform = `translateY(${(1 - ki) * 60 - ko * 30}px) scale(${1 - (1 - ki) * .04 - ko * .05})`;
  el.style.clipPath = `inset(-20px ${(1 - ki) * 100}% -20px -20px round 30px)`;
  el.style.filter = ko > 0 ? `blur(${ko * 10}px)` : 'none';
  let scan = el.querySelector('.scan'); if (!scan) { scan = document.createElement('div'); scan.className = 'scan';
    el.prepend(scan); for (const c of ['tl', 'tr', 'bl', 'bri']) { const b = document.createElement('div'); b.className = 'br ' + c; el.appendChild(b); } }
  const ks = P(t, a + .2, a + 1.4); scan.style.opacity = ks > 0 && ks < 1 ? Math.sin(ks * Math.PI) : 0;
  scan.style.transform = `translateX(${ks * 900 - 160}px)`;
  return ki * (1 - ko);
}
const pop = (el, t, a, dur = .45) => { const k = P(t, a, a + dur); el.style.opacity = Math.min(1, k * 3);
  el.style.transform = `translateY(${(1 - outExpo(k)) * 26}px) scale(${.85 + .15 * outBack(k, 2)})`; el.style.filter = k < 1 ? `blur(${(1 - k) * 6}px)` : 'none'; return k; };

// captions
const WORDS = await (await fetch('/medical-card/words.json')).json();
const merged = []; for (const w of WORDS) { if (w[2].startsWith(',') && merged.length) { merged[merged.length - 1][1] = w[1]; merged[merged.length - 1][2] += w[2]; } else merged.push([...w]); }
const KEYS = /^(peguam|30|tahun|medical|card|RM3|juta|RM217|sebulan|tanpa|tuntutan|ganjaran|RM2,500|vaksinasi|pemeriksaan|kesihatan|komplikasi|kehamilan|hibah|hilang|upaya|kekal|15|jenis|rawatan|lanjutan|Berminat\?|daftar|sekarang)/i;
const BREAKS = [0, 'memilih', 'sehingga', 'Carumannya', 'Lebih', 'anda', 'ganjaran', 'untuk', 'pemeriksaan', 'Lengkap', 'komplikasi', 'hibah,', 'serta', 'Berminat?', 'Klik'];
const phrases = []; let cur = null;
merged.forEach((w, i) => { if (i === 0 || BREAKS.includes(w[2]) && !(w[2] === 'untuk' && merged[i - 1][2] !== 'tahun')) { cur = []; phrases.push(cur); } cur.push(w); });
const capEl = $('cap');
capEl.innerHTML = phrases.map((p, i) => `<div class="line" data-i="${i}" style="position:absolute;left:0;width:840px;display:none">` +
  p.map(w => `<span class="w${KEYS.test(w[2].replace(/[.,]$/, '')) ? ' key' : ''}">${w[2].replace(/[.,]$/, '')}</span>`).join('') + '</div>').join('');
const lineEls = [...capEl.children];
function captions(t) {
  const r = t - COVER;
  phrases.forEach((p, i) => {
    const el = lineEls[i], s = p[0][0] - .12, next = phrases[i + 1] ? phrases[i + 1][0][0] - .12 : 99, e = Math.min(p[p.length - 1][1] + .5, next);
    if (r < s || r >= e || t < COVER || t >= C.berminat - .05) { el.style.display = 'none'; return; }
    el.style.display = 'flex'; el.style.top = '0px'; el.style.height = '136px'; el.style.alignContent = 'center';
    const ko = P(r, e - .15, e);
    [...el.children].forEach((sp, j) => {
      const w = p[j], k = P(r, w[0] - .1, w[0] + .12);
      const active = r >= w[0] - .05 && r < w[1] + .05;
      sp.style.opacity = Math.min(1, k * 1.5) * (1 - ko);
      sp.style.transform = `translateY(${(1 - outCubic(k)) * 18}px) scale(${active ? 1.07 : 1})`;
      sp.style.filter = k < 1 ? `blur(${(1 - k) * 5}px)` : 'none';
    });
  });
}

// grain
const gctx = $('grain').getContext('2d'), gimg = gctx.createImageData(540, 960);
function grain() { const d = gimg.data; for (let i = 0; i < d.length; i += 4) { const v = rnd() * 255; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; } gctx.putImageData(gimg, 0, 0); }

// ---------- camera moves on the footage ----------
// [start, end, scale from, scale to, vertical shift px]  (scaled about top-centre, then shifted up
// so faces sit above the graphics band: panels start ~1040px, captions 1300-1436px)
const SHOTS = [
  [0, COVER, 1.12, 1.14, -70],
  [COVER, C.juta, 1.05, 1.09, -60],
  [C.juta, C.caruman, 1.14, 1.17, -90],
  [C.caruman, C.rm217, 1.07, 1.09, -60],
  [C.rm217, C.cut1, 1.13, 1.16, -90],
  [C.cut1, C.ganjaran, 1.08, 1.12, -150],
  [C.ganjaran, C.cut2, 1.1, 1.12, -160],
  [C.cut2, C.cut3, 1.07, 1.11, -110],
  [C.cut3, C.cut4, 1.08, 1.12, -140],
  [C.cut4, C.n15, 1.13, 1.15, -240],
  [C.n15, C.berminat, 1.15, 1.17, -260],
  [C.berminat, DUR, 1.13, 1.16, -240],
];
function camAt(t) {
  let i = SHOTS.findIndex(s => t >= s[0] && t < s[1]); if (i < 0) i = SHOTS.length - 1;
  const [a, b, s0, s1, sh0] = SHOTS[i];
  let s = lerp(s0, s1, ease(P(t, a, b))), sh = sh0;
  const hardCut = [C.cut1, C.cut2, C.cut3, C.cut4, COVER].some(c => Math.abs(c - a) < .01);
  if (i > 0 && !hardCut) { const pv = SHOTS[i - 1], k = outExpo(P(t, a, a + .45)); s = lerp(pv[3], s, k); sh = lerp(pv[4], sh, k); }
  let w = 1;
  for (const c of [C.cut1, C.cut2, C.cut3, C.cut4]) { const d = t - c; if (d >= 0 && d < .4) w = 1 + .07 * Math.pow(1 - d / .4, 3); }
  if (t >= COVER && t < COVER + .5) w = 1 + .1 * Math.pow(1 - (t - COVER) / .5, 3);
  const dx = Math.sin(t * .35) * 8, dy = Math.cos(t * .27) * 5, rot = Math.sin(t * .22) * .3;
  return { s, w, sh, dx, dy, rot };
}

// ---------- main ----------
window.renderAt = async (t) => {
  await setFrame(t < COVER ? fidx(COVER + 1.25) : fidx(t));
  const c = camAt(t);
  const tf = `translate(${c.dx}px,${c.sh + c.dy}px) translate(540px,600px) scale(${c.w}) rotate(${c.rot}deg) translate(-540px,-600px) translate(540px,0) scale(${c.s}) translate(-540px,0)`;
  cam.style.transform = tf; blurcam.style.transform = tf;

  // cover
  const cov = $('cover'), ko = P(t, .78, 1.02);
  cov.style.display = t < 1.05 ? 'block' : 'none';
  cov.style.opacity = 1 - ease(ko);
  cov.querySelector('.txt').style.transform = `translateY(${-ease(ko) * 40}px) scale(${1 + Math.sin(t * 3) * .006 + ko * .08})`;
  cov.querySelector('.l3').style.filter = `drop-shadow(0 0 ${30 + 20 * Math.sin(t * 6)}px rgba(255,200,100,.5))`;

  // section chip
  secEls.forEach((el, i) => { const [a, b] = SECS[i]; const k = outExpo(P(t, a, a + .5)), o = ease(P(t, b - .25, b));
    el.style.opacity = t >= a && t <= b ? Math.min(1, k * 2) * (1 - o) : 0; el.style.transform = `translateY(${(1 - k) * -16 + o * -10}px)`; });

  // panels
  panel($('pProfile'), t, C.peguam, C.juta - .05);
  const kl = panel($('pLimit'), t, C.juta - .1, C.caruman);
  $('limitNum').textContent = fmt(3e6 * outCubic(P(t, C.juta, C.juta + 1.1)));
  panel($('pCaruman'), t, C.caruman - .05, C.cut1 + .05);
  $('carNum').textContent = fmt(217 * outCubic(P(t, C.rm217 - .1, C.rm217 + .7)));
  const eq = $('pCaruman').querySelector('.eq'); pop(eq, t, C.rm217 + .9, .5);
  panel($('pReward'), t, C.tanpa - .1, C.cut4 + .05);
  $('rwKick').textContent = t < C.ganjaran - .1 ? 'LEBIH MENARIK' : 'TANPA TUNTUTAN · GANJARAN';
  $('rwNum').textContent = t < C.ganjaran ? 'TANPA TUNTUTAN' : fmt(2500 * outCubic(P(t, C.ganjaran + .3, C.ganjaran + 1.2)));
  $('rwPer').style.display = t < C.ganjaran ? 'none' : 'block';
  $('rwNum').style.fontSize = t < C.ganjaran ? '58px' : '92px';
  const ck = $('sealck'), kc = P(t, C.tanpa + .3, C.tanpa + .8); ck.style.strokeDasharray = 60; ck.style.strokeDashoffset = 60 * (1 - kc);
  pop($('c1'), t, C.vaks); pop($('c2'), t, C.periksa); pop($('c3'), t, C.banyak);
  panel($('pBenefit'), t, C.lengkap - .05, C.berminat + .1);
  pop($('b1'), t, C.kehamilan - .2); pop($('b2'), t, C.hibah); pop($('b3'), t, C.hilang); pop($('b4'), t, C.n15);
  $('n15').textContent = Math.round(15 * outCubic(P(t, C.n15, C.n15 + .7)));
  for (const id of ['b1', 'b2', 'b3', 'b4']) { const el = $(id); el.style.boxShadow = ''; }
  const activeTile = t >= C.n15 ? 'b4' : t >= C.hilang ? 'b3' : t >= C.hibah ? 'b2' : t >= C.kehamilan - .2 ? 'b1' : null;
  if (activeTile) $(activeTile).style.boxShadow = '0 0 0 2px rgba(255,214,140,.9), 0 0 40px rgba(255,190,80,.35)';
  panel($('pCta'), t, C.berminat, DUR + 1);
  const kb = P(t, C.klik, C.klik + .5); $('ctaBtn').style.transform = `scale(${(.8 + .2 * outBack(kb, 2)) * (1 + Math.sin(t * 6) * .015 * kb)})`; $('ctaBtn').style.opacity = kb;
  $('ctaSh').style.left = `${((t - C.klik) % 1.6) / 1.6 * 900 - 200}px`;
  $('ctaArr').style.transform = `translateY(${Math.abs(Math.sin(t * 5)) * 8}px)`;

  captions(t);

  // ---------- 3D ----------
  showObj(coverShield, t, -1, 1.0, { rotIn: 0 });
  if (t < 1) coverShield.root.scale.setScalar(.95 * (1 - ease(P(t, .78, 1))));
  showObj(card, t, C.card, C.juta + 1.6, { fromX: 4, rotIn: 3.5, spinRate: .8, bob: .06 });
  if (t < C.caruman + .5) showObj(shield, t, C.juta, C.caruman + .3, { fromY: -1.5, rotIn: 3.14 });
  else showObj(shield, t, C.kehamilan - .2, C.berminat + .1, { fromY: -1.5, rotIn: 3.14 });
  // coins: caruman
  const coinOn = t > C.caruman && t < C.cut1 + .1;
  stack.visible = coinOn;
  stackCoins.forEach((c, i) => { const k = P(t, C.rm217 - .2 + i * .09, C.rm217 + .25 + i * .09); c.position.y = i * .11 + (1 - outCubic(k)) * 5; c.visible = k > 0; c.rotation.y = i * .7 + t * .3; });
  stack.scale.setScalar(.6 * (1 - ease(P(t, C.cut1 - .3, C.cut1 + .1)))); stack.rotation.x = .35;
  coins.forEach((c, i) => {
    const k = outBack(P(t, C.caruman + i * .07, C.caruman + .6 + i * .07)), o = ease(P(t, C.cut1 - .35, C.cut1 + .05));
    c.m.visible = coinOn && k > 0; if (!c.m.visible) return;
    const p = px(c.x - 470 * (i % 2), c.y - 120 + Math.sin(t * c.sp + c.ph) * 18, c.z); c.m.position.copy(p);
    c.m.scale.setScalar(c.s * .6 * k * (1 - o) + 1e-4); c.m.rotation.set(1.2 + Math.sin(t * c.sp) * .5, t * c.sp + c.ph, .3);
  });
  // ganjaran: gift + burst
  showObj(gift, t, C.menarik + .4, C.cut2 + .1, { rotIn: 2.5, spinRate: .5, tiltX: .3 });
  const lid = gift.obj.userData.lid, kOpen = outBack(P(t, C.ganjaran + .1, C.ganjaran + .6));
  lid.position.y = 1.2 + kOpen * .7; lid.rotation.z = kOpen * .35; lid.rotation.x = kOpen * -.2;
  burst.forEach(b => { const d = t - C.ganjaran - .2; b.m.visible = d > 0 && t < C.cut2 + .1; if (!b.m.visible) return;
    const g0 = gift.root.position; b.m.position.set(g0.x + b.vx * d * .3, g0.y + .6 + b.vy * d * .5 - 2.2 * d * d, g0.z + b.vz * d);
    b.m.rotation.set(b.rx * d, b.rx * d * .7, 0); b.m.scale.setScalar(.6 * b.s * (1 - ease(P(t, C.cut2 - .3, C.cut2 + .1))) + 1e-4); });
  showObj(syringe, t, C.vaks - .2, C.cut3 + .1, { tiltX: 0, rotIn: 2, fromX: -3 });
  syringe.spin.rotation.z = -.7;
  showObj(heart, t, C.periksa - .15, C.cut4 + .1, { rotIn: 3.14, spinRate: .9 });
  heart.obj.scale.setScalar(1 + Math.max(0, Math.sin(t * 7.5)) ** 8 * .08);
  showObj(hosp, t, C.n15 - .1, C.berminat + .1, { rotIn: 1.6, spinRate: .4, tiltX: .18 });
  hosp.obj.userData.sign.rotation.y = t * 1.5;
  showObj(ctaShield, t, C.berminat + .1, DUR + 2, { fromY: -1, rotIn: 6.28, spinRate: .7 });

  // dust
  for (let i = 0; i < dustN; i++) { const [x, y, z, ph, sp] = dustSeed[i];
    dustPos[i * 3] = x + Math.sin(t * sp + ph * 6) * .4; dustPos[i * 3 + 1] = ((y + t * sp * .5 + 10) % 20) - 10; dustPos[i * 3 + 2] = z; }
  dustGeo.attributes.position.needsUpdate = true;
  dust.material.opacity = .55 + .25 * Math.sin(t * 2);
  renderer.render(scene, camera);

  // ---------- transitions: light leak + streak ----------
  let leak = 0, st = 0, sy = 960;
  for (const c of [COVER, C.cut1, C.cut2, C.cut3, C.cut4]) { const d = t - c; leak = Math.max(leak, Math.exp(-Math.pow(d / .14, 2)) * .85); }
  for (const c of [C.juta, C.ganjaran, C.n15, C.klik]) { const d = t - c; leak = Math.max(leak, Math.exp(-Math.pow(d / .2, 2)) * .35); }
  for (const [c, y] of [[COVER, 1180], [C.cut1, 820], [C.cut2, 1100], [C.cut3, 700], [C.cut4, 980], [C.juta, 1200], [C.ganjaran, 1100]]) {
    const d = t - c; const k = Math.exp(-Math.pow(d / .12, 2)); if (k > st) { st = k; sy = y; } }
  $('leak').style.opacity = leak;
  const sk = $('streak'); sk.style.opacity = st; sk.style.top = sy + 'px'; sk.style.transform = `scaleY(${1 + st * 3})`;
  grain();
};

await renderAt(0);
window.ready = true;
