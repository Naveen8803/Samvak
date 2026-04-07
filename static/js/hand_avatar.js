/**
 * hand_avatar.js  –  Samvak 3D Hands Avatar v7 (Three.js)
 * ========================================================
 * High-quality 3D hand avatar with detailed geometry, distinct
 * gesture poses, and smooth motion-blended animations.
 *
 *   const ha = new HandAvatar('avatar-container');
 *   ha.play(sign_tokens);
 *   ha.setSpeed(1.4);
 *   ha.replay();
 */
(function (root) {
  "use strict";

  /* ── Helpers ─────────────────────────────────────────────── */
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  /* ── Finger bend presets (curl angles in radians per joint) ─
   *  Each hand: [THUMB, INDEX, MIDDLE, RING, PINKY]
   *  Each finger: [MCP, PIP, DIP] — 0=straight, ~1.57=fully curled
   *  Plus per-finger splay angle [SPLAY] applied at MCP root       */
  const POSE = {
    rest: {
      curls: [
        [0.18, 0.12, 0.06],
        [0.25, 0.18, 0.12],
        [0.30, 0.22, 0.14],
        [0.35, 0.25, 0.16],
        [0.40, 0.28, 0.18],
      ],
      splays: [0.05, 0.04, 0, -0.04, -0.08],
      wrist: [0, 0, 0],
    },
    open: {
      curls: [
        [0.06, 0.03, 0.01],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
      ],
      splays: [0.35, 0.14, 0.04, -0.08, -0.18],
      wrist: [0.1, 0, 0],
    },
    fist: {
      curls: [
        [0.85, 0.75, 0.55],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
      ],
      splays: [0, 0, 0, 0, 0],
      wrist: [0, 0, 0],
    },
    point: {
      curls: [
        [0.85, 0.65, 0.45],
        [0.0, 0.0, 0.0],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
      ],
      splays: [0, 0, 0, 0, 0],
      wrist: [0, 0, 0],
    },
    thumbU: {
      curls: [
        [0.0, 0.0, 0.0],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
      ],
      splays: [0.3, 0, 0, 0, 0],
      wrist: [0, 0, 0],
    },
    vSign: {
      curls: [
        [0.85, 0.65, 0.45],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
      ],
      splays: [0, 0.18, -0.18, 0, 0],
      wrist: [0, 0, 0],
    },
    ily: {
      curls: [
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [1.55, 1.5, 1.25],
        [1.55, 1.5, 1.25],
        [0.0, 0.0, 0.0],
      ],
      splays: [0.42, 0.16, 0, 0, -0.22],
      wrist: [0, 0, 0],
    },
    flat: {
      curls: [
        [0.35, 0.12, 0.06],
        [0.02, 0.0, 0.0],
        [0.02, 0.0, 0.0],
        [0.02, 0.0, 0.0],
        [0.02, 0.0, 0.0],
      ],
      splays: [0.2, 0.06, 0, -0.06, -0.12],
      wrist: [-0.25, 0, 0],
    },
    pinch: {
      curls: [
        [0.55, 0.45, 0.35],
        [0.65, 0.55, 0.45],
        [0.22, 0.16, 0.10],
        [0.28, 0.20, 0.13],
        [0.32, 0.22, 0.15],
      ],
      splays: [-0.1, -0.08, 0, 0.04, 0.08],
      wrist: [0, 0, 0],
    },
    cup: {
      curls: [
        [0.38, 0.22, 0.16],
        [0.58, 0.48, 0.38],
        [0.62, 0.52, 0.42],
        [0.58, 0.48, 0.38],
        [0.52, 0.42, 0.32],
      ],
      splays: [0.1, 0.04, 0, -0.04, -0.1],
      wrist: [0.15, 0, 0],
    },
    clawOpen: {
      curls: [
        [0.4, 0.3, 0.2],
        [0.55, 0.4, 0.2],
        [0.55, 0.4, 0.2],
        [0.55, 0.4, 0.2],
        [0.55, 0.4, 0.2],
      ],
      splays: [0.35, 0.16, 0.04, -0.12, -0.24],
      wrist: [0.1, 0, 0],
    },
    hookFist: {
      curls: [
        [0.7, 0.55, 0.4],
        [0.1, 1.3, 1.2],
        [0.1, 1.3, 1.2],
        [0.1, 1.3, 1.2],
        [0.1, 1.3, 1.2],
      ],
      splays: [0, 0, 0, 0, 0],
      wrist: [0, 0, 0],
    },
    fingerTip: {
      curls: [
        [0.45, 0.35, 0.25],
        [0.4, 0.3, 0.25],
        [0.4, 0.3, 0.25],
        [0.4, 0.3, 0.25],
        [0.4, 0.3, 0.25],
      ],
      splays: [-0.12, -0.06, 0, 0.06, 0.12],
      wrist: [0.08, 0, 0],
    },
  };

  /* ── Gesture definitions mapping backend gestures → hand poses + motions ── */
  const GESTURE_DEFS = {
    idle:            { R: 'rest',     L: 'rest',     motion: 'none',    dur: 200 },
    // Greetings
    wave:            { R: 'open',     L: 'rest',     motion: 'wave',    dur: 500, repeat: 3 },
    thank_you:       { R: 'flat',     L: 'rest',     motion: 'nod',     dur: 450 },
    welcome:         { R: 'open',     L: 'open',     motion: 'sweep',   dur: 500 },
    congratulations: { R: 'clawOpen', L: 'clawOpen',  motion: 'clap',   dur: 400, repeat: 3 },
    // Yes/No/Positive
    positive:        { R: 'thumbU',   L: 'rest',     motion: 'pump',    dur: 400 },
    yes:             { R: 'fist',     L: 'rest',     motion: 'nod',     dur: 350, repeat: 2 },
    no:              { R: 'point',    L: 'rest',     motion: 'shake',   dur: 350, repeat: 2 },
    // Questions
    question:        { R: 'clawOpen', L: 'clawOpen', motion: 'shrug',   dur: 500 },
    // Pronouns
    point_you:       { R: 'point',    L: 'rest',     motion: 'forward', dur: 350 },
    point_self:      { R: 'point',    L: 'rest',     motion: 'inward',  dur: 350 },
    // Actions
    help:            { R: 'flat',     L: 'fist',     motion: 'lift',    dur: 450 },
    need:            { R: 'hookFist', L: 'rest',     motion: 'beckon',  dur: 400 },
    please:          { R: 'flat',     L: 'rest',     motion: 'circle',  dur: 450 },
    sorry:           { R: 'fist',     L: 'rest',     motion: 'circle',  dur: 450 },
    love:            { R: 'ily',      L: 'ily',      motion: 'spread',  dur: 550 },
    name:            { R: 'flat',     L: 'flat',     motion: 'tap',     dur: 400 },
    drink:           { R: 'cup',      L: 'rest',     motion: 'tilt',    dur: 400 },
    eat:             { R: 'fingerTip',L: 'rest',     motion: 'eat',     dur: 400 },
    directional:     { R: 'point',    L: 'rest',     motion: 'sweep',   dur: 400 },
    stop:            { R: 'open',     L: 'rest',     motion: 'push',    dur: 350 },
    repeat:          { R: 'hookFist', L: 'flat',     motion: 'tap',     dur: 400 },
    take_care:       { R: 'flat',     L: 'flat',     motion: 'cradle',  dur: 500 },
    turn_on:         { R: 'pinch',    L: 'rest',     motion: 'flick',   dur: 350 },
    light:           { R: 'fingerTip',L: 'rest',     motion: 'bloom',   dur: 400 },
    fingerspell:     { R: 'flat',     L: 'rest',     motion: 'none',    dur: 200 },
  };

  /* ── Motion functions ────────────────────────────────────── */
  const MF = {
    none:  () => ({ rx:0, ry:0, rz:0, rax:0, ray:0, raz:0, lx:0, ly:0, lz:0, lax:0, lay:0, laz:0 }),
    wave: (t) => ({
      rx: Math.sin(t*Math.PI*4)*0.45, ry: 0.35+Math.sin(t*Math.PI*2)*0.15,
      rz: 0, rax: 0, ray: 0, raz: Math.sin(t*Math.PI*4)*0.35,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    nod: (t) => ({
      rx: 0, ry: Math.sin(t*Math.PI)*0.55, rz: -Math.sin(t*Math.PI)*0.15,
      rax: Math.sin(t*Math.PI)*0.2, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    sweep: (t) => ({
      rx: Math.sin(t*Math.PI)*0.65-0.3, ry: Math.sin(t*Math.PI)*0.25,
      rz: 0, rax: 0, ray: Math.sin(t*Math.PI)*0.25, raz: 0,
      lx: -Math.sin(t*Math.PI)*0.65+0.3, ly: Math.sin(t*Math.PI)*0.25,
      lz: 0, lax: 0, lay: -Math.sin(t*Math.PI)*0.25, laz: 0,
    }),
    pump: (t) => ({
      rx: 0, ry: Math.abs(Math.sin(t*Math.PI*2))*0.55, rz: 0,
      rax: 0, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    shrug: (t) => {
      const s = Math.sin(t*Math.PI);
      return {
        rx: 0.25, ry: s*0.35, rz: 0, rax: s*0.15, ray: 0, raz: s*0.12,
        lx: -0.25, ly: s*0.35, lz: 0, lax: s*0.15, lay: 0, laz: -s*0.12,
      };
    },
    forward: (t) => ({
      rx: 0, ry: Math.sin(t*Math.PI)*0.18, rz: -Math.sin(t*Math.PI)*0.55,
      rax: -0.1, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    inward: (t) => ({
      rx: 0, ry: Math.sin(t*Math.PI)*0.18, rz: Math.sin(t*Math.PI)*0.4,
      rax: Math.sin(t*Math.PI)*0.22, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    lift: (t) => {
      const s = Math.sin(t*Math.PI);
      return {
        rx: 0.18, ry: s*0.6, rz: 0, rax: s*0.12, ray: 0, raz: 0,
        lx: -0.18, ly: s*0.45, lz: 0, lax: s*0.12, lay: 0, laz: 0,
      };
    },
    beckon: (t) => ({
      rx: Math.sin(t*Math.PI*3)*0.2, ry: Math.sin(t*Math.PI)*0.35,
      rz: 0, rax: Math.sin(t*Math.PI*3)*0.25, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    circle: (t) => ({
      rx: Math.cos(t*Math.PI*2)*0.3, ry: Math.sin(t*Math.PI*2)*0.3+0.18,
      rz: 0, rax: Math.sin(t*Math.PI*2)*0.18, ray: Math.cos(t*Math.PI*2)*0.1, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    spread: (t) => {
      const s = Math.sin(t*Math.PI);
      return {
        rx: s*0.4, ry: s*0.25, rz: 0, rax: 0, ray: s*0.15, raz: 0,
        lx: -s*0.4, ly: s*0.25, lz: 0, lax: 0, lay: -s*0.15, laz: 0,
      };
    },
    shake: (t) => ({
      rx: Math.sin(t*Math.PI*4)*0.35, ry: 0.1, rz: 0,
      rax: 0, ray: Math.sin(t*Math.PI*4)*0.2, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    tap: (t) => {
      const s = Math.sin(t*Math.PI*2);
      return {
        rx: 0.12, ry: Math.abs(s)*0.35, rz: 0, rax: 0.08, ray: 0, raz: 0,
        lx: -0.12, ly: Math.abs(s)*0.35, lz: 0, lax: 0.08, lay: 0, laz: 0,
      };
    },
    tilt: (t) => ({
      rx: 0, ry: Math.sin(t*Math.PI*0.5)*0.22, rz: 0,
      rax: 0, ray: 0, raz: Math.sin(t*Math.PI)*0.5,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    eat: (t) => ({
      rx: 0, ry: Math.sin(t*Math.PI)*0.38+Math.sin(t*Math.PI*3)*0.14,
      rz: -0.12, rax: Math.sin(t*Math.PI*3)*0.12, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    push: (t) => ({
      rx: 0, ry: 0.1, rz: -Math.sin(t*Math.PI)*0.55,
      rax: -Math.sin(t*Math.PI)*0.15, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    cradle: (t) => {
      const s = Math.sin(t*Math.PI);
      return {
        rx: 0.22+s*0.14, ry: s*0.2, rz: 0, rax: s*0.15, ray: 0, raz: s*0.1,
        lx: -0.22-s*0.14, ly: s*0.2, lz: 0, lax: s*0.15, lay: 0, laz: -s*0.1,
      };
    },
    flick: (t) => ({
      rx: Math.sin(t*Math.PI*2)*0.25, ry: Math.abs(Math.sin(t*Math.PI*2))*0.35,
      rz: 0, rax: Math.sin(t*Math.PI*2)*0.3, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    bloom: (t) => ({
      rx: 0, ry: t*0.5, rz: 0, rax: t*0.3, ray: 0, raz: 0,
      lx: 0, ly: 0, lz: 0, lax: 0, lay: 0, laz: 0,
    }),
    clap: (t) => {
      const s = Math.sin(t*Math.PI*2);
      const d = Math.abs(s)*0.5;
      return {
        rx: d, ry: 0.18, rz: 0, rax: -s*0.12, ray: 0, raz: -s*0.08,
        lx: -d, ly: 0.18, lz: 0, lax: -s*0.12, lay: 0, laz: s*0.08,
      };
    },
  };

  /* ── 3D Hand Builder ──────────────────────────────────────── */
  class Hand3D {
    constructor(THREE, isLeft = false) {
      this.THREE = THREE;
      this.isLeft = isLeft;
      this.group = new THREE.Group();

      // Current & target poses
      this._curCurls = POSE.rest.curls.map(f => [...f]);
      this._tgtCurls = POSE.rest.curls.map(f => [...f]);
      this._curSplays = [...POSE.rest.splays];
      this._tgtSplays = [...POSE.rest.splays];
      this._curWrist = [...POSE.rest.wrist];
      this._tgtWrist = [...POSE.rest.wrist];

      // Materials
      this._skinMat = new THREE.MeshPhongMaterial({
        color: 0xd4a574,
        specular: 0x553322,
        shininess: 25,
        flatShading: false,
      });
      this._skinDark = new THREE.MeshPhongMaterial({
        color: 0xc89860,
        specular: 0x443322,
        shininess: 20,
      });
      this._nailMat = new THREE.MeshPhongMaterial({
        color: 0xf2cec0,
        specular: 0xffffff,
        shininess: 80,
      });

      this._fingers = [];
      this._palmGroup = new THREE.Group();
      this.group.add(this._palmGroup);
      this._buildHand();

      if (isLeft) {
        this.group.scale.x = -1;
      }
    }

    _buildHand() {
      const T = this.THREE;

      // ── Palm (wider for finger spacing) ──
      const palmW = 0.56, palmH = 0.52, palmD = 0.13;
      const palmGeo = new T.BoxGeometry(palmW, palmH, palmD, 6, 6, 3);
      this._roundBoxVertices(palmGeo, palmW, palmH, palmD, 0.06);
      palmGeo.computeVertexNormals();
      const palmMesh = new T.Mesh(palmGeo, this._skinMat);
      palmMesh.castShadow = true;
      palmMesh.receiveShadow = true;
      this._palmGroup.add(palmMesh);

      // ── Palm detail: slight bump on palm-center (thenar eminence) ──
      const thenarGeo = new T.SphereGeometry(0.13, 10, 8);
      thenarGeo.scale(1, 0.7, 0.5);
      const thenarMesh = new T.Mesh(thenarGeo, this._skinMat);
      thenarMesh.position.set(-0.12, -0.08, 0.04);
      thenarMesh.castShadow = true;
      this._palmGroup.add(thenarMesh);

      // Hypothenar bump (opposite side)
      const hypoGeo = new T.SphereGeometry(0.10, 8, 6);
      hypoGeo.scale(1, 0.65, 0.45);
      const hypoMesh = new T.Mesh(hypoGeo, this._skinMat);
      hypoMesh.position.set(0.12, -0.06, 0.04);
      hypoMesh.castShadow = true;
      this._palmGroup.add(hypoMesh);

      // ── Wrist (tapered cylinder) ──
      const wristGeo = new T.CylinderGeometry(0.21, 0.24, 0.18, 14, 1);
      const wristMesh = new T.Mesh(wristGeo, this._skinMat);
      wristMesh.position.set(0, -0.35, 0);
      wristMesh.castShadow = true;
      this._palmGroup.add(wristMesh);

      // Forearm stub
      const forearmGeo = new T.CylinderGeometry(0.22, 0.25, 0.35, 12, 1);
      const forearmMesh = new T.Mesh(forearmGeo, this._skinMat);
      forearmMesh.position.set(0, -0.6, 0);
      forearmMesh.castShadow = true;
      this._palmGroup.add(forearmMesh);

      // ── Knuckle ridge across top of palm ──
      for (let i = 0; i < 4; i++) {
        const kGeo = new T.SphereGeometry(0.038, 8, 6);
        const kMesh = new T.Mesh(kGeo, this._skinDark);
        kMesh.position.set(-0.16 + i * 0.105, 0.24, 0.03);
        kMesh.scale.set(1.1, 0.75, 0.85);
        kMesh.castShadow = true;
        this._palmGroup.add(kMesh);
      }

      // ── Build fingers ──
      // Thumb (special positioning — offset further out)
      const thumbCfg = {
        lengths: [0.13, 0.11, 0.09],
        radii:   [0.048, 0.043, 0.037],
      };
      const thumbRoot = new T.Group();
      thumbRoot.position.set(-0.26, -0.02, 0.06);
      thumbRoot.rotation.z = 0.65;
      thumbRoot.rotation.y = -0.4;
      this._palmGroup.add(thumbRoot);
      this._fingers.push(this._buildFinger(thumbRoot, thumbCfg));

      // Four main fingers — wider spacing (0.105 apart instead of 0.08)
      const fingerCfgs = [
        { lengths: [0.15, 0.13, 0.09], radii: [0.038, 0.034, 0.029], x: -0.16, y: 0.26 },
        { lengths: [0.165, 0.14, 0.10], radii: [0.040, 0.036, 0.031], x: -0.055, y: 0.27 },
        { lengths: [0.155, 0.13, 0.09], radii: [0.038, 0.034, 0.029], x: 0.05, y: 0.265 },
        { lengths: [0.13, 0.11, 0.08],  radii: [0.035, 0.031, 0.026], x: 0.155, y: 0.24 },
      ];

      fingerCfgs.forEach((cfg, i) => {
        const root = new T.Group();
        root.position.set(cfg.x, cfg.y, 0);
        this._palmGroup.add(root);
        this._fingers.push(this._buildFinger(root, cfg));
      });
    }

    _roundBoxVertices(geo, w, h, d, radius) {
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        // Distance from edges normalized 0–1
        const dx = Math.abs(x) / (w / 2);
        const dy = Math.abs(y) / (h / 2);
        const dz = Math.abs(z) / (d / 2);
        // Round corners
        const corner = Math.max(0, Math.max(dx, dy) - 0.7);
        const factor = 1 - corner * radius * 3;
        pos.setXYZ(i,
          x * Math.max(factor, 0.8),
          y,
          z * Math.max(factor, 0.85)
        );
      }
      geo.computeVertexNormals();
    }

    _buildFinger(rootGroup, cfg) {
      const T = this.THREE;
      const joints = [];

      let parent = rootGroup;
      for (let seg = 0; seg < 3; seg++) {
        const len = cfg.lengths[seg];
        const r1 = cfg.radii[seg];
        const r2 = seg < 2 ? cfg.radii[seg + 1] : r1 * 0.82;

        // Joint pivot
        const joint = new T.Group();
        if (seg > 0) {
          joint.position.set(0, cfg.lengths[seg - 1], 0);
        }
        parent.add(joint);

        // Segment mesh (capsule-like: tapered cylinder with hemisphere caps)
        const segGeo = new T.CylinderGeometry(r2, r1, len, 10, 1);
        const segMesh = new T.Mesh(segGeo, this._skinMat);
        segMesh.position.set(0, len / 2, 0);
        segMesh.castShadow = true;
        joint.add(segMesh);

        // Spherical cap at base of segment for smooth joint look
        const capGeo = new T.SphereGeometry(r1 * 0.95, 8, 6);
        const capMesh = new T.Mesh(capGeo, this._skinMat);
        capMesh.position.set(0, 0, 0);
        capMesh.castShadow = true;
        joint.add(capMesh);

        // Joint sphere between segments (darker for visual distinction)
        if (seg < 2) {
          const jGeo = new T.SphereGeometry(r1 * 0.88, 8, 6);
          const jMesh = new T.Mesh(jGeo, this._skinDark);
          jMesh.position.set(0, len, 0);
          jMesh.castShadow = true;
          joint.add(jMesh);
        }

        // Nail on last segment (rounded shape)
        if (seg === 2) {
          const nailW = r1 * 1.5, nailH = len * 0.48, nailD = r1 * 0.22;
          const nailGeo = new T.BoxGeometry(nailW, nailH, nailD, 3, 3, 1);
          this._roundBoxVertices(nailGeo, nailW, nailH, nailD, 0.1);
          const nailMesh = new T.Mesh(nailGeo, this._nailMat);
          nailMesh.position.set(0, len * 0.78, -r1 * 0.58);
          joint.add(nailMesh);

          // Fingertip cap
          const tipGeo = new T.SphereGeometry(r2 * 0.95, 8, 6);
          const tipMesh = new T.Mesh(tipGeo, this._skinMat);
          tipMesh.position.set(0, len, 0);
          tipMesh.castShadow = true;
          joint.add(tipMesh);
        }

        joints.push(joint);
        parent = joint;
      }

      return { root: rootGroup, joints };
    }

    setPose(poseName, instant = false) {
      const pose = POSE[poseName] || POSE.rest;
      this._tgtCurls = pose.curls.map(f => [...f]);
      this._tgtSplays = [...pose.splays];
      this._tgtWrist = [...pose.wrist];
      if (instant) {
        this._curCurls = this._tgtCurls.map(f => [...f]);
        this._curSplays = [...this._tgtSplays];
        this._curWrist = [...this._tgtWrist];
        this._applyPose();
      }
    }

    update(dt) {
      const speed = Math.min(dt * 10, 1);
      let changed = false;

      // Lerp curls
      for (let f = 0; f < 5; f++) {
        for (let j = 0; j < 3; j++) {
          const cur = this._curCurls[f][j];
          const tgt = this._tgtCurls[f][j];
          if (Math.abs(cur - tgt) > 0.002) {
            this._curCurls[f][j] = lerp(cur, tgt, speed);
            changed = true;
          }
        }
        // Lerp splays
        if (Math.abs(this._curSplays[f] - this._tgtSplays[f]) > 0.002) {
          this._curSplays[f] = lerp(this._curSplays[f], this._tgtSplays[f], speed);
          changed = true;
        }
      }

      // Lerp wrist
      for (let i = 0; i < 3; i++) {
        if (Math.abs(this._curWrist[i] - this._tgtWrist[i]) > 0.002) {
          this._curWrist[i] = lerp(this._curWrist[i], this._tgtWrist[i], speed);
          changed = true;
        }
      }

      if (changed) this._applyPose();
    }

    _applyPose() {
      // Apply wrist rotation to palm group
      this._palmGroup.rotation.set(
        this._curWrist[0],
        this._curWrist[1],
        this._curWrist[2],
      );

      for (let f = 0; f < this._fingers.length; f++) {
        const finger = this._fingers[f];
        const curls = this._curCurls[f];
        const splay = this._curSplays[f];

        // Apply splay to root
        if (f === 0) {
          // Thumb already has base rotation
          finger.root.rotation.z = 0.65 + splay;
        } else {
          finger.root.rotation.z = (-1.5 + (f - 1)) * 0.06 + splay;
        }

        // Apply curls
        for (let j = 0; j < finger.joints.length; j++) {
          finger.joints[j].rotation.x = -curls[j];
        }
      }
    }

    dispose() {
      this._skinMat.dispose();
      this._skinDark.dispose();
      this._nailMat.dispose();
    }
  }

  /* ── HandAvatar (main class) ─────────────────────────────── */
  class HandAvatar {
    constructor(elOrId, opts = {}) {
      const container = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
      if (!container) throw new Error('HandAvatar: container not found');

      // If it's a canvas, replace it with a div
      let el = container;
      if (container.tagName === 'CANVAS') {
        el = document.createElement('div');
        el.id = container.id;
        el.style.cssText = container.style.cssText;
        el.style.width = '100%';
        el.style.height = container.style.height || '340px';
        container.parentNode.replaceChild(el, container);
      }

      this._el = el;
      this._speed = 1.0;
      this._dead = false;
      this._word = '';
      this._chips = [];
      this._runId = 0;
      this._last = [];

      if (typeof THREE === 'undefined') {
        console.error('HandAvatar: THREE.js not loaded');
        return;
      }

      this._initScene();
      this._initHands();
      this._animate();

      this._resizeObs = new ResizeObserver(() => this._onResize());
      this._resizeObs.observe(el);
    }

    /* ── Scene setup ────────────────────────────────────────── */
    _initScene() {
      const T = THREE;
      const w = this._el.clientWidth || 560;
      const h = this._el.clientHeight || 340;

      // Renderer
      this._renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
      this._renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this._renderer.setSize(w, h);
      this._renderer.shadowMap.enabled = true;
      this._renderer.shadowMap.type = T.PCFSoftShadowMap;
      this._renderer.toneMapping = T.ACESFilmicToneMapping;
      this._renderer.toneMappingExposure = 1.15;
      this._renderer.setClearColor(0x0a0f1e, 1);
      this._el.appendChild(this._renderer.domElement);
      this._renderer.domElement.style.cssText = 'display:block;width:100%;height:100%;border-radius:inherit;';

      // Camera
      this._camera = new T.PerspectiveCamera(30, w / h, 0.1, 50);
      this._camera.position.set(0, 0.25, 3.5);
      this._camera.lookAt(0, 0.05, 0);

      // Scene
      this._scene = new T.Scene();
      this._scene.fog = new T.Fog(0x0a0f1e, 4.5, 9);

      // Lighting ──
      // Ambient (subtle warm fill)
      this._scene.add(new T.AmbientLight(0x778899, 0.45));

      // Key light (warm directional)
      const keyLight = new T.DirectionalLight(0xffeedd, 1.3);
      keyLight.position.set(2.5, 4, 2.5);
      keyLight.castShadow = true;
      keyLight.shadow.mapSize.set(1024, 1024);
      keyLight.shadow.camera.near = 0.5;
      keyLight.shadow.camera.far = 12;
      keyLight.shadow.camera.left = -2;
      keyLight.shadow.camera.right = 2;
      keyLight.shadow.camera.top = 2;
      keyLight.shadow.camera.bottom = -2;
      keyLight.shadow.radius = 4;
      this._scene.add(keyLight);

      // Fill light (cool blue)
      const fillLight = new T.DirectionalLight(0x8899cc, 0.55);
      fillLight.position.set(-2.5, 2, 1);
      this._scene.add(fillLight);

      // Under light (soft bottom, to reduce harsh shadows)
      const underLight = new T.DirectionalLight(0x998877, 0.25);
      underLight.position.set(0, -2, 1);
      this._scene.add(underLight);

      // Rim/accent light (indigo from behind)
      const rimLight = new T.PointLight(0x6366f1, 0.65, 8);
      rimLight.position.set(0, 0.5, -2.5);
      this._scene.add(rimLight);

      // Subtle spot from top for specular highlight
      const topSpot = new T.SpotLight(0xffffff, 0.35, 10, Math.PI / 6, 0.8, 1);
      topSpot.position.set(0, 5, 0);
      this._scene.add(topSpot);

      // Ground plane
      const groundGeo = new T.PlaneGeometry(8, 8);
      const groundMat = new T.MeshPhongMaterial({
        color: 0x0a0f1e,
        specular: 0x111422,
        shininess: 5,
      });
      const ground = new T.Mesh(groundGeo, groundMat);
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = -1.2;
      ground.receiveShadow = true;
      this._scene.add(ground);

      // 2D overlays
      this._el.style.position = 'relative';

      this._labelCanvas = document.createElement('canvas');
      this._labelCanvas.style.cssText = 'position:absolute;bottom:8px;left:50%;transform:translateX(-50%);pointer-events:none;z-index:5;';
      this._labelCanvas.width = 420;
      this._labelCanvas.height = 50;
      this._el.appendChild(this._labelCanvas);
      this._labelCtx = this._labelCanvas.getContext('2d');

      this._wordCanvas = document.createElement('canvas');
      this._wordCanvas.style.cssText = 'position:absolute;top:8px;left:50%;transform:translateX(-50%);pointer-events:none;z-index:5;';
      this._wordCanvas.width = 320;
      this._wordCanvas.height = 42;
      this._el.appendChild(this._wordCanvas);
      this._wordCtx = this._wordCanvas.getContext('2d');
    }

    _initHands() {
      // Right hand
      this._rightHand = new Hand3D(THREE, false);
      this._rightHand.group.position.set(0.58, 0, 0);
      this._rightHand.group.rotation.set(-0.25, 0, 0.08);
      this._scene.add(this._rightHand.group);

      // Left hand
      this._leftHand = new Hand3D(THREE, true);
      this._leftHand.group.position.set(-0.58, 0, 0);
      this._leftHand.group.rotation.set(-0.25, 0, -0.08);
      this._scene.add(this._leftHand.group);

      this._rBase = { x: 0.58, y: 0, z: 0 };
      this._lBase = { x: -0.58, y: 0, z: 0 };
      this._rOff = { x:0, y:0, z:0, ax:0, ay:0, az:0 };
      this._lOff = { x:0, y:0, z:0, ax:0, ay:0, az:0 };
      this._idleTime = 0;
    }

    /* ── Public API ────────────────────────────────────────── */
    setTheme() { /* dark only for 3D */ }
    setSpeed(v) { this._speed = clamp(Number(v) || 1, 0.3, 3.0); }
    idle() { this._runId++; this._word = ''; this._chips = []; }
    replay() { if (this._last.length) this.play(this._last); }
    destroy() {
      this._dead = true;
      this._runId++;
      if (this._resizeObs) this._resizeObs.disconnect();
      if (this._renderer) this._renderer.dispose();
    }

    async play(tokens) {
      if (!Array.isArray(tokens) || !tokens.length) return;
      const rid = ++this._runId;
      this._last = tokens;
      this._chips = tokens.map(t => String(t.word || '').toUpperCase()).filter(Boolean);

      // Reset to idle
      await this._animateGesture('idle', 180 / this._speed, rid);
      if (this._runId !== rid) return;

      for (const tok of tokens) {
        if (this._runId !== rid) return;
        this._word = String(tok.word || '').trim();
        this._drawWord(this._word);

        const g = String(tok.gesture || 'fingerspell').toLowerCase();

        if (g === 'fingerspell') {
          const chars = Array.isArray(tok.chars) ? tok.chars :
            this._word.toUpperCase().replace(/[^A-Z0-9]/g, '').split('');
          await this._spellChars(chars, rid);
        } else {
          await this._animateGesture(g, null, rid);
        }

        if (this._runId !== rid) return;
        await this._wait(80 / this._speed);
      }

      if (this._runId !== rid) return;
      this._word = '';
      this._drawWord('');
      this._drawChips();
      await this._animateGesture('idle', 250 / this._speed, rid);
    }

    /* ── Animation engine ────────────────────────────────────── */
    async _animateGesture(name, durOverride, rid) {
      const def = GESTURE_DEFS[name] || GESTURE_DEFS.idle;
      const motionFn = MF[def.motion] || MF.none;
      const dur = (durOverride || def.dur) / this._speed;
      const repeats = def.repeat || 1;
      const totalDur = dur * repeats;

      // Set hand poses
      this._rightHand.setPose(def.R);
      this._leftHand.setPose(def.L);

      const t0 = performance.now();
      return new Promise(resolve => {
        const step = () => {
          if (this._dead || this._runId !== rid) { resolve(); return; }
          const elapsed = performance.now() - t0;
          const cycleT = (elapsed % dur) / dur;
          const m = motionFn(cycleT);

          const fadeIn = ease(clamp(elapsed / 160, 0, 1));
          const fadeOut = elapsed > totalDur - 160 ? ease(clamp((totalDur - elapsed) / 160, 0, 1)) : 1;
          const env = fadeIn * fadeOut;

          this._rOff = {
            x: m.rx * env, y: m.ry * env, z: m.rz * env,
            ax: (m.rax||0) * env, ay: (m.ray||0) * env, az: (m.raz||0) * env,
          };
          this._lOff = {
            x: m.lx * env, y: m.ly * env, z: m.lz * env,
            ax: (m.lax||0) * env, ay: (m.lay||0) * env, az: (m.laz||0) * env,
          };

          if (elapsed < totalDur) {
            requestAnimationFrame(step);
          } else {
            this._rOff = { x:0, y:0, z:0, ax:0, ay:0, az:0 };
            this._lOff = { x:0, y:0, z:0, ax:0, ay:0, az:0 };
            resolve();
          }
        };
        requestAnimationFrame(step);
      });
    }

    async _spellChars(chars, rid) {
      // Alternate between slightly different poses for each letter
      const spellPoses = ['flat', 'point', 'open', 'vSign'];
      for (let i = 0; i < chars.length && i < 16; i++) {
        if (this._runId !== rid) return;
        const poseName = spellPoses[i % spellPoses.length];
        this._rightHand.setPose(poseName);
        this._drawWord(this._word + ' [' + chars[i] + ']');

        const dur = 220 / this._speed;
        const t0 = performance.now();
        await new Promise(resolve => {
          const step = () => {
            if (this._dead || this._runId !== rid) { resolve(); return; }
            const t = clamp((performance.now() - t0) / dur, 0, 1);
            this._rOff = {
              x: Math.sin(t * Math.PI) * 0.08,
              y: Math.sin(t * Math.PI) * 0.22,
              z: 0,
              ax: Math.sin(t * Math.PI * 2) * 0.1,
              ay: 0, az: 0,
            };
            if (t < 1) requestAnimationFrame(step); else resolve();
          };
          requestAnimationFrame(step);
        });

        if (this._runId !== rid) return;
        await this._wait(70 / this._speed);
      }
    }

    _wait(ms) { return new Promise(r => setTimeout(r, Math.max(ms, 8))); }

    /* ── Render loop ─────────────────────────────────────────── */
    _animate() {
      let lastTime = performance.now();
      const loop = () => {
        if (this._dead) return;
        requestAnimationFrame(loop);

        const now = performance.now();
        const dt = (now - lastTime) / 1000;
        lastTime = now;

        // Idle breathing
        this._idleTime += dt;
        const breath = Math.sin(this._idleTime * 1.5) * 0.018;
        const sway = Math.sin(this._idleTime * 0.8) * 0.006;

        // Update hand positions with offsets
        const rg = this._rightHand.group;
        rg.position.set(
          this._rBase.x + this._rOff.x,
          this._rBase.y + this._rOff.y + breath,
          this._rBase.z + this._rOff.z,
        );
        rg.rotation.set(
          -0.25 + this._rOff.ax,
          this._rOff.ay + sway,
          0.08 + this._rOff.az,
        );

        const lg = this._leftHand.group;
        lg.position.set(
          this._lBase.x + this._lOff.x,
          this._lBase.y + this._lOff.y + breath,
          this._lBase.z + this._lOff.z,
        );
        lg.rotation.set(
          -0.25 + this._lOff.ax,
          this._lOff.ay - sway,
          -0.08 + this._lOff.az,
        );

        // Update finger interpolation
        this._rightHand.update(dt);
        this._leftHand.update(dt);

        this._renderer.render(this._scene, this._camera);
      };
      requestAnimationFrame(loop);
    }

    _onResize() {
      const w = this._el.clientWidth;
      const h = this._el.clientHeight;
      if (w < 1 || h < 1) return;
      this._camera.aspect = w / h;
      this._camera.updateProjectionMatrix();
      this._renderer.setSize(w, h);
    }

    /* ── 2D label overlays ─────────────────────────────────── */
    _drawWord(text) {
      const ctx = this._wordCtx;
      const c = this._wordCanvas;
      ctx.clearRect(0, 0, c.width, c.height);
      if (!text) return;

      ctx.font = "600 15px 'Inter', system-ui, sans-serif";
      const tw = ctx.measureText(text).width;
      const px = 14, bh = 28;
      const bw = tw + px * 2;
      const bx = (c.width - bw) / 2, by = 7;

      ctx.fillStyle = 'rgba(8,14,32,0.9)';
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 14);
      ctx.fill();

      ctx.strokeStyle = 'rgba(129,140,248,0.4)';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = '#e2e8f0';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, c.width / 2, by + bh / 2);
      ctx.textAlign = 'start';
    }

    _drawChips() {
      const ctx = this._labelCtx;
      const c = this._labelCanvas;
      ctx.clearRect(0, 0, c.width, c.height);
      if (!this._chips.length) return;

      ctx.font = "600 11px 'Inter', system-ui, sans-serif";
      const px = 8, gap = 5;
      const tot = this._chips.reduce((s, ch) => s + ctx.measureText(ch).width + px * 2 + gap, -gap);
      let x = (c.width - tot) / 2;

      for (const ch of this._chips) {
        const tw = ctx.measureText(ch).width + px * 2;
        const bh = 22;
        const by = (c.height - bh) / 2;

        ctx.fillStyle = 'rgba(99,102,241,0.16)';
        ctx.beginPath();
        ctx.roundRect(x, by, tw, bh, 11);
        ctx.fill();

        ctx.strokeStyle = 'rgba(99,102,241,0.3)';
        ctx.lineWidth = 0.5;
        ctx.stroke();

        ctx.fillStyle = '#818cf8';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(ch, x + tw / 2, by + bh / 2);
        ctx.textAlign = 'start';

        x += tw + gap;
      }
    }
  }

  root.HandAvatar = HandAvatar;
})(typeof window !== 'undefined' ? window : global);
