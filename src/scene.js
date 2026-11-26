import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

// ---------- helpers ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, b) => clamp((t - a) / (b - a));
const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const outExpo = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
const outBack = (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
const outBounce = x => { const n = 7.5625, d = 2.75;
  if (x < 1 / d) return n * x * x; if (x < 2 / d) return n * (x -= 1.5 / d) * x + .75;
  if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + .9375; return n * (x -= 2.625 / d) * x + .984375; };
const lerp = (a, b, k) => a + (b - a) * k;
// in/out window: 0 before a, ramps to 1 over dIn, holds, ramps out over dOut ending at b
const win = (t, a, b, dIn = .45, dOut = .35, fin = outExpo) => Math.min(fin(P(t, a, a + dIn)), 1 - ease(P(t, b - dOut, b)));
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

const W = 1280, H = 868, STAGE_X = 880, STAGE_Y = 385, CAM_K = .63;
const TL = await (await fetch('/build/timeline.json')).json();
const guides = new URLSearchParams(location.search).has('guides');


// ---------- key times (output seconds) ----------
const T = {
  family: .9, ibu: 1.55, ayah: 2.0, ketua: 3.15, tray: 3.55,
  house: 4.72, rumah: 5.45, houseToStone: 5.85, money: 6.0, kereta: 7.2,
  hosp: 999, hospOut: 999, risk: 7.95, berlaku: 12.6, fall: 12.95, menimpa: 14.2, isteri: 15.7, rewind: 18.75,
  tembok: 23.0, kanan: 24.2, kiri: 24.8, perlindungan: 25.6, toDome: 26.9, semua: 28.55, beban: 29.63,
  keluarga: 32.5, outro: 34.1, end: 36.6,
};

// ---------- renderer ----------
const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(30, W / H, .1, 100);
camera.setViewOffset(W, H, (W / 2 - STAGE_X), (H / 2 - STAGE_Y), W, H);

scene.add(new THREE.HemisphereLight(0xdfeaff, 0x0a1f55, 1.1));
const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(3, 5, 6); scene.add(key);
const rimL = new THREE.PointLight(0x4f9dff, 30, 12); rimL.position.set(-3, 1.5, -1.5); scene.add(rimL);
const rimR = new THREE.PointLight(0x8fd8ff, 24, 12); rimR.position.set(3, -0.5, -1.5); scene.add(rimR);

// ---------- materials ----------
const M = {
  white: new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: .05, roughness: .28, clearcoat: 1, clearcoatRoughness: .15 }),
  silver: new THREE.MeshPhysicalMaterial({ color: 0xdfe6f0, metalness: .95, roughness: .2, clearcoat: 1 }),
  steel: new THREE.MeshPhysicalMaterial({ color: 0x8fa3c4, metalness: .9, roughness: .3 }),
  blue: new THREE.MeshPhysicalMaterial({ color: 0x2b6cff, metalness: .4, roughness: .25, clearcoat: 1, emissive: 0x0b2a80, emissiveIntensity: .6 }),
  glow: new THREE.MeshBasicMaterial({ color: 0x7fd0ff }),
  glowBlue: new THREE.MeshBasicMaterial({ color: 0x3f8cff }),
  glass: new THREE.MeshPhysicalMaterial({ color: 0xcfe2ff, metalness: 0, roughness: .06, transparent: true, opacity: .22, clearcoat: 1, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 2 }),
  glassStrong: new THREE.MeshPhysicalMaterial({ color: 0xbcd6ff, metalness: .1, roughness: .05, transparent: true, opacity: .38, clearcoat: 1, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 2.2 }),
  stone: new THREE.MeshPhysicalMaterial({ color: 0x9aa7bd, metalness: .55, roughness: .42, flatShading: true, clearcoat: .4 }),
  window: new THREE.MeshBasicMaterial({ color: 0x8fd3ff }),
};
const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const r = g.createRadialGradient(128, 128, 0, 128, 128, 128); r.addColorStop(0, 'rgba(200,235,255,1)'); r.addColorStop(.25, 'rgba(110,180,255,.55)'); r.addColorStop(1, 'rgba(40,100,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 256, 256); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const glowSprite = (s, op = .8) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false }));
  m.scale.set(s, s, 1); return m; };
const ring = (r, tube = .012, mat = M.glow) => { const m = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 12, 128), mat); m.rotation.x = Math.PI / 2; return m; };

const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };

// ---------- STACK: platform + family + tray (the "stone concept") ----------
const stack = new THREE.Group(); scene.add(stack);
const platform = new THREE.Group(); stack.add(platform);
platform.add(at(new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.04, .07, 96), M.glassStrong), 0, -.035, 0));
const pRing = ring(1.02, .014); pRing.position.y = 0; platform.add(pRing);
const pRing2 = ring(.75, .006, M.glowBlue); pRing2.position.y = .002; platform.add(pRing2);
const pGlow = glowSprite(2.6, .35); pGlow.position.set(0, -.05, 0); platform.add(pGlow);

function person(s, mat) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(.12 * s, .3 * s, 8, 24), mat); body.position.y = .27 * s; g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.105 * s, 32, 20), M.white); head.position.y = .67 * s; g.add(head);
  const arms = [];
  for (const side of [-1, 1]) {
    const pivot = new THREE.Group(); pivot.position.set(side * .12 * s, .45 * s, 0);
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(.032 * s, .24 * s, 6, 12), mat); arm.position.y = -.15 * s; pivot.add(arm);
    pivot.rotation.z = side * .25; g.add(pivot); arms.push(pivot);
  }
  const halo = glowSprite(.9 * s, 0); halo.position.y = .45 * s; g.add(halo);
  g.userData = { arms, halo, body, s };
  return g;
}
const dad = person(1, M.silver), mum = person(.94, M.blue), kid1 = person(.62, M.silver), kid2 = person(.55, M.blue);
dad.position.set(-.55, 0, 0); mum.position.set(.55, 0, 0); kid1.position.set(-.16, 0, .25); kid2.position.set(.2, 0, .3);
const family = [dad, mum, kid1, kid2]; family.forEach(f => stack.add(f));

const tray = new THREE.Group(); stack.add(tray);
tray.add(new THREE.Mesh(new THREE.BoxGeometry(2.0, .05, .62), M.glassStrong));
const trayEdge = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2.0, .05, .62)), new THREE.LineBasicMaterial({ color: 0x8fd8ff }));
tray.add(trayEdge);
const bowlPts = [[.42, 0], [.56, .03], [.7, .12], [.8, .3], [.82, .33]].map(([x, y]) => new THREE.Vector2(x, y));
const bowl = new THREE.Mesh(new THREE.LatheGeometry(bowlPts, 96), M.glass); bowl.scale.z = .42; bowl.position.y = .025; tray.add(bowl);
const bowlRim = ring(.82, .01); bowlRim.position.y = .355; bowlRim.scale.y = .42; tray.add(bowlRim);
const trayGlow = glowSprite(2.2, .25); trayGlow.position.y = .15; tray.add(trayGlow);
const TRAY_Y = .99;

// stones
const STONES = [
  { label: 'Rumah', t: T.houseToStone, p: [-.42, .13, .02] },
  { label: 'Pinjaman', t: 6.35, p: [.05, .12, .05] },
  { label: 'Pendidikan', t: 6.8, p: [.48, .13, 0] },
  { label: 'Kereta', t: T.kereta, p: [-.18, .27, -.04] },
  { label: 'Dapur', t: 7.55, p: [.28, .28, .02] },
  { label: '', t: 7.7, p: [-.6, .27, -.03] },
  { label: '', t: 7.82, p: [.62, .3, -.02] },
  { label: '', t: 7.92, p: [.02, .4, 0] },
];
const stoneGeo = () => { const g = new THREE.IcosahedronGeometry(.15, 1); const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const k = .82 + rnd() * .3; p.setXYZ(i, p.getX(i) * k, p.getY(i) * k * .8, p.getZ(i) * k); }
  g.computeVertexNormals(); return g; };
STONES.forEach(s => { s.mesh = new THREE.Mesh(stoneGeo(), M.stone); s.mesh.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3); tray.add(s.mesh); s.spin = rnd() * 2 - 1; });
// extra stones that fall on the takaful dome during "semua beban komitmen"
const DOME_C = new THREE.Vector3(0, .5, 0), DOME_S = new THREE.Vector3(1.12, 1.0, .75);
const EXTRA = [-.62, -.22, .2, .6].map((x, i) => {
  const y = DOME_C.y + DOME_S.y * Math.sqrt(1 - (x / DOME_S.x) ** 2) + .1;
  const m = new THREE.Mesh(stoneGeo(), M.stone); m.scale.setScalar(1.15); stack.add(m);
  return { mesh: m, x, y, t: 29.0 + i * .3 };
});

// walls (tembok) + dome
const walls = [-1, 1].map(side => {
  const g = new THREE.Group(); g.position.x = side * .98; stack.add(g);
  const geo = new THREE.BoxGeometry(.13, .97, .62); geo.translate(0, .485, 0);
  g.add(new THREE.Mesh(geo, M.glassStrong));
  g.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0x9fe0ff })));
  for (let i = 1; i < 6; i++) { const l = new THREE.Mesh(new THREE.BoxGeometry(.135, .006, .625), M.glow); l.position.y = i * .16; g.add(l); }
  const gl = glowSprite(1.3, .45); gl.position.y = .5; g.add(gl);
  return g;
});
const dome = new THREE.Group(); dome.position.copy(DOME_C); dome.scale.copy(DOME_S); stack.add(dome);
const domeGeo = new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2);
const domeMat = new THREE.MeshPhysicalMaterial({ color: 0x9cc8ff, roughness: .1, transparent: true, opacity: .12, side: THREE.DoubleSide, depthWrite: false, clearcoat: 1 });
dome.add(new THREE.Mesh(domeGeo, domeMat));
const hexMat = new THREE.MeshBasicMaterial({ color: 0x7fd0ff, wireframe: true, transparent: true, opacity: .35 });
const hexGeo = new THREE.IcosahedronGeometry(1.005, 3);
{ // keep upper hemisphere only
  const p = hexGeo.attributes.position; for (let i = 0; i < p.count; i++) if (p.getY(i) < -0.02) p.setY(i, -0.02);
}
dome.add(new THREE.Mesh(hexGeo, hexMat));

// waves (ombak) under the platform
const waveGeo = new THREE.PlaneGeometry(2.5, .045, 160, 1);
const wave = new THREE.Mesh(waveGeo, new THREE.MeshBasicMaterial({ color: 0x7fd0ff, side: THREE.DoubleSide, transparent: true }));
wave.position.set(0, -.16, .55); stack.add(wave);
const wave2 = new THREE.Mesh(waveGeo.clone(), new THREE.MeshBasicMaterial({ color: 0x3f8cff, side: THREE.DoubleSide, transparent: true, opacity: .7 }));
wave2.position.set(0, -.24, .35); stack.add(wave2);
const wBase = waveGeo.attributes.position.array.slice();
function setWave(mesh, t, amp, ph) {
  const p = mesh.geometry.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = wBase[i * 3], y = wBase[i * 3 + 1];
    const edge = Math.pow(Math.abs(x) / 1.25, 1.5);
    p.setY(i, y + amp * (.35 + edge) * Math.sin(x * 5 - t * 5 + ph) + amp * .4 * Math.sin(x * 11 + t * 3 + ph)); }
  p.needsUpdate = true;
}

// ---------- HOUSE ----------
const house = new THREE.Group(); scene.add(house);
{
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.0, .66, .8), M.white); body.position.y = .33; house.add(body);
  const rs = new THREE.Shape(); rs.moveTo(-.64, 0); rs.lineTo(0, .5); rs.lineTo(.64, 0); rs.lineTo(-.64, 0);
  const rg = new THREE.ExtrudeGeometry(rs, { depth: .92, bevelEnabled: true, bevelSize: .02, bevelThickness: .02, bevelSegments: 2 }); rg.translate(0, 0, -.46);
  const roof = new THREE.Mesh(rg, M.blue); roof.position.y = .66; house.add(roof);
  const ch = new THREE.Mesh(new THREE.BoxGeometry(.12, .26, .12), M.silver); ch.position.set(.3, .98, -.1); house.add(ch);
  const door = new THREE.Mesh(new THREE.BoxGeometry(.2, .36, .02), M.glowBlue); door.position.set(0, .18, .405); house.add(door);
  for (const x of [-.3, .3]) { const w = new THREE.Mesh(new THREE.BoxGeometry(.18, .16, .02), M.window); w.position.set(x, .42, .405); house.add(w); }
  const r = ring(.85, .012); house.add(r); house.add(at(glowSprite(2.4, .4), 0, .3, -.3));
}

// ---------- HOSPITAL ----------
const hosp = new THREE.Group(); scene.add(hosp);
{
  const main = new THREE.Mesh(new THREE.BoxGeometry(.95, 1.25, .75), M.white); main.position.y = .625; hosp.add(main);
  for (const s of [-1, 1]) {
    const wing = new THREE.Mesh(new THREE.BoxGeometry(.5, .75, .65), M.white); wing.position.set(s * .72, .375, -.02); hosp.add(wing);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 2; c++) {
      const w = new THREE.Mesh(new THREE.BoxGeometry(.12, .1, .02), M.window); w.position.set(s * .72 + (c - .5) * .2, .17 + r * .19, .31); hosp.add(w); }
  }
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const w = new THREE.Mesh(new THREE.BoxGeometry(.16, .11, .02), M.window); w.position.set((c - 1) * .26, .42 + r * .19, .38); hosp.add(w); }
  const door = new THREE.Mesh(new THREE.BoxGeometry(.32, .26, .02), M.glowBlue); door.position.set(0, .13, .38); hosp.add(door);
  const canopy = new THREE.Mesh(new THREE.BoxGeometry(.5, .04, .22), M.silver); canopy.position.set(0, .29, .46); hosp.add(canopy);
  const cross = new THREE.Group(); cross.position.set(0, 1.08, .39);
  cross.add(new THREE.Mesh(new THREE.BoxGeometry(.26, .08, .04), M.glow)); cross.add(new THREE.Mesh(new THREE.BoxGeometry(.08, .26, .04), M.glow));
  hosp.add(cross); const cg = glowSprite(.9, .8); cg.position.set(0, 1.08, .45); hosp.add(cg);
  hosp.add(ring(1.1, .012)); hosp.add(ring(1.25, .005, M.glowBlue));
  hosp.add(at(glowSprite(3, .35), 0, .5, -.5));
  hosp.userData.cross = cross;
}

// ---------- SHIELD emblem ----------
function shieldShape(k = 1) {
  const s = new THREE.Shape();
  s.moveTo(0, 1 * k); s.bezierCurveTo(.3 * k, .86 * k, .62 * k, .86 * k, .86 * k, .8 * k); s.lineTo(.86 * k, .12 * k);
  s.bezierCurveTo(.86 * k, -.5 * k, .4 * k, -.86 * k, 0, -1.06 * k); s.bezierCurveTo(-.4 * k, -.86 * k, -.86 * k, -.5 * k, -.86 * k, .12 * k);
  s.lineTo(-.86 * k, .8 * k); s.bezierCurveTo(-.62 * k, .86 * k, -.3 * k, .86 * k, 0, 1 * k); return s;
}
const shield = new THREE.Group(); scene.add(shield);
{
  const g1 = new THREE.ExtrudeGeometry(shieldShape(1), { depth: .16, bevelEnabled: true, bevelSize: .05, bevelThickness: .05, bevelSegments: 4, curveSegments: 48 });
  g1.translate(0, 0, -.08); shield.add(new THREE.Mesh(g1, M.silver));
  const g2 = new THREE.ExtrudeGeometry(shieldShape(.78), { depth: .1, bevelEnabled: true, bevelSize: .03, bevelThickness: .03, bevelSegments: 3, curveSegments: 48 });
  g2.translate(0, 0, .04); shield.add(new THREE.Mesh(g2, M.blue));
  const ck = new THREE.Shape(); ck.moveTo(-.36, .02); ck.lineTo(-.12, -.24); ck.lineTo(.38, .3); ck.lineTo(.28, .4); ck.lineTo(-.12, -.04); ck.lineTo(-.26, .12); ck.lineTo(-.36, .02);
  const g3 = new THREE.ExtrudeGeometry(ck, { depth: .06, bevelEnabled: true, bevelSize: .015, bevelThickness: .015 }); g3.translate(0, -.05, .16);
  shield.add(new THREE.Mesh(g3, new THREE.MeshBasicMaterial({ color: 0xeaf6ff })));
  const sg = glowSprite(3.4, .6); sg.position.z = -.3; shield.add(sg); shield.userData.glow = sg;
}

// ---------- COINS (money flow) ----------
const coinGeo = new THREE.CylinderGeometry(.075, .075, .018, 36);
const coinMat = [M.silver, new THREE.MeshPhysicalMaterial({ color: 0x5aa0ff, metalness: .9, roughness: .2 }), M.silver];
const COINS = Array.from({ length: 16 }, (_, i) => {
  const m = new THREE.Mesh(coinGeo, coinMat); m.rotation.x = Math.PI / 2; stack.add(m);
  return { mesh: m, t: 6.05 + i * .11, x0: (rnd() - .5) * .9, x1: (rnd() - .5) * 1.2, z: (rnd() - .5) * .3, s: rnd() };
});

// ---------- intro orbit ----------
const intro = new THREE.Group(); scene.add(intro);
const INTRO = Array.from({ length: 9 }, (_, i) => { const m = new THREE.Mesh(stoneGeo(), i % 3 ? M.stone : M.silver); intro.add(m); return { m, a: i / 9 * Math.PI * 2, r: .75 + (i % 3) * .12 }; });
const introRing = ring(.9, .01); introRing.rotation.x = 1.25; intro.add(introRing);
const introRing2 = ring(1.05, .005, M.glowBlue); introRing2.rotation.x = 1.25; intro.add(introRing2);
intro.add(glowSprite(2.2, .5));

// ---------- background particles ----------
const parts = new THREE.Group(); scene.add(parts);
const PARTS = Array.from({ length: 26 }, () => {
  const m = rnd() < .5 ? new THREE.Mesh(new THREE.OctahedronGeometry(.04 + rnd() * .05, 0), M.silver) : glowSprite(.12 + rnd() * .12, .7);
  const o = { m, x: (rnd() - .5) * 1.5, y: (rnd() - .5) * 2.2, z: -1.5 - rnd() * 2.5, sp: .2 + rnd() * .4, ph: rnd() * 6 };
  parts.add(m); return o;
});

// ---------- DOM ----------
const $ = id => document.getElementById(id);
const ICON = {
  home: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  family: '<circle cx="8" cy="6" r="3"/><circle cx="17" cy="8" r="2.4"/><path d="M2.5 21v-4a5.5 5.5 0 0 1 11 0v4M13.5 21v-3a3.5 3.5 0 0 1 7 0v3"/>',
  hosp: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M12 7v6M9 10h6"/>',
  heart: '<path d="M12 20s-7-4.5-9-9a4.8 4.8 0 0 1 9-3 4.8 4.8 0 0 1 9 3c-2 4.5-9 9-9 9z"/><path d="M3 12h5l2-3 3 6 2-3h6"/>',
  person: '<circle cx="12" cy="6" r="3"/><path d="M12 10v6M8 21l4-5 4 5M7 13h10"/>',
  leaf: '<path d="M12 21V11M12 11c0-4 3-7 8-7 0 5-3 8-8 7zM12 14c0-3-2.5-5.5-7-5.5 0 4 2.5 6.5 7 5.5z"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
  card: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
  coin: '<circle cx="12" cy="12" r="8"/><path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.8 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5M12 6.5V8M12 16v1.5"/>',
};
const svg = k => `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICON[k]}</svg>`;
function mkChip(text, icon, cls = '') { const d = document.createElement('div'); d.className = 'abs chip ' + cls; d.innerHTML = `<div class="ic">${svg(icon)}</div>${text}`; $('chips').appendChild(d); return d; }
// chip: [element, x (left edge) or -right edge, y, tIn, tOut, fromSide]
const L = 60, Y0 = 290, DY = 64;
const CHIPS = [
  [mkChip('Ibu · Ayah', 'family'), L, Y0, T.ibu, T.house - .1, -1],
  [mkChip('Ketua Keluarga', 'person'), L, Y0 + DY, T.ketua, T.house - .1, -1],
  [mkChip('Pembiayaan Rumah', 'home'), L, Y0 + DY * 2 + 10, T.rumah - .15, T.money + .1, -1],
  [mkChip('Hospitalisasi', 'hosp', 'warn'), L, Y0, 8.6, T.fall - .1, -1],
  [mkChip('Penyakit Kritikal', 'heart', 'warn'), L, Y0 + DY, 9.3, T.fall - .1, -1],
  [mkChip('TPD', 'person', 'warn'), L, Y0 + DY * 2, 10.0, T.fall - .1, -1],
  [mkChip('Kematian', 'leaf', 'warn'), L, Y0 + DY * 3, 10.8, T.fall - .1, -1],
  [mkChip('Isteri · Anak-anak', 'family', 'warn'), L, Y0, T.isteri, T.rewind, -1],
  [mkChip('Tembok Kanan', 'shield'), L, Y0, T.kanan, T.perlindungan - .1, -1],
  [mkChip('Tembok Kiri', 'shield'), L, Y0 + DY, T.kiri, T.perlindungan - .1, -1],
  [mkChip('Hibah', 'shield'), L, Y0, 27.6, T.outro, -1],
  [mkChip('Sakit Kritikal', 'heart'), L, Y0 + DY, 28.1, T.outro, -1],
  [mkChip('Medical Card', 'card'), L, Y0 + DY * 2, 28.6, T.outro, -1],
];
const headlines = [
  [0, T.family + 0.05, 'TAKAFUL 101', 'Kenapa takaful penting?'],
  [T.family + .05, T.house, '01 · TANGGUNGJAWAB', 'Ketua keluarga'],
  [T.house, T.risk, '02 · KOMITMEN', 'Beban setiap bulan'],
  [T.risk, T.fall, '03 · UJIAN HIDUP', 'Bila musibah berlaku'],
  [T.fall, T.rewind, '04 · KESANNYA', 'Beban menimpa keluarga'],
  [T.rewind, T.outro, '05 · PERLINDUNGAN', 'Takaful sebagai tembok'],
];
$('headline').innerHTML = headlines.map(h => `<div class="h"><div class="k">${h[2]}</div><span>${h[3]}</span></div>`).join('');
const hEls = [...$('headline').children];

// infographic bar
const SEGS = [['Rumah', '#e8f1ff', 5.95], ['Pinjaman', '#9cc4ff', 6.4], ['Pendidikan', '#5a9bff', 6.85], ['Kereta', '#2f6fe8', 7.25], ['Dapur', '#7fd4ff', 7.6]];
const SEGW = [.27, .18, .2, .19, .16];
$('bar').querySelector('.track').innerHTML = SEGS.map(s => `<div class="seg" style="background:${s[1]}"></div>`).join('');
$('bar').querySelector('.legend').innerHTML = SEGS.map(s => `<span><i style="background:${s[1]}"></i>${s[0]}</span>`).join('');
const segEls = [...$('bar').querySelectorAll('.seg')];


// stone labels
const labelEls = STONES.filter(s => s.label).map(s => { const d = document.createElement('div'); d.className = 'abs tag'; d.textContent = s.label; $('labels').appendChild(d); s.el = d; return d; });

// subtitles
let curCap = -1;
function updateSubs(t) {
  const i = TL.captions.findIndex(c => t >= c.s && t < c.e);
  const box = $('subs');
  if (i !== curCap) {
    curCap = i;
    box.innerHTML = i < 0 ? '' : `<div class="line">${TL.captions[i].words.map(w => `<span class="w${w.key ? ' key' : ''}">${w.w}</span>`).join('')}</div>`;
  }
  if (i < 0) return;
  const c = TL.captions[i]; const line = box.firstChild;
  const pin = outBack(P(t, c.s, c.s + .22)), pout = P(t, c.e - .12, c.e);
  line.style.transform = `translateY(${(1 - pin) * 30 + pout * -10}px) scale(${.92 + .08 * pin})`;
  line.style.opacity = Math.min(P(t, c.s, c.s + .12), 1 - pout);
  [...line.children].forEach((el, k) => { const w = c.words[k];
    const a = P(t, w.s - .06, w.s + .12), active = t >= w.s - .04 && t < w.e + .04;
    el.style.opacity = .3 + .7 * a;
    el.style.transform = `translateY(${a < 1 ? (1 - outBack(a)) * 8 * (a > 0 ? 1 : 0) : 0}px) scale(${active ? 1.05 : 1})`;
    if (!w.key) el.style.color = active ? '#bfe6ff' : '#ffffff';
  });
}

function setEl(el, x, y, s, o, extra = '') { el.style.transform = `translate(${x}px, ${y}px) scale(${s}) ${extra}`; el.style.opacity = o; }

// ---------- camera path ----------
const CAM = [
  [0, [0, .9, 13.5]], [.9, [0, .25, 11]], [3.5, [.9, .55, 11.3]], [4.7, [0, .35, 11.2]], [6.0, [-.7, .7, 11.6]],
  [7.95, [-.4, .55, 11.4]], [12.8, [0, .2, 10.6]], [14.2, [.5, .45, 11.2]], [18.5, [-.4, .3, 10.8]],
  [20.2, [0, .5, 12.4]], [23.0, [.5, .5, 12.5]], [25.5, [0, .55, 12.6]], [28.5, [.8, .55, 12.3]],
  [32, [-.6, .35, 11.8]], [34.1, [0, .3, 12.2]], [36.6, [0, .2, 12.9]],
];
function camAt(t) {
  let i = 0; while (i < CAM.length - 2 && t > CAM[i + 1][0]) i++;
  const [t0, a] = CAM[i], [t1, b] = CAM[i + 1]; const cut = t1 - t0 < .1;
  const k = cut ? (t >= t1 ? 1 : 0) : ease(P(t, t0, t1));
  return a.map((v, j) => lerp(v, b[j], k));
}

// ---------- per-frame ----------
function vis(o, s) { o.visible = s > .001; o.scale.setScalar(Math.max(s, .0001)); }
const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();
function toPx(obj, local = [0, 0, 0]) { tmp.set(...local); obj.localToWorld(tmp); tmp.project(camera);
  return [(tmp.x * .5 + .5) * W, (-tmp.y * .5 + .5) * H]; }

window.renderAt = function (t) {
  // background drift
  $('b1').style.transform = `translate(${Math.sin(t * .4) * 80}px, ${Math.cos(t * .3) * 120}px)`;
  $('b2').style.transform = `translate(${Math.cos(t * .35) * 90}px, ${Math.sin(t * .45) * 100}px)`;
  $('grid').style.backgroundPosition = `0 ${t * 40}px`;

  // camera + shake
  const [cx, cy, cz] = camAt(t);
  const shake = Math.max(win(t, 11.5, 14.2, 1.5, .1) * .025, Math.exp(-Math.max(0, t - T.menimpa) * 4) * (t >= T.menimpa ? .09 : 0), Math.exp(-Math.max(0, t - T.perlindungan) * 8) * (t >= T.perlindungan ? .06 : 0),
                         t > 29 && t < 30.4 ? .02 * Math.abs(Math.sin(t * 40)) : 0);
  camera.position.set((cx + Math.sin(t * 47) * shake) * CAM_K, (cy + Math.cos(t * 53) * shake) * CAM_K, cz * CAM_K);
  camera.lookAt(0, 0, 0);

  // ---- stack visibility: in from family, hidden during hospital, out at outro
  const stackIn = outBack(P(t, T.family - .1, T.family + .55), 1.2);
  const stackOut = 1 - ease(P(t, T.outro, T.outro + .55));
  const ss = stackIn * stackOut;
  vis(stack, ss);
  stack.position.set(0, -.62 + (t > T.outro ? -ease(P(t, T.outro, T.outro + .55)) * .6 : 0), 0);
  stack.rotation.y = Math.sin(t * .5) * .22 + (1 - ss) * 1.2 + (t < 2 ? (1 - outExpo(P(t, T.family, 2))) * -1.4 : 0);

  // family
  family.forEach((f, i) => {
    const d = f.userData; const pop = outBack(P(t, T.family + .1 + i * .12, T.family + .55 + i * .12), 2);
    const breathe = 1 + Math.sin(t * 3 + i) * .015;
    const crush = 1 - (i < 2 ? .22 : .32) * win(t, T.menimpa + .15 + i * .1, T.rewind + 1.0, .35, .8, outBack);
    f.scale.set(pop * (2 - crush) ** .5, pop * breathe * crush, pop);
    f.rotation.z = (1 - crush) * (i % 2 ? .25 : -.25);
    const parentHi = i === 0 ? win(t, T.ibu + .4, T.house, .25, .3) : i === 1 ? win(t, T.ibu, T.house, .25, .3) : 0;
    const famHi = win(t, T.keluarga - .1, T.outro + .3, .4, .4);
    d.halo.material.opacity = Math.max(parentHi * .9, famHi * .9 * (.75 + .25 * Math.sin(t * 6 + i)));
    f.position.y = parentHi * .04 * Math.sin(t * 5);
  });
  // parents' arms: left arm rotates +, right arm rotates - to point up
  for (const f of [dad, mum]) { const up = ease(P(t, T.tray - .1, T.tray + .45)); f.userData.arms[0].rotation.z = lerp(-.25, -2.75, up); f.userData.arms[1].rotation.z = lerp(.25, 2.75, up); }

  // tray
  const trayIn = outBack(P(t, T.tray, T.tray + .5), 1.4);
  vis(tray, trayIn);
  const risk = win(t, T.risk + .3, T.menimpa + .1, 3.5, .2, ease);
  const sag = risk * (.06 + .02 * Math.sin(t * 9));
  const tip = win(t, T.menimpa - .15, T.rewind + 1.2, .45, 1.0, outBack);   // tray tips over and drops
  tray.position.set(0, TRAY_Y + (1 - trayIn) * .9 - sag - .25 * tip, 0);
  tray.rotation.z = risk * .07 * Math.sin(t * 7.3) + risk * .05 + tip * .42;
  tray.rotation.x = risk * .03 * Math.sin(t * 5.1);
  stack.updateMatrixWorld(true);

  // stones
  STONES.forEach((s, i) => {
    const k = P(t, s.t, s.t + .55); const vis0 = t >= s.t;
    s.mesh.visible = vis0;
    const [x, y, z] = s.p; const fall = outBounce(k);
    s.mesh.position.set(x, lerp(y + 1.6, y, fall), z);
    // crash onto the family, then rewind back into the bowl
    const dk = Math.min(P(t, T.menimpa + i * .1, T.menimpa + .7 + i * .1), 1 - ease(P(t, T.rewind + .1 + i * .06, T.rewind + 1.1 + i * .06)));
    if (dk > 0) {
      const tgt = tmp2.set(-.75 + i * .21, .12 + (i % 3) * .13 + (i === 2 || i === 5 ? .35 : 0), .35 - (i % 2) * .5);
      stack.localToWorld(tgt); tray.worldToLocal(tgt);
      const up = t < T.rewind + .1 ? outBounce(dk) : ease(dk);
      s.mesh.position.set(lerp(x, tgt.x, up), lerp(y, tgt.y, up) + Math.sin(dk * Math.PI) * (t < T.rewind ? .15 : .4), lerp(z, tgt.z, up));
    }
    s.mesh.scale.setScalar(i === 0 ? lerp(1.6, 1, outExpo(k)) : 1);
    s.mesh.rotation.y = s.spin * t * .3 + (1 - k) * 4;
    if (s.el) { const [px, py] = toPx(s.mesh, [0, .2, 0]); const o = win(t, s.t + .15, T.risk, .3, .2) * (stack.visible ? 1 : 0);
      s.el.style.opacity = o; s.el.style.transform = `translate(-50%,-50%) translate(${clamp(px, 640, 1220)}px, ${clamp(py - 30 - (i % 2) * 26, 40, 700)}px) scale(${.9 + .1 * outBack(P(t, s.t + .15, s.t + .45))})`; }
  });
  EXTRA.forEach(e => { const k = P(t, e.t, e.t + .5); e.mesh.visible = t >= e.t && stack.visible;
    e.mesh.position.set(e.x, lerp(e.y + 2.2, e.y, outBounce(k)), 0); e.mesh.rotation.set(t * .4 + e.x, e.x * 3, 0); });

  // coins: from family up into the bowl
  COINS.forEach(c => { const k = P(t, c.t, c.t + .55); c.mesh.visible = k > 0 && k < 1;
    const e = ease(k); c.mesh.position.set(lerp(c.x0, c.x1 * .6, e) + Math.sin(k * 3.14) * .25 * (c.s - .5), lerp(.35, TRAY_Y + .35, e) + Math.sin(k * 3.14) * .25, c.z + .3);
    c.mesh.rotation.set(Math.PI / 2 + k * 6, k * 9 * c.s, 0); c.mesh.scale.setScalar(Math.sin(k * Math.PI) * .6 + .5); });

  // waves
  const wAmp = .012 + .05 * win(t, T.risk, T.tembok + .4, 1, .6, ease) + .03 * win(t, T.menimpa, T.rewind, .3, .6);
  setWave(wave, t, wAmp * (t > T.tembok ? lerp(1, .3, P(t, T.tembok, T.tembok + 1)) : 1), 0);
  setWave(wave2, t + .3, wAmp * .8, 1.7);
  wave.material.opacity = wave2.material.opacity = .25 + .75 * win(t, T.family + .5, T.outro, .6, .4);

  // walls + dome
  walls.forEach((w, i) => { const wt = i ? T.kanan : T.kiri; const k = outBack(P(t, wt, wt + .45), 1.6); vis(w, k); w.scale.set(1, Math.max(k, .001), 1); });
  const dk = outExpo(P(t, T.toDome + .2, T.toDome + .85));
  dome.visible = dk > .01; dome.scale.set(DOME_S.x * dk, DOME_S.y * dk, DOME_S.z * dk);
  domeMat.opacity = .1 + .1 * Math.max(0, Math.sin(t * 2)); hexMat.opacity = .22 + .25 * win(t, 29.0, 30.6, .2, .6) + .1 * Math.sin(t * 3);
  dome.rotation.y = t * .15;
  pRing.material.color.setHSL(.58, 1, .72 + .1 * Math.sin(t * 4));

  // house
  const hIn = outBack(P(t, T.house, T.house + .45), 1.5), hOut = P(t, T.houseToStone - .15, T.houseToStone + .15);
  const hs = hIn * (1 - ease(hOut));
  vis(house, hs * .85);
  house.position.set(lerp(0, -.42, ease(hOut)), lerp(-.35, .55, ease(hOut)) + Math.sin(t * 2) * .03, 1.2 * (1 - hOut));
  house.rotation.set(.15, -.6 + (t - T.house) * .9, 0);

  // hospital
  const hpk = Math.min(outBack(P(t, T.hosp, T.hosp + .55), 1.3), 1 - ease(P(t, T.hospOut - .3, T.hospOut)));
  vis(hosp, hpk * .9);
  hosp.position.set(0, -.72, 0); hosp.scale.multiplyScalar(.85); hosp.rotation.set(.08, -.7 + (t - T.hosp) * .35 + (1 - hpk) * 1.5, 0);
  hosp.userData.cross.scale.setScalar(1 + .15 * Math.max(0, Math.sin(t * 7)));

  // shield emblem: hero in front at "perlindungan takaful", then dissolves into the dome; hero again in outro
  const shIn = outBack(P(t, T.perlindungan - .1, T.perlindungan + .55), 1.3);
  const toDome = ease(P(t, T.toDome, T.toDome + .6));
  const outroK = ease(P(t, T.outro, T.outro + .7));
  let shs, sy, sz;
  if (t < T.outro) { shs = shIn * lerp(.55, .2, toDome) * (1 - toDome); sy = lerp(.1, .75, toDome); sz = lerp(1.6, 0, toDome); }
  else { shs = outBack(P(t, T.outro, T.outro + .7), 1.2) * .62; sy = 1.08; sz = .5; }
  vis(shield, shs);
  shield.position.set(0, sy + Math.sin(t * 1.5) * .03, sz);
  shield.rotation.set(0, (t - T.perlindungan) * (t < T.outro ? 1.1 : .6) + (1 - shIn) * 3, 0);
  shield.userData.glow.material.opacity = .45 + .25 * Math.sin(t * 3) + .3 * win(t, T.keluarga - .1, T.end, .4, .2);

  // intro orbit collapses into the family platform
  const ik = 1 - ease(P(t, .75, 1.15));
  vis(intro, outBack(P(t, 0, .5)) * ik);
  intro.position.set(0, -.1, 0); intro.rotation.set(.15, t * .8, 0);
  INTRO.forEach((o, i) => { const a = o.a + t * 1.6; o.m.position.set(Math.cos(a) * o.r, Math.sin(a * 2 + i) * .18, Math.sin(a) * o.r * .55); o.m.rotation.set(t + i, t * 1.3, 0); });

  // particles
  PARTS.forEach(p => { p.m.position.set(p.x + Math.sin(t * p.sp + p.ph) * .15, ((p.y + 1.1 + t * p.sp * .25 + p.ph) % 2.6) - 1.0, p.z);
    if (p.m.isMesh) p.m.rotation.set(t * p.sp, t * p.sp * 1.3, 0); });

  renderer.render(scene, camera);

  // ---------- DOM ----------
  // brand + headlines
  setEl($('brand'), 0, (1 - outExpo(P(t, 0, .5))) * -20, 1, P(t, 0, .4) * (1 - ease(P(t, T.outro, T.outro + .4))));
  headlines.forEach((h, i) => { const k = win(t, h[0], h[1], .45, .3);
    const inK = outExpo(P(t, h[0], h[0] + .45));
    hEls[i].style.opacity = k; hEls[i].style.transform = `translateY(${(1 - inK) * 40}px)`; hEls[i].style.filter = `blur(${(1 - k) * 10}px)`; });

  // chips
  CHIPS.forEach(([el, x, y, a, b, side]) => {
    const k = win(t, a, b, .5, .3, x => outBack(x, 1.8));
    if (k <= 0.001) { el.style.opacity = 0; return; }
    const w = el.offsetWidth, left = x >= 0 ? x : -x - w;
    const float = Math.sin(t * 2 + y) * 6;
    setEl(el, left + (1 - clamp(k)) * side * -40, y + float + (1 - clamp(k)) * (side ? 0 : 30), .6 + .4 * k, clamp(k * 1.4));
  });

  // infographic bar
  const bk = win(t, T.money - .25, T.risk + .05, .45, .3);
  setEl($('bar'), 0, (1 - outExpo(P(t, T.money - .25, T.money + .2))) * 40, 1, bk);
  segEls.forEach((el, i) => el.style.width = (SEGW[i] * 100 * outExpo(P(t, SEGS[i][2], SEGS[i][2] + .4))) + '%');

  // ECG
  const ek = win(t, T.hosp + .5, T.hospOut, .45, .3);
  setEl($('ecg'), 0, (1 - outExpo(P(t, T.hosp + .5, T.hosp + .95))) * 40, 1, ek);
  if (ek > 0) {
    let d = ''; const head = ((t - T.hosp) * 160) % 520;
    for (let x = 0; x <= 400; x += 4) { const ph = ((x - head + 520) % 130);
      let y = 50; if (ph > 40 && ph < 50) y = 50 - (ph - 40) * 6; else if (ph >= 50 && ph < 60) y = -10 + (ph - 50) * 11; else if (ph >= 60 && ph < 66) y = 100 - (ph - 60) * 8;
      y += Math.sin(x * .2 + t) * 1.5; d += (x ? 'L' : 'M') + x + ' ' + y.toFixed(1); }
    $('ecgp').setAttribute('d', d);
  }

  // flash on wall impact
  $('flash').style.opacity = .45 * Math.exp(-Math.max(0, t - T.perlindungan) * 6) * (t >= T.perlindungan ? 1 : 0) + .3 * Math.exp(-Math.max(0, t - T.menimpa) * 7) * (t >= T.menimpa ? 1 : 0) + .35 * Math.exp(-Math.max(0, t - T.outro - .3) * 5) * (t >= T.outro + .3 ? 1 : 0);

  // end card
  const endk = outExpo(P(t, T.outro + .3, T.outro + 1.0));
  setEl($('end'), 0, (1 - endk) * 60 + 40, .94 + .06 * endk, endk * (1 - P(t, T.end - .25, T.end)));
  $('end').style.filter = `blur(${(1 - endk) * 12}px)`;

  updateSubs(t);
};

await document.fonts.ready;
window.renderAt(0);
window.ready = true;
