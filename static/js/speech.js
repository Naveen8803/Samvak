const BASE_POSE = {
    torso: [0, 0, 0],
    head: [0, 0, 0],
    lS: [0.2, 0, 0.45],
    rS: [0.2, 0, -0.45],
    lE: [-0.2, 0, 0],
    rE: [-0.2, 0, 0],
    lW: [0, 0, 0],
    rW: [0, 0, 0],
};

const HAND_PREVIEW_POSE = {
    torso: [0, 0, 0],
    head: [0, 0, 0],
    lS: [-0.18, -0.12, 0.54],
    rS: [-0.18, 0.12, -0.54],
    lE: [-0.82, 0.04, 0.08],
    rE: [-0.82, -0.04, -0.08],
    lW: [0.08, 0.02, 0.04],
    rW: [0.08, -0.02, -0.04],
};

const WORD_GESTURES = {
    hello: "wave",
    hi: "wave",
    hey: "wave",
    hello_hi: "wave",
    "hello hi": "wave",
    thank: "thank_you",
    thanks: "thank_you",
    appreciate: "thank_you",
    grateful: "thank_you",
    yes: "yes",
    no: "no",
    not: "no",
    never: "no",
    you: "point_you",
    your: "point_you",
    i: "point_self",
    me: "point_self",
    my: "point_self",
    what: "question",
    where: "question",
    when: "question",
    why: "question",
    how: "question",
    who: "question",
    help: "help",
    need: "need",
    want: "need",
    please: "please",
    sorry: "sorry",
    love: "love",
    welcome: "thank_you",
    good: "positive",
    fine: "positive",
    name: "name",
    water: "drink",
    drink: "drink",
    food: "eat",
    eat: "eat",
    go: "directional",
    come: "directional",
    stop: "stop",
    again: "repeat",
    repeat: "repeat",
    take_care: "take_care",
    "take care": "take_care",
    turn_on: "turn_on",
    "turn on": "turn_on",
    light: "light",
    congratulations: "congratulations",
};

const SUPPORTED_GESTURES = new Set([
    "wave",
    "thank_you",
    "welcome",
    "positive",
    "question",
    "point_you",
    "point_self",
    "help",
    "need",
    "please",
    "sorry",
    "love",
    "yes",
    "no",
    "name",
    "drink",
    "eat",
    "directional",
    "stop",
    "repeat",
    "take_care",
    "turn_on",
    "light",
    "congratulations",
    "fingerspell",
]);

const AVATAR_STYLES = {
    classic_teal: {
        skin: 0xf6d2b4,
        hoodie: 0x22c1a7,
        hoodieAccent: 0x0f766e,
        hair: 0x111827,
        eyeDark: 0x111827,
        lip: 0xfb7185,
        nose: 0xedb892,
        nail: 0xfce7f3,
        hairStyle: "swoop",
    },
    deep_blue: {
        skin: 0xf2c8a6,
        hoodie: 0x3b82f6,
        hoodieAccent: 0x1d4ed8,
        hair: 0x1f2937,
        eyeDark: 0x0f172a,
        lip: 0xf472b6,
        nose: 0xe8b28e,
        nail: 0xfde2e8,
        hairStyle: "layered",
    },
    coral_pop: {
        skin: 0xf3c39f,
        hoodie: 0xfb7185,
        hoodieAccent: 0xe11d48,
        hair: 0x0b1220,
        eyeDark: 0x111827,
        lip: 0xf43f5e,
        nose: 0xe3aa86,
        nail: 0xfde2e8,
        hairStyle: "bun",
    },
};

function getAvatarStyleConfig() {
    const fallback = AVATAR_STYLES.classic_teal;
    try {
        const key = window.localStorage.getItem("sam_avatar_style");
        return AVATAR_STYLES[key] || fallback;
    } catch (error) {
        return fallback;
    }
}

function clonePose(pose) {
    return {
        torso: pose.torso.slice(),
        head: pose.head.slice(),
        lS: pose.lS.slice(),
        rS: pose.rS.slice(),
        lE: pose.lE.slice(),
        rE: pose.rE.slice(),
        lW: pose.lW.slice(),
        rW: pose.rW.slice(),
    };
}

function mergePose(base, override) {
    const out = clonePose(base);
    if (!override) return out;
    for (const key of Object.keys(out)) {
        if (Array.isArray(override[key]) && override[key].length === 3) {
            out[key] = override[key].slice();
        }
    }
    return out;
}

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function lerpPose(a, b, t) {
    const out = {};
    for (const key of Object.keys(a)) {
        out[key] = [
            lerp(a[key][0], b[key][0], t),
            lerp(a[key][1], b[key][1], t),
            lerp(a[key][2], b[key][2], t),
        ];
    }
    return out;
}

function easeInOut(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

function inferGesture(word) {
    return WORD_GESTURES[String(word || "").trim().toLowerCase()] || "fingerspell";
}

function sanitizeToken(token) {
    const word = String((token && token.word) || "").trim();
    if (!word) return null;
    let gesture = String((token && token.gesture) || inferGesture(word)).trim().toLowerCase();
    if (!SUPPORTED_GESTURES.has(gesture)) {
        gesture = "fingerspell";
    }
    const out = { word, gesture };
    if (gesture === "fingerspell") {
        const chars = (Array.isArray(token && token.chars) ? token.chars : word.toUpperCase().split(""))
            .map((c) => String(c).toUpperCase())
            .filter((c) => /^[A-Z0-9]$/.test(c))
            .slice(0, 14);
        if (!chars.length) return null;
        out.chars = chars;
    }
    return out;
}

function getTokens(payload) {
    if (payload && Array.isArray(payload.sign_tokens) && payload.sign_tokens.length) {
        return payload.sign_tokens.map(sanitizeToken).filter(Boolean).slice(0, 36);
    }
    if (payload && Array.isArray(payload.sequence) && payload.sequence.length) {
        return payload.sequence
            .map((item) => sanitizeToken({
                word: item.word,
                gesture: item.type === "fingerspell" ? "fingerspell" : inferGesture(item.word),
                chars: item.chars,
            }))
            .filter(Boolean)
            .slice(0, 36);
    }
    return [];
}

const MAKEHUMAN_DEFAULT_MODEL_URL = "/static/models/makehuman/avatar.glb";
const MOCAP_MANIFEST_URL = "/static/models/sign-mocap/manifest.json";
const MOCAP_ARCHIVE_MODEL_URL = "/static/models/sign-mocap/base/avatar_mesh.fbx";
const AVATAR_LIBRARY_LOADS = new Map();

function loadScriptOnce(url) {
    const targetUrl = String(url || "").trim();
    if (!targetUrl) return Promise.resolve(false);
    if (AVATAR_LIBRARY_LOADS.has(targetUrl)) return AVATAR_LIBRARY_LOADS.get(targetUrl);

    const existing = Array.from(document.scripts || []).find((script) => script.src === targetUrl);
    if (existing && existing.dataset.loaded === "true") {
        const ready = Promise.resolve(true);
        AVATAR_LIBRARY_LOADS.set(targetUrl, ready);
        return ready;
    }

    const promise = new Promise((resolve, reject) => {
        const script = existing || document.createElement("script");
        const cleanup = () => {
            script.removeEventListener("load", handleLoad);
            script.removeEventListener("error", handleError);
        };
        const handleLoad = () => {
            script.dataset.loaded = "true";
            cleanup();
            resolve(true);
        };
        const handleError = () => {
            cleanup();
            reject(new Error(`Failed to load script: ${targetUrl}`));
        };

        script.addEventListener("load", handleLoad, { once: true });
        script.addEventListener("error", handleError, { once: true });

        if (!existing) {
            script.src = targetUrl;
            script.defer = true;
            script.dataset.dynamicAvatarLib = "true";
            document.head.appendChild(script);
        } else if (existing.dataset.loaded === "true") {
            cleanup();
            resolve(true);
        }
    });

    AVATAR_LIBRARY_LOADS.set(targetUrl, promise);
    return promise;
}

function getAvatarLibraryUrls(container) {
    const dataset = container && container.dataset ? container.dataset : {};
    return {
        three: String(dataset.avatarThreeUrl || "").trim(),
        gltf: String(dataset.avatarGltfLoaderUrl || "").trim(),
        fflate: String(dataset.avatarFflateUrl || "").trim(),
        fbx: String(dataset.avatarFbxLoaderUrl || "").trim(),
    };
}

function normalizeClipKey(value) {
    return String(value || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
}

const MAKEHUMAN_BONE_HINTS = {
    torso: ["spine", "pelvis", "hips"],
    head: ["head"],
    leftShoulder: ["leftshoulder", "lshoulder", "clavicle_l", "leftclavicle", "shoulder_l", "clavicle.l"],
    rightShoulder: ["rightshoulder", "rshoulder", "clavicle_r", "rightclavicle", "shoulder_r", "clavicle.r"],
    leftElbow: ["leftforearm", "leftlowerarm", "forearm_l", "lowerarm_l", "forearm.l"],
    rightElbow: ["rightforearm", "rightlowerarm", "forearm_r", "lowerarm_r", "forearm.r"],
    leftWrist: ["lefthand", "leftwrist", "hand_l", "wrist_l", "hand.l"],
    rightWrist: ["righthand", "rightwrist", "hand_r", "wrist_r", "hand.r"],
};

const HAND_FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"];

const HAND_PRESETS = {
    relaxed: {
        thumb: { curl: [0.34, 0.27, 0.22], spread: 0.22, yaw: 0.12, pitch: 0.03 },
        index: { curl: [0.46, 0.34, 0.26], spread: 0.16 },
        middle: { curl: [0.5, 0.38, 0.29], spread: 0.05 },
        ring: { curl: [0.54, 0.42, 0.32], spread: -0.07 },
        pinky: { curl: [0.58, 0.46, 0.35], spread: -0.18 },
    },
    open: {
        thumb: { curl: [0.16, 0.12, 0.1], spread: 0.35, yaw: 0.08 },
        index: { curl: [0.16, 0.1, 0.08], spread: 0.28 },
        middle: { curl: [0.14, 0.1, 0.08], spread: 0.08 },
        ring: { curl: [0.2, 0.14, 0.1], spread: -0.1 },
        pinky: { curl: [0.25, 0.17, 0.12], spread: -0.24 },
    },
    flat: {
        thumb: { curl: [0.2, 0.16, 0.12], spread: 0.24, yaw: 0.06 },
        index: { curl: [0.1, 0.08, 0.06], spread: 0.14 },
        middle: { curl: [0.1, 0.08, 0.06], spread: 0.04 },
        ring: { curl: [0.12, 0.09, 0.07], spread: -0.06 },
        pinky: { curl: [0.16, 0.12, 0.08], spread: -0.14 },
    },
    fist: {
        thumb: { curl: [0.56, 0.62, 0.56], spread: 0.18, yaw: 0.24, pitch: -0.02 },
        index: { curl: [1.32, 1.14, 0.98], spread: 0.1 },
        middle: { curl: [1.36, 1.16, 1.0], spread: 0.03 },
        ring: { curl: [1.32, 1.14, 0.97], spread: -0.04 },
        pinky: { curl: [1.26, 1.08, 0.92], spread: -0.1 },
    },
    point: {
        thumb: { curl: [0.46, 0.46, 0.38], spread: 0.18, yaw: 0.18 },
        index: { curl: [0.06, 0.04, 0.03], spread: 0.04 },
        middle: { curl: [1.22, 1.06, 0.9], spread: -0.02 },
        ring: { curl: [1.2, 1.04, 0.88], spread: -0.08 },
        pinky: { curl: [1.16, 1.0, 0.84], spread: -0.14 },
    },
    v_sign: {
        thumb: { curl: [0.42, 0.4, 0.34], spread: 0.12, yaw: 0.15 },
        index: { curl: [0.08, 0.06, 0.05], spread: 0.26 },
        middle: { curl: [0.08, 0.06, 0.05], spread: -0.18 },
        ring: { curl: [1.14, 1.0, 0.84], spread: -0.08 },
        pinky: { curl: [1.1, 0.96, 0.8], spread: -0.16 },
    },
    pinch: {
        thumb: { curl: [0.24, 0.22, 0.2], spread: 0.2, yaw: 0.18 },
        index: { curl: [0.52, 0.58, 0.52], spread: 0.05 },
        middle: { curl: [1.06, 0.96, 0.82], spread: -0.04 },
        ring: { curl: [1.06, 0.94, 0.8], spread: -0.09 },
        pinky: { curl: [1.02, 0.9, 0.76], spread: -0.15 },
    },
    cup: {
        thumb: { curl: [0.34, 0.3, 0.24], spread: 0.16, yaw: 0.12 },
        index: { curl: [0.62, 0.54, 0.42], spread: 0.1 },
        middle: { curl: [0.68, 0.58, 0.45], spread: 0.03 },
        ring: { curl: [0.7, 0.6, 0.46], spread: -0.04 },
        pinky: { curl: [0.72, 0.62, 0.47], spread: -0.1 },
    },
    ily: {
        thumb: { curl: [0.16, 0.14, 0.12], spread: 0.34, yaw: 0.2 },
        index: { curl: [0.08, 0.06, 0.05], spread: 0.2 },
        middle: { curl: [1.18, 1.04, 0.9], spread: 0.0 },
        ring: { curl: [1.16, 1.02, 0.88], spread: -0.08 },
        pinky: { curl: [0.1, 0.08, 0.06], spread: -0.28 },
    },
    thumbs_up: {
        thumb: { curl: [0.08, 0.06, 0.05], spread: 0.28, yaw: 0.34, pitch: -0.06 },
        index: { curl: [1.28, 1.12, 0.96], spread: 0.08 },
        middle: { curl: [1.32, 1.14, 0.98], spread: 0.01 },
        ring: { curl: [1.3, 1.12, 0.96], spread: -0.06 },
        pinky: { curl: [1.24, 1.06, 0.9], spread: -0.12 },
    },
};

function resolveHandPreset(preset, sideFactor) {
    const config = HAND_PRESETS[preset] || HAND_PRESETS.relaxed;
    const resolved = {};
    for (const name of HAND_FINGER_NAMES) {
        const pose = { ...(config[name] || {}) };
        if (pose.spread !== undefined) pose.spread *= sideFactor;
        if (pose.yaw !== undefined) pose.yaw *= sideFactor;
        if (pose.twist !== undefined) pose.twist *= sideFactor;
        resolved[name] = pose;
    }
    return resolved;
}

function getGestureHandPresets(gesture) {
    const g = String(gesture || "").toLowerCase();
    if (g === "wave") return { left: "relaxed", right: "open" };
    if (g === "thank_you") return { left: "relaxed", right: "flat" };
    if (g === "welcome") return { left: "relaxed", right: "open" };
    if (g === "positive") return { left: "relaxed", right: "thumbs_up" };
    if (g === "please" || g === "sorry") return { left: "relaxed", right: "cup" };
    if (g === "question") return { left: "open", right: "open" };
    if (g === "love") return { left: "open", right: "ily" };
    if (g === "point_you" || g === "point_self" || g === "need" || g === "name" || g === "directional" || g === "turn_on") {
        return { left: "relaxed", right: "point" };
    }
    if (g === "yes") return { left: "relaxed", right: "fist" };
    if (g === "no") return { left: "relaxed", right: "v_sign" };
    if (g === "help") return { left: "open", right: "cup" };
    if (g === "drink") return { left: "relaxed", right: "cup" };
    if (g === "eat") return { left: "relaxed", right: "pinch" };
    if (g === "stop") return { left: "relaxed", right: "open" };
    if (g === "repeat") return { left: "relaxed", right: "open" };
    if (g === "take_care") return { left: "open", right: "cup" };
    if (g === "light") return { left: "relaxed", right: "pinch" };
    if (g === "congratulations") return { left: "open", right: "open" };
    if (g === "fingerspell") return { left: "relaxed", right: "pinch" };
    return { left: "relaxed", right: "relaxed" };
}

function makeHumanFingerSegmentHints(side, finger, segment) {
    const sideLong = side === "left" ? "left" : "right";
    const sideShort = side === "left" ? "l" : "r";
    const altFinger = finger === "pinky" ? "little" : finger;
    return [
        `${sideLong}hand${finger}${segment}`,
        `${sideLong}${finger}${segment}`,
        `${finger}${segment}${sideShort}`,
        `${finger}${segment}_${sideShort}`,
        `${sideShort}${finger}${segment}`,
        `${sideLong}hand${altFinger}${segment}`,
        `${altFinger}${segment}${sideShort}`,
    ];
}

function getQuaternionAxesWorld(bone) {
    const THREE = window.THREE;
    if (!bone || !THREE) return null;
    const worldQuaternion = new THREE.Quaternion();
    bone.getWorldQuaternion(worldQuaternion);
    return {
        x: new THREE.Vector3(1, 0, 0).applyQuaternion(worldQuaternion).normalize(),
        y: new THREE.Vector3(0, 1, 0).applyQuaternion(worldQuaternion).normalize(),
        z: new THREE.Vector3(0, 0, 1).applyQuaternion(worldQuaternion).normalize(),
    };
}

function findBestLocalAxisForWorldVector(bone, target) {
    const axes = getQuaternionAxesWorld(bone);
    if (!axes || !target || target.lengthSq() < 0.000001) return null;
    let best = null;
    for (const axisName of ["x", "y", "z"]) {
        const dot = axes[axisName].dot(target);
        const score = Math.abs(dot);
        if (!best || score > best.score) {
            best = { axis: axisName, sign: dot >= 0 ? 1 : -1, score };
        }
    }
    return best;
}

function averageVectors(vectors) {
    const THREE = window.THREE;
    const total = new THREE.Vector3();
    let count = 0;
    for (const vector of vectors) {
        if (!vector || vector.lengthSq() < 0.000001) continue;
        total.add(vector);
        count += 1;
    }
    if (!count || total.lengthSq() < 0.000001) return null;
    return total.normalize();
}

function getBoneWorldPosition(bone) {
    const THREE = window.THREE;
    if (!bone || !THREE) return null;
    return bone.getWorldPosition(new THREE.Vector3());
}

function dedupeBones(bones) {
    const seen = new Set();
    const out = [];
    for (const bone of bones) {
        if (!bone || !bone.isBone || seen.has(bone.uuid)) continue;
        seen.add(bone.uuid);
        out.push(bone);
    }
    return out;
}

function buildGestureFramesForToken(token, poseFactory) {
    const g = token.gesture || "fingerspell";
    const p = (overrides) => poseFactory(overrides);
    if (g === "wave") return [p({ rS: [-0.85, 0, -0.9], rE: [-1.15, 0, 0.2], rW: [0.3, 0.1, 0] }), p({ rS: [-0.85, 0, -0.72], rE: [-1.08, 0, -0.22], rW: [0.12, -0.2, 0] }), p({ rS: [-0.85, 0, -1.02], rE: [-1.08, 0, 0.24], rW: [0.36, 0.2, 0] })];
    if (g === "thank_you") return [p({ rS: [-0.7, 0, -0.75], rE: [-1.45, 0, 0.1], rW: [0.34, 0.05, 0.06] }), p({ rS: [-0.32, 0, -0.42], rE: [-0.92, 0, -0.08], rW: [0.02, 0, -0.04] })];
    if (g === "welcome") return [p({ rS: [-0.26, 0, -0.26], rE: [-0.72, 0, -0.08], rW: [0.08, -0.18, 0.0] }), p({ rS: [-0.72, 0, -0.78], rE: [-1.1, 0, 0.12], rW: [0.28, 0.08, 0.06] })];
    if (g === "positive") return [p({ rS: [-0.6, 0, -0.32], rE: [-1.18, 0, 0.14], rW: [0.22, 0.12, 0.12], torso: [0.0, 0.06, 0.0] }), p({ rS: [-0.42, 0, -0.18], rE: [-0.96, 0, 0.08], rW: [0.1, 0.06, 0.06] })];
    if (g === "question") return [p({ lS: [-0.4, 0, 0.6], rS: [-0.4, 0, -0.6], lE: [-0.9, 0, 0], rE: [-0.9, 0, 0], head: [0.05, 0, 0] }), p({ lS: [-0.28, 0, 0.54], rS: [-0.28, 0, -0.54], head: [-0.03, 0, 0] })];
    if (g === "point_you") return [p({ rS: [-0.15, 0.35, -0.1], rE: [-0.08, 0, 0], torso: [0, 0.12, 0] })];
    if (g === "point_self") return [p({ rS: [-0.78, 0, -0.46], rE: [-1.48, 0, 0.16], rW: [0.25, 0.1, 0.1] })];
    if (g === "help") return [p({ lS: [-0.55, 0, 0.28], lE: [-1.2, 0, 0], rS: [-0.55, 0, -0.32], rE: [-1.32, 0, 0.08] }), p({ lS: [-0.22, 0, 0.1], lE: [-0.8, 0, 0], rS: [-0.24, 0, -0.2], rE: [-0.82, 0, 0] })];
    if (g === "need") return [p({ rS: [-0.22, 0, -0.42], rE: [-0.92, 0, 0] }), p({ rS: [-0.62, 0, -0.72], rE: [-1.3, 0, 0], rW: [0.5, 0, 0] })];
    if (g === "please") return [p({ rS: [-0.66, 0, -0.46], rE: [-1.35, 0, 0.06], rW: [0.2, 0.2, 0] }), p({ rS: [-0.66, 0, -0.52], rW: [0.2, -0.2, 0] }), p({ rS: [-0.66, 0, -0.46], rW: [0.2, 0.2, 0] })];
    if (g === "sorry") return [p({ rS: [-0.7, 0, -0.46], rE: [-1.4, 0, 0.08], rW: [0.28, 0.2, 0] }), p({ rS: [-0.7, 0, -0.52], rW: [0.28, -0.2, 0] })];
    if (g === "love") return [p({ lS: [-0.68, 0, 0.46], rS: [-0.68, 0, -0.46], lE: [-1.2, 0, -0.24], rE: [-1.2, 0, 0.24], torso: [0.03, 0, 0] })];
    if (g === "yes") return [p({ rS: [-0.62, 0, -0.5], rE: [-1.32, 0, 0.08], head: [0.08, 0, 0] }), p({ rS: [-0.54, 0, -0.44], rE: [-1.24, 0, 0.04], head: [-0.05, 0, 0] })];
    if (g === "no") return [p({ rS: [-0.46, 0, -0.5], rE: [-1.1, 0, 0], rW: [0, -0.18, -0.08] }), p({ rS: [-0.46, 0, -0.26], rE: [-1.1, 0, 0.3], rW: [0, 0.24, 0.1] })];
    if (g === "name") return [p({ lS: [-0.5, 0, 0.24], lE: [-1.06, 0, -0.08], rS: [-0.44, 0, -0.18], rE: [-1.0, 0, 0.14], torso: [0.0, 0.02, 0.0] }), p({ lS: [-0.48, 0, 0.18], rS: [-0.4, 0, -0.12], torso: [0.0, -0.02, 0.0] })];
    if (g === "drink") return [p({ rS: [-0.78, 0, -0.5], rE: [-1.48, 0, 0.12], rW: [0.46, 0.08, 0.12] }), p({ rS: [-0.46, 0, -0.2], rE: [-1.02, 0, 0.0], rW: [0.12, 0.02, 0.04] })];
    if (g === "eat") return [p({ rS: [-0.74, 0, -0.42], rE: [-1.42, 0, 0.08], rW: [0.36, 0.14, 0.08] }), p({ rS: [-0.38, 0, -0.14], rE: [-0.92, 0, 0.02], rW: [0.08, 0.02, 0.02] })];
    if (g === "directional") return [p({ rS: [-0.16, 0.26, -0.14], rE: [-0.2, 0, 0.1], rW: [0.0, 0.1, 0.02], torso: [0.0, 0.1, 0.0] }), p({ rS: [-0.26, 0.04, -0.42], rE: [-0.78, 0, 0.02], rW: [0.1, 0.0, 0.02] })];
    if (g === "stop") return [p({ rS: [-0.32, 0.16, -0.26], rE: [-0.72, 0, 0.16], rW: [0.08, -0.08, 0.02] }), p({ rS: [-0.32, 0.16, -0.3], rE: [-0.76, 0, 0.16], rW: [0.08, 0.08, 0.02] })];
    if (g === "repeat") return [p({ rS: [-0.3, 0.08, -0.24], rE: [-0.84, 0, 0.1], rW: [0.08, 0.08, 0.02] }), p({ rS: [-0.42, 0.08, -0.38], rE: [-0.98, 0, 0.06], rW: [0.18, 0.02, 0.02] }), p({ rS: [-0.3, 0.08, -0.24], rE: [-0.84, 0, 0.1], rW: [0.08, 0.08, 0.02] })];
    if (g === "take_care") return [p({ lS: [-0.56, 0, 0.26], lE: [-1.14, 0, -0.08], rS: [-0.54, 0, -0.28], rE: [-1.12, 0, 0.08], torso: [0.02, 0.0, 0.0] }), p({ lS: [-0.28, 0, 0.12], lE: [-0.78, 0, -0.02], rS: [-0.26, 0, -0.14], rE: [-0.8, 0, 0.02], torso: [0.0, 0.06, 0.0] })];
    if (g === "turn_on") return [p({ rS: [-0.28, 0.22, -0.16], rE: [-0.3, 0, 0.08], rW: [0.02, 0.12, -0.12] }), p({ rS: [-0.28, 0.22, -0.16], rE: [-0.32, 0, 0.12], rW: [0.16, -0.12, 0.12] })];
    if (g === "light") return [p({ rS: [-0.62, 0, -0.38], rE: [-1.14, 0, 0.12], rW: [0.22, -0.02, 0.06] }), p({ rS: [-0.42, 0, -0.2], rE: [-0.88, 0, 0.02], rW: [0.08, 0.12, 0.02] })];
    if (g === "congratulations") return [p({ lS: [-0.42, 0, 0.54], rS: [-0.42, 0, -0.54], lE: [-0.86, 0, -0.08], rE: [-0.86, 0, 0.08] }), p({ lS: [-0.58, 0, 0.34], rS: [-0.58, 0, -0.34], lE: [-1.08, 0, -0.1], rE: [-1.08, 0, 0.1] }), p({ lS: [-0.42, 0, 0.54], rS: [-0.42, 0, -0.54], lE: [-0.86, 0, -0.08], rE: [-0.86, 0, 0.08] })];

    const chars = (token.chars || []).slice(0, 10);
    if (!chars.length) return [clonePose(BASE_POSE)];
    return chars.map((char) => {
        const code = char.charCodeAt(0);
        const y = ((code % 5) - 2) * 0.08;
        const z = ((code % 7) - 3) * 0.07;
        return p({ rS: [-0.66 + y * 0.25, 0, -0.58 + z], rE: [-1.2 + y * 0.2, 0, z * 0.66], rW: [0.22 + z * 0.85, y * 0.9, z * 0.5] });
    });
}

class Avatar3D {
    constructor(container) {
        this.container = container;
        this.ready = false;
        this.runToken = 0;
        this.currentPose = clonePose(HAND_PREVIEW_POSE);
        this.style = getAvatarStyleConfig();
        this.expression = "neutral";
        this._blinkValue = 1;
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.clock = null;
        this.rig = null;
        this.resizeObserver = null;
        this.windowResizeHandler = null;
        this.fitRetryTimer = null;
    }

    isWebGLAvailable() {
        try {
            const canvas = document.createElement("canvas");
            return !!(
                window.WebGLRenderingContext &&
                (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
            );
        } catch (error) {
            return false;
        }
    }

    isContainerVisible() {
        if (!this.container) return false;
        const style = window.getComputedStyle(this.container);
        if (style.display === "none" || style.visibility === "hidden") return false;
        if (this.container.clientWidth < 8 || this.container.clientHeight < 8) return false;
        if (this.container.offsetParent === null && style.position !== "fixed") return false;
        return true;
    }

    queueFitRetry(reason = "retry") {
        if (this.fitRetryTimer || !this.container) return;
        this.fitRetryTimer = window.setTimeout(() => {
            this.fitRetryTimer = null;
            this.fitToContainer({ reason: `${reason} (retry)`, allowRetry: false });
        }, 180);
    }

    fitToContainer(options = {}) {
        if (!this.renderer || !this.camera || !this.container) return false;
        const reason = options.reason || "layout";
        const warnIfHidden = Boolean(options.warnIfHidden);
        const allowRetry = options.allowRetry !== false;

        if (!this.isContainerVisible()) {
            if (warnIfHidden) {
                console.warn(`[Avatar3D] fit skipped during ${reason}: avatar container is hidden or zero-sized. Retrying.`);
            }
            if (allowRetry) this.queueFitRetry(reason);
            return false;
        }

        const width = Math.max(this.container.clientWidth, 1);
        const height = Math.max(this.container.clientHeight, 1);
        const aspect = width / height;
        const shortEdge = Math.min(width, height);
        const shortfall = clamp((360 - shortEdge) / 360, 0, 1);
        const portraitBias = clamp((1 - aspect) * 0.62, -0.14, 0.48);

        // Keep the procedural fallback framed around the signing space instead of the full body.
        const modelScale = clamp(
            Math.min(shortEdge / 340, 1.08 - shortfall * 0.12 + portraitBias * 0.08),
            0.9,
            1.18
        );
        const cameraDistance = clamp(3.05 + shortfall * 0.5 + portraitBias * 0.18, 2.8, 3.8);
        const cameraFov = clamp(30 + shortfall * 6 + Math.max(0, 1.06 - aspect) * 6, 30, 40);
        const cameraY = clamp(0.66 - shortfall * 0.04, 0.58, 0.74);
        const lookAtY = clamp(0.18 - shortfall * 0.02, 0.12, 0.24);

        if (this.rig && this.rig.root) {
            this.rig.root.scale.setScalar(modelScale);
        }

        this.camera.aspect = aspect;
        this.camera.fov = cameraFov;
        this.camera.position.set(0, cameraY, cameraDistance);
        this.camera.lookAt(0, lookAtY, 0);
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
        return true;
    }

    async init() {
        if (this.ready || !this.container) return;
        if (!window.THREE) throw new Error("Three.js unavailable");
        if (!this.isWebGLAvailable()) throw new Error("WebGL unavailable");
        const THREE = window.THREE;

        this.container.innerHTML = "";
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0b1220);
        this.scene.fog = new THREE.Fog(0x0b1220, 6, 15);
        this.clock = new THREE.Clock();

        const w = Math.max(this.container.clientWidth, 260);
        const h = Math.max(this.container.clientHeight, 260);
        this.camera = new THREE.PerspectiveCamera(30, w / h, 0.1, 40);
        this.camera.position.set(0, 0.68, 3.15);
        this.camera.lookAt(0, 0.18, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
        this.renderer.setSize(w, h, false);
        if ("outputColorSpace" in this.renderer && THREE.SRGBColorSpace) {
            this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        }
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.04;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.className = "sign-avatar-canvas";
        this.container.appendChild(this.renderer.domElement);

        const hemi = new THREE.HemisphereLight(0xfffaf3, 0x111827, 0.8);
        const key = new THREE.DirectionalLight(0xffffff, 1.5);
        key.position.set(2.5, 5.0, 3.5);
        key.castShadow = true;
        key.shadow.mapSize.set(2048, 2048);
        key.shadow.camera.near = 0.5;
        key.shadow.camera.far = 15;
        key.shadow.bias = -0.0005;
        
        const fill = new THREE.DirectionalLight(0x6366f1, 0.9); // Indigo fill
        fill.position.set(-3.0, 2.5, 2.0);
        
        const rim = new THREE.DirectionalLight(0xec4899, 1.0); // Pink rim
        rim.position.set(-2.5, 3.0, -3.0);

        const rim2 = new THREE.DirectionalLight(0x8b5cf6, 0.8); // Purple back rim
        rim2.position.set(2.5, 2.0, -3.0);

        this.scene.add(hemi, key, fill, rim, rim2);

        const stageMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.2, metalness: 0.8 });
        const stage = new THREE.Mesh(new THREE.CylinderGeometry(1.9, 2.1, 0.18, 42), stageMat);
        stage.position.y = -1.66;
        stage.receiveShadow = true;
        this.scene.add(stage);

        const halo = new THREE.Mesh(
            new THREE.TorusGeometry(1.2, 0.04, 16, 100),
            new THREE.MeshStandardMaterial({ color: 0x6366f1, emissive: 0x4f46e5, roughness: 0.2, metalness: 0.8, emissiveIntensity: 2.5 })
        );
        halo.rotation.x = -Math.PI / 2;
        halo.position.y = -1.56;
        this.scene.add(halo);

        const backdrop = new THREE.Mesh(
            new THREE.CylinderGeometry(3.1, 3.1, 3.8, 52, 1, true, Math.PI * 0.18, Math.PI * 0.64),
            new THREE.MeshStandardMaterial({ color: 0x101a33, roughness: 1.0, metalness: 0.0, side: THREE.BackSide })
        );
        backdrop.position.y = 0.18;
        this.scene.add(backdrop);

        this.rig = this.buildRig();
        this.scene.add(this.rig.root);
        this.applyPose(HAND_PREVIEW_POSE);
        this.setGestureHands("relaxed");
        this.setExpression("neutral");

        const resize = () => {
            this.fitToContainer({ reason: "resize" });
        };

        if (typeof ResizeObserver !== "undefined") {
            this.resizeObserver = new ResizeObserver(() => resize());
            this.resizeObserver.observe(this.container);
        } else {
            this.windowResizeHandler = () => resize();
            window.addEventListener("resize", this.windowResizeHandler);
        }
        this.fitToContainer({ reason: "init" });

        const render = () => {
            if (!this.renderer || !this.scene || !this.camera || !this.rig) return;
            const t = this.clock.getElapsedTime();
            this.rig.torsoPivot.position.y = 0.75 + Math.sin(t * 1.5) * 0.02;
            this.rig.root.rotation.y = Math.sin(t * 0.42) * 0.018;
            this.updateFaceMotion(t);
            this.renderer.render(this.scene, this.camera);
            window.requestAnimationFrame(render);
        };
        render();

        this.ready = true;
    }

    makeOutlinedMesh(geometry, material, outlineMaterial, outlineScale = 1.035) {
        const base = new window.THREE.Mesh(geometry, material);
        base.castShadow = true;
        base.receiveShadow = true;

        const outline = new window.THREE.Mesh(geometry, outlineMaterial);
        outline.scale.setScalar(outlineScale);

        const group = new window.THREE.Group();
        group.add(outline, base);
        return { group, base, outline };
    }

    buildHairStyle(styleName, hairMaterial, outlineMat) {
        const THREE = window.THREE;
        const root = new THREE.Group();

        if (styleName === "bun") {
            const cap = this.makeOutlinedMesh(
                new THREE.SphereGeometry(0.5, 24, 24, 0, Math.PI * 2, 0, Math.PI * 0.6),
                hairMaterial,
                outlineMat,
                1.03
            );
            cap.group.position.set(0, 0.62, 0.02);
            root.add(cap.group);

            const bun = this.makeOutlinedMesh(new THREE.SphereGeometry(0.19, 18, 18), hairMaterial, outlineMat, 1.03);
            bun.group.position.set(0, 0.86, -0.18);
            root.add(bun.group);

            const fringe = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.2, 0.24, 0.14, 16), hairMaterial, outlineMat, 1.03);
            fringe.group.position.set(0, 0.66, 0.35);
            fringe.group.rotation.x = Math.PI * 0.42;
            root.add(fringe.group);
            return root;
        }

        if (styleName === "layered") {
            const cap = this.makeOutlinedMesh(
                new THREE.SphereGeometry(0.5, 24, 24, 0, Math.PI * 2, 0, Math.PI * 0.62),
                hairMaterial,
                outlineMat,
                1.03
            );
            cap.group.position.set(0, 0.62, 0.0);
            root.add(cap.group);

            const sideL = this.makeOutlinedMesh(new THREE.BoxGeometry(0.14, 0.23, 0.16), hairMaterial, outlineMat, 1.03);
            sideL.group.position.set(-0.34, 0.56, 0.06);
            sideL.group.rotation.z = 0.16;
            const sideR = this.makeOutlinedMesh(new THREE.BoxGeometry(0.14, 0.23, 0.16), hairMaterial, outlineMat, 1.03);
            sideR.group.position.set(0.34, 0.56, 0.06);
            sideR.group.rotation.z = -0.16;
            root.add(sideL.group, sideR.group);

            const fringe = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.23, 0.28, 0.18, 18), hairMaterial, outlineMat, 1.03);
            fringe.group.position.set(0, 0.67, 0.34);
            fringe.group.rotation.x = Math.PI * 0.36;
            root.add(fringe.group);
            return root;
        }

        const cap = this.makeOutlinedMesh(
            new THREE.SphereGeometry(0.505, 24, 24, 0, Math.PI * 2, 0, Math.PI * 0.58),
            hairMaterial,
            outlineMat,
            1.03
        );
        cap.group.position.set(0, 0.62, 0.03);
        root.add(cap.group);

        const fringe = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.2, 0.23, 0.16, 16), hairMaterial, outlineMat, 1.03);
        fringe.group.position.set(0, 0.66, 0.36);
        fringe.group.rotation.x = Math.PI * 0.42;
        root.add(fringe.group);
        return root;
    }

    setExpression(mode = "neutral") {
        if (!this.rig || !this.rig.face) return;
        this.expression = mode;
        const face = this.rig.face;

        if (mode === "happy") {
            face.browL.rotation.z = -0.18;
            face.browR.rotation.z = 0.18;
            face.browL.position.y = face.base.browY + 0.01;
            face.browR.position.y = face.base.browY + 0.01;
            face.smile.scale.set(1.12, 1.0, 1.0);
            face.smile.position.y = face.base.smileY + 0.01;
            face.pupilL.position.y = face.base.pupilY + 0.004;
            face.pupilR.position.y = face.base.pupilY + 0.004;
            return;
        }

        if (mode === "focus") {
            face.browL.rotation.z = -0.04;
            face.browR.rotation.z = 0.04;
            face.browL.position.y = face.base.browY - 0.01;
            face.browR.position.y = face.base.browY - 0.01;
            face.smile.scale.set(0.8, 0.8, 1.0);
            face.smile.position.y = face.base.smileY - 0.01;
            face.pupilL.position.y = face.base.pupilY;
            face.pupilR.position.y = face.base.pupilY;
            return;
        }

        if (mode === "question") {
            face.browL.rotation.z = -0.28;
            face.browR.rotation.z = 0.03;
            face.browL.position.y = face.base.browY + 0.04;
            face.browR.position.y = face.base.browY + 0.008;
            face.smile.scale.set(0.86, 0.85, 1.0);
            face.smile.position.y = face.base.smileY - 0.008;
            face.pupilL.position.y = face.base.pupilY + 0.01;
            face.pupilR.position.y = face.base.pupilY + 0.01;
            return;
        }

        if (mode === "frown") {
            face.browL.rotation.z = 0.18;
            face.browR.rotation.z = -0.18;
            face.browL.position.y = face.base.browY - 0.005;
            face.browR.position.y = face.base.browY - 0.005;
            face.smile.scale.set(0.72, -0.9, 1.0);
            face.smile.position.y = face.base.smileY - 0.018;
            face.pupilL.position.y = face.base.pupilY - 0.005;
            face.pupilR.position.y = face.base.pupilY - 0.005;
            return;
        }

        face.browL.rotation.z = face.base.browLZ;
        face.browR.rotation.z = face.base.browRZ;
        face.browL.position.y = face.base.browY;
        face.browR.position.y = face.base.browY;
        face.smile.scale.set(1, 1, 1);
        face.smile.position.y = face.base.smileY;
        face.pupilL.position.y = face.base.pupilY;
        face.pupilR.position.y = face.base.pupilY;
    }

    expressionForGesture(gesture) {
        const g = String(gesture || "").toLowerCase();
        if (g === "wave" || g === "thank_you" || g === "welcome" || g === "positive" || g === "love" || g === "take_care" || g === "congratulations") return "happy";
        if (g === "question") return "question";
        if (g === "no" || g === "sorry") return "frown";
        if (g === "fingerspell" || g === "point_you" || g === "point_self" || g === "need" || g === "name" || g === "directional" || g === "turn_on" || g === "stop" || g === "light") return "focus";
        return "neutral";
    }

    updateFaceMotion(t) {
        if (!this.rig || !this.rig.face) return;
        const face = this.rig.face;
        const blinkCycle = Math.abs(Math.sin(t * 1.2 + 0.65));
        let blink = 1;
        if (blinkCycle > 0.965) {
            const k = (blinkCycle - 0.965) / 0.035;
            blink = Math.max(0.1, 1 - k * 0.95);
        }
        this._blinkValue = blink;

        const bob = Math.sin(t * 0.75) * 0.01;
        face.eyeL.group.scale.y = blink;
        face.eyeR.group.scale.y = blink;
        face.eyeL.group.position.y = face.base.eyeY + bob;
        face.eyeR.group.position.y = face.base.eyeY + bob;
        face.pupilL.scale.y = blink;
        face.pupilR.scale.y = blink;
    }

    buildRig() {
        const THREE = window.THREE;
        const style = this.style || getAvatarStyleConfig();
        const outlineMat = new THREE.MeshBasicMaterial({ color: 0x0f172a, side: THREE.BackSide });
        const skin = new THREE.MeshToonMaterial({ color: style.skin });
        const hoodie = new THREE.MeshToonMaterial({ color: style.hoodie });
        const hoodieAccent = new THREE.MeshToonMaterial({ color: style.hoodieAccent });
        const hair = new THREE.MeshToonMaterial({ color: style.hair });
        const eyeWhite = new THREE.MeshToonMaterial({ color: 0xffffff });
        const eyeDark = new THREE.MeshToonMaterial({ color: style.eyeDark });
        const lip = new THREE.MeshToonMaterial({ color: style.lip });

        const root = new THREE.Group();
        root.position.y = -0.24;

        const torsoPivot = new THREE.Group();
        torsoPivot.position.y = 0.74;
        root.add(torsoPivot);

        const torsoGeom = THREE.CapsuleGeometry
            ? new THREE.CapsuleGeometry(0.5, 0.95, 8, 18)
            : new THREE.CylinderGeometry(0.5, 0.58, 1.68, 20);
        const torsoPart = this.makeOutlinedMesh(torsoGeom, hoodie, outlineMat, 1.042);
        torsoPivot.add(torsoPart.group);

        const chestGeom = THREE.RoundedBoxGeometry
            ? new THREE.RoundedBoxGeometry(0.52, 1.0, 0.12, 5, 0.04)
            : new THREE.BoxGeometry(0.52, 1.0, 0.12);
        const chestPatch = this.makeOutlinedMesh(chestGeom, hoodieAccent, outlineMat, 1.03);
        chestPatch.group.position.set(0, 0.02, 0.44);
        torsoPivot.add(chestPatch.group);

        const hoodRing = this.makeOutlinedMesh(new THREE.TorusGeometry(0.35, 0.05, 10, 30), hoodieAccent, outlineMat, 1.03);
        hoodRing.group.rotation.x = Math.PI / 2;
        hoodRing.group.position.y = 0.5;
        torsoPivot.add(hoodRing.group);

        const stringL = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.015, 0.015, 0.32, 8), eyeWhite, outlineMat, 1.02);
        stringL.group.position.set(-0.08, 0.25, 0.49);
        stringL.group.rotation.z = 0.1;
        const stringR = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.015, 0.015, 0.32, 8), eyeWhite, outlineMat, 1.02);
        stringR.group.position.set(0.08, 0.25, 0.49);
        stringR.group.rotation.z = -0.1;
        torsoPivot.add(stringL.group, stringR.group);

        const headPivot = new THREE.Group();
        headPivot.position.y = 1.12;
        torsoPivot.add(headPivot);

        const neck = this.makeOutlinedMesh(new THREE.CylinderGeometry(0.1, 0.1, 0.16, 10), skin, outlineMat, 1.03);
        neck.group.position.y = -0.09;
        headPivot.add(neck.group);

        const head = this.makeOutlinedMesh(new THREE.SphereGeometry(0.5, 26, 26), skin, outlineMat, 1.038);
        head.group.position.y = 0.42;
        headPivot.add(head.group);

        const earL = this.makeOutlinedMesh(new THREE.SphereGeometry(0.085, 14, 14), skin, outlineMat, 1.03);
        earL.group.position.set(-0.47, 0.43, 0.02);
        const earR = this.makeOutlinedMesh(new THREE.SphereGeometry(0.085, 14, 14), skin, outlineMat, 1.03);
        earR.group.position.set(0.47, 0.43, 0.02);
        headPivot.add(earL.group, earR.group);

        const hairGroup = this.buildHairStyle(style.hairStyle, hair, outlineMat);
        headPivot.add(hairGroup);

        const eyeL = this.makeOutlinedMesh(new THREE.SphereGeometry(0.085, 14, 14), eyeWhite, outlineMat, 1.02);
        eyeL.group.position.set(-0.165, 0.5, 0.405);
        const eyeR = this.makeOutlinedMesh(new THREE.SphereGeometry(0.085, 14, 14), eyeWhite, outlineMat, 1.02);
        eyeR.group.position.set(0.165, 0.5, 0.405);
        headPivot.add(eyeL.group, eyeR.group);

        const pupilL = new THREE.Mesh(new THREE.SphereGeometry(0.034, 10, 10), eyeDark);
        pupilL.position.set(-0.165, 0.49, 0.477);
        const pupilR = pupilL.clone();
        pupilR.position.x = 0.165;
        headPivot.add(pupilL, pupilR);

        const browL = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.018, 0.02), eyeDark);
        browL.position.set(-0.16, 0.61, 0.43);
        browL.rotation.z = -0.1;
        const browR = browL.clone();
        browR.position.x = 0.16;
        browR.rotation.z = 0.1;
        headPivot.add(browL, browR);

        const nose = new THREE.Mesh(new THREE.SphereGeometry(0.028, 10, 10), new THREE.MeshToonMaterial({ color: style.nose || 0xedb892 }));
        nose.position.set(0, 0.43, 0.485);
        headPivot.add(nose);

        const smile = new THREE.Mesh(new THREE.TorusGeometry(0.115, 0.011, 10, 28, Math.PI), lip);
        smile.position.set(0, 0.33, 0.49);
        smile.rotation.z = Math.PI;
        headPivot.add(smile);

        const blushMat = new THREE.MeshToonMaterial({ color: 0xfda4af, transparent: true, opacity: 0.5 });
        const blushL = new THREE.Mesh(new THREE.SphereGeometry(0.055, 10, 10), blushMat);
        blushL.scale.set(1.2, 0.45, 0.5);
        blushL.position.set(-0.24, 0.39, 0.45);
        const blushR = blushL.clone();
        blushR.position.x = 0.24;
        headPivot.add(blushL, blushR);

        const left = this.buildArm(-1, { skin, sleeve: hoodie, cuff: hoodieAccent, outlineMat, nailColor: style.nail });
        const right = this.buildArm(1, { skin, sleeve: hoodie, cuff: hoodieAccent, outlineMat, nailColor: style.nail });
        torsoPivot.add(left.shoulder);
        torsoPivot.add(right.shoulder);

        const baseFace = {
            browY: 0.61,
            browLZ: -0.1,
            browRZ: 0.1,
            smileY: 0.33,
            pupilY: 0.49,
            eyeY: 0.5,
        };

        return {
            root,
            torsoPivot,
            headPivot,
            left,
            right,
            face: {
                eyeL,
                eyeR,
                pupilL,
                pupilR,
                browL,
                browR,
                smile,
                base: baseFace,
            },
        };
    }

    buildArm(side, palette) {
        const THREE = window.THREE;
        const { skin, sleeve, cuff, outlineMat, nailColor } = palette;
        const shoulder = new THREE.Group();
        shoulder.position.set(0.63 * side, 0.58, 0);

        const shoulderJoint = this.makeOutlinedMesh(new THREE.SphereGeometry(0.11, 14, 14), sleeve, outlineMat, 1.03);
        shoulder.add(shoulderJoint.group);

        const upperGeom = THREE.CapsuleGeometry
            ? new THREE.CapsuleGeometry(0.12, 0.58, 8, 14)
            : new THREE.CylinderGeometry(0.12, 0.13, 0.82, 14);
        const upper = this.makeOutlinedMesh(upperGeom, sleeve, outlineMat, 1.034);
        upper.group.position.y = -0.39;
        shoulder.add(upper.group);

        const elbow = new THREE.Group();
        elbow.position.y = -0.77;
        shoulder.add(elbow);

        const elbowJoint = this.makeOutlinedMesh(new THREE.SphereGeometry(0.096, 12, 12), sleeve, outlineMat, 1.03);
        elbow.add(elbowJoint.group);

        const foreGeom = THREE.CapsuleGeometry
            ? new THREE.CapsuleGeometry(0.1, 0.52, 8, 12)
            : new THREE.CylinderGeometry(0.1, 0.11, 0.72, 12);
        const fore = this.makeOutlinedMesh(foreGeom, skin, outlineMat, 1.03);
        fore.group.position.y = -0.34;
        elbow.add(fore.group);

        const cuffBand = this.makeOutlinedMesh(new THREE.TorusGeometry(0.105, 0.018, 8, 16), cuff, outlineMat, 1.02);
        cuffBand.group.position.y = -0.63;
        cuffBand.group.rotation.x = Math.PI / 2;
        elbow.add(cuffBand.group);

        const wrist = new THREE.Group();
        wrist.position.y = -0.68;
        elbow.add(wrist);

        const hand = this.buildHand(side, { skin, outlineMat, nailColor });
        hand.root.position.y = -0.12;
        wrist.add(hand.root);

        return { shoulder, elbow, wrist, hand };
    }

    buildHand(side, palette) {
        const THREE = window.THREE;
        const { skin, outlineMat, nailColor } = palette;

        const root = new THREE.Group();
        root.rotation.x = 0.08;
        root.rotation.z = -side * 0.06;
        const palm = this.makeOutlinedMesh(new THREE.BoxGeometry(0.24, 0.13, 0.2), skin, outlineMat, 1.03);
        palm.group.scale.set(1.0, 1.0, 0.95);
        root.add(palm.group);

        const heel = this.makeOutlinedMesh(new THREE.SphereGeometry(0.075, 12, 12), skin, outlineMat, 1.025);
        heel.group.position.set(0, 0.03, -0.02);
        heel.group.scale.set(1.3, 0.85, 1.0);
        root.add(heel.group);

        const fingers = {
            thumb: this.buildFinger(
                {
                    x: 0.11 * side,
                    y: -0.015,
                    z: 0.05,
                    rotX: -0.48,
                    rotY: side * 0.28,
                    rotZ: side * 0.92,
                    lengths: [0.09, 0.075, 0.06],
                    radius: [0.03, 0.026, 0.022],
                },
                { skin, outlineMat, nailColor }
            ),
            index: this.buildFinger(
                {
                    x: side * 0.06,
                    y: -0.068,
                    z: 0.09,
                    rotX: -0.22,
                    rotY: 0,
                    rotZ: side * 0.08,
                    lengths: [0.11, 0.085, 0.07],
                    radius: [0.026, 0.023, 0.02],
                },
                { skin, outlineMat, nailColor }
            ),
            middle: this.buildFinger(
                {
                    x: side * 0.02,
                    y: -0.074,
                    z: 0.096,
                    rotX: -0.2,
                    rotY: 0,
                    rotZ: 0,
                    lengths: [0.125, 0.095, 0.076],
                    radius: [0.028, 0.024, 0.021],
                },
                { skin, outlineMat, nailColor }
            ),
            ring: this.buildFinger(
                {
                    x: side * -0.02,
                    y: -0.071,
                    z: 0.09,
                    rotX: -0.2,
                    rotY: 0,
                    rotZ: side * -0.05,
                    lengths: [0.116, 0.088, 0.07],
                    radius: [0.026, 0.023, 0.02],
                },
                { skin, outlineMat, nailColor }
            ),
            pinky: this.buildFinger(
                {
                    x: side * -0.055,
                    y: -0.063,
                    z: 0.08,
                    rotX: -0.18,
                    rotY: 0,
                    rotZ: side * -0.14,
                    lengths: [0.09, 0.072, 0.058],
                    radius: [0.022, 0.019, 0.016],
                },
                { skin, outlineMat, nailColor }
            ),
        };

        root.add(fingers.thumb.root, fingers.index.root, fingers.middle.root, fingers.ring.root, fingers.pinky.root);
        return { root, palm: palm.group, fingers, side };
    }

    buildFinger(spec, palette) {
        const THREE = window.THREE;
        const { skin, outlineMat, nailColor } = palette;
        const fingerRoot = new THREE.Group();
        fingerRoot.position.set(spec.x, spec.y, spec.z);
        fingerRoot.rotation.set(spec.rotX, spec.rotY, spec.rotZ);

        const bend0 = new THREE.Group();
        fingerRoot.add(bend0);
        const bends = [bend0];
        let currentJoint = bend0;
        let lastSegLen = 0.06;
        let lastSegRad = 0.018;

        for (let i = 0; i < spec.lengths.length; i += 1) {
            const segLen = spec.lengths[i];
            const segRad = spec.radius[i];
            lastSegLen = segLen;
            lastSegRad = segRad;
            const segGeom = THREE.CapsuleGeometry
                ? new THREE.CapsuleGeometry(segRad, Math.max(segLen - (segRad * 2), segLen * 0.3), 6, 10)
                : new THREE.CylinderGeometry(segRad, segRad * 0.95, segLen, 10);
            const segment = this.makeOutlinedMesh(segGeom, skin, outlineMat, 1.02);
            segment.group.position.y = -segLen * 0.5;
            currentJoint.add(segment.group);

            if (i < spec.lengths.length - 1) {
                const nextJoint = new THREE.Group();
                nextJoint.position.y = -segLen;
                currentJoint.add(nextJoint);
                bends.push(nextJoint);
                currentJoint = nextJoint;
            }
        }

        const nail = this.makeOutlinedMesh(
            new THREE.BoxGeometry(lastSegRad * 1.05, lastSegRad * 0.22, lastSegRad * 0.72),
            new THREE.MeshToonMaterial({ color: nailColor || 0xfce7f3 }),
            outlineMat,
            1.01
        );
        nail.group.position.set(0, -lastSegLen + lastSegRad * 0.16, lastSegRad * 0.58);
        currentJoint.add(nail.group);

        return {
            root: fingerRoot,
            bends,
            baseRotation: { x: spec.rotX, y: spec.rotY, z: spec.rotZ },
        };
    }

    setFingerCurl(finger, curl) {
        if (!finger || !Array.isArray(finger.bends)) return;
        const c0 = Array.isArray(curl) ? Number(curl[0] || 0) : Number(curl || 0);
        const c1 = Array.isArray(curl) ? Number(curl[1] || c0 * 0.8) : c0 * 0.8;
        const c2 = Array.isArray(curl) ? Number(curl[2] || c1 * 0.85) : c1 * 0.85;
        finger.bends[0].rotation.x = c0;
        if (finger.bends[1]) finger.bends[1].rotation.x = c1;
        if (finger.bends[2]) finger.bends[2].rotation.x = c2;
    }

    setFingerPose(finger, pose) {
        if (!finger) return;
        const base = finger.baseRotation || { x: 0, y: 0, z: 0 };
        const pitch = Number((pose && pose.pitch) || 0);
        const yaw = Number((pose && pose.yaw) || 0);
        const spread = Number((pose && pose.spread) || 0);
        const twist = Number((pose && pose.twist) || 0);
        finger.root.rotation.set(base.x + pitch, base.y + yaw + twist, base.z + spread);
        this.setFingerCurl(finger, (pose && pose.curl) || 0.4);
    }

    setHandPreset(hand, preset) {
        if (!hand || !hand.fingers) return;
        const f = hand.fingers;
        const config = resolveHandPreset(preset, Number(hand.side || 1));
        for (const name of HAND_FINGER_NAMES) {
            const finger = f[name];
            this.setFingerPose(finger, config[name] || {});
        }
    }

    setGestureHands(gesture) {
        if (!this.rig || !this.rig.left || !this.rig.right) return;
        const presets = getGestureHandPresets(gesture);
        this.setHandPreset(this.rig.left.hand, presets.left);
        this.setHandPreset(this.rig.right.hand, presets.right);
    }

    applyPose(pose) {
        this.rig.torsoPivot.rotation.set(pose.torso[0], pose.torso[1], pose.torso[2]);
        this.rig.headPivot.rotation.set(pose.head[0], pose.head[1], pose.head[2]);
        this.rig.left.shoulder.rotation.set(pose.lS[0], pose.lS[1], pose.lS[2]);
        this.rig.right.shoulder.rotation.set(pose.rS[0], pose.rS[1], pose.rS[2]);
        this.rig.left.elbow.rotation.set(pose.lE[0], pose.lE[1], pose.lE[2]);
        this.rig.right.elbow.rotation.set(pose.rE[0], pose.rE[1], pose.rE[2]);
        this.rig.left.wrist.rotation.set(pose.lW[0], pose.lW[1], pose.lW[2]);
        this.rig.right.wrist.rotation.set(pose.rW[0], pose.rW[1], pose.rW[2]);
        this.currentPose = clonePose(pose);
    }

    async tween(target, duration, runToken) {
        const to = mergePose(BASE_POSE, target);
        const from = clonePose(this.currentPose);
        return new Promise((resolve) => {
            const start = performance.now();
            const step = (now) => {
                if (this.runToken !== runToken) return resolve(false);
                const t = Math.min((now - start) / Math.max(duration, 1), 1);
                this.applyPose(lerpPose(from, to, easeInOut(t)));
                if (t < 1) return window.requestAnimationFrame(step);
                this.applyPose(to);
                resolve(true);
            };
            window.requestAnimationFrame(step);
        });
    }

    pose(overrides) {
        return mergePose(BASE_POSE, overrides);
    }

    gestureFrames(token) {
        return buildGestureFramesForToken(token, (overrides) => this.pose(overrides));
    }

    async showProcessing(runToken) {
        this.runToken = runToken;
        this.setGestureHands("open");
        this.setExpression("focus");
        await this.tween(this.pose({ lS: [-0.34, 0, 0.44], rS: [-0.34, 0, -0.44], lE: [-0.88, 0, 0], rE: [-0.88, 0, 0] }), 180, runToken);
    }

    async showIdle(runToken) {
        this.runToken = runToken;
        this.setGestureHands("relaxed");
        this.setExpression("neutral");
        await this.tween(HAND_PREVIEW_POSE, 200, runToken);
    }

    async play(tokens, runToken) {
        this.runToken = runToken;
        this.setGestureHands("relaxed");
        this.setExpression("neutral");
        await this.tween(HAND_PREVIEW_POSE, 120, runToken);
        for (const token of tokens) {
            if (this.runToken !== runToken) return false;
            this.setGestureHands(token.gesture || "");
            this.setExpression(this.expressionForGesture(token.gesture || ""));
            const frames = this.gestureFrames(token);
            for (const frame of frames) {
                const ok = await this.tween(frame, token.gesture === "fingerspell" ? 140 : 210, runToken);
                if (!ok) return false;
            }
        }
        this.setGestureHands("relaxed");
        this.setExpression("happy");
        await this.tween(HAND_PREVIEW_POSE, 220, runToken);
        this.setExpression("neutral");
        return true;
    }
}

function findFirstBoneByHints(root, hints) {
    if (!root || !Array.isArray(hints) || !hints.length) return null;
    let found = null;
    root.traverse((node) => {
        if (found || !node || !node.isBone) return;
        const name = String(node.name || "").toLowerCase();
        if (!name) return;
        if (hints.some((hint) => name.includes(hint))) found = node;
    });
    return found;
}

class MakeHumanAvatar3D {
    constructor(container) {
        this.container = container;
        this.ready = false;
        this.runToken = 0;
        this.currentPose = clonePose(HAND_PREVIEW_POSE);
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.clock = null;
        this.modelRoot = null;
        this.baseModelScale = 1;
        this.baseModelY = -1.6;
        this.currentModelY = -1.6;
        this.baseGroundOffset = 0.02;
        this.bones = {};
        this.handRig = { left: null, right: null };
        this.restBoneRotations = [];
        this.currentHandPresets = { left: "relaxed", right: "relaxed" };
        this.resizeObserver = null;
        this.windowResizeHandler = null;
        this.fitRetryTimer = null;
        const hintedUrl = this.container && this.container.dataset
            ? this.container.dataset.makehumanModelUrl
            : "";
        this.modelUrl = hintedUrl || MAKEHUMAN_DEFAULT_MODEL_URL;
    }

    isWebGLAvailable() {
        try {
            const canvas = document.createElement("canvas");
            return !!(
                window.WebGLRenderingContext &&
                (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
            );
        } catch (error) {
            return false;
        }
    }

    isContainerVisible() {
        if (!this.container) return false;
        const style = window.getComputedStyle(this.container);
        if (style.display === "none" || style.visibility === "hidden") return false;
        if (this.container.clientWidth < 8 || this.container.clientHeight < 8) return false;
        if (this.container.offsetParent === null && style.position !== "fixed") return false;
        return true;
    }

    queueFitRetry(reason = "retry") {
        if (this.fitRetryTimer || !this.container) return;
        this.fitRetryTimer = window.setTimeout(() => {
            this.fitRetryTimer = null;
            this.fitToContainer({ reason: `${reason} (retry)`, allowRetry: false });
        }, 180);
    }

    fitToContainer(options = {}) {
        if (!this.renderer || !this.camera || !this.container) return false;
        const reason = options.reason || "layout";
        const warnIfHidden = Boolean(options.warnIfHidden);
        const allowRetry = options.allowRetry !== false;

        if (!this.isContainerVisible()) {
            if (warnIfHidden) {
                console.warn(`[MakeHumanAvatar3D] fit skipped during ${reason}: container hidden or zero-sized.`);
            }
            if (allowRetry) this.queueFitRetry(reason);
            return false;
        }

        const width = Math.max(this.container.clientWidth, 1);
        const height = Math.max(this.container.clientHeight, 1);
        const aspect = width / height;
        const shortEdge = Math.min(width, height);
        const shortfall = clamp((360 - shortEdge) / 360, 0, 1);
        const portraitBias = clamp((1 - aspect) * 0.58, -0.16, 0.42);

        // The MakeHuman renderer is framed on the hands and wrists so the sign is readable.
        const cameraDistance = clamp(3.1 + shortfall * 0.5 + portraitBias * 0.16, 2.86, 3.82);
        const cameraFov = clamp(30 + shortfall * 6 + Math.max(0, 1.04 - aspect) * 6, 30, 40);
        const cameraY = clamp(0.66 - shortfall * 0.04, 0.58, 0.76);
        const lookAtY = clamp(0.18 - shortfall * 0.03, 0.1, 0.24);
        const modelScale = clamp(this.baseModelScale * (1.12 - shortfall * 0.08), this.baseModelScale * 1.02, this.baseModelScale * 1.2);

        if (this.modelRoot) {
            this.modelRoot.scale.setScalar(modelScale);
            const ratio = modelScale / Math.max(this.baseModelScale, 0.0001);
            this.currentModelY = -1.7 + this.baseGroundOffset * ratio;
            this.modelRoot.position.y = this.currentModelY;
        }

        this.camera.aspect = aspect;
        this.camera.fov = cameraFov;
        this.camera.position.set(0, cameraY, cameraDistance);
        this.camera.lookAt(0, lookAtY, 0);
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
        return true;
    }

    trackedBones() {
        const bones = Object.values(this.bones);
        for (const side of ["left", "right"]) {
            const hand = this.handRig[side];
            if (!hand) continue;
            bones.push(hand.handBone);
            for (const fingerName of HAND_FINGER_NAMES) {
                const finger = hand.fingers[fingerName];
                if (!finger || !Array.isArray(finger.bones)) continue;
                bones.push(...finger.bones);
            }
        }
        return dedupeBones(bones);
    }

    captureRestRotations() {
        this.restBoneRotations = this.trackedBones().map((bone) => ({
            bone,
            rest: bone.quaternion.clone(),
        }));
    }

    resetToRestRotations() {
        for (const entry of this.restBoneRotations) {
            if (entry && entry.bone && entry.rest) entry.bone.quaternion.copy(entry.rest);
        }
    }

    findFingerChain(side, finger) {
        const chain = [];
        for (let segment = 1; segment <= 4; segment += 1) {
            const bone = findFirstBoneByHints(this.modelRoot, makeHumanFingerSegmentHints(side, finger, segment));
            if (bone) chain.push(bone);
        }
        return chain;
    }

    detectHandRig(side) {
        const handBone = side === "left" ? this.bones.leftWrist : this.bones.rightWrist;
        const fingers = {};
        for (const fingerName of HAND_FINGER_NAMES) {
            fingers[fingerName] = {
                name: fingerName,
                bones: this.findFingerChain(side, fingerName),
            };
        }
        return {
            side,
            sideFactor: side === "left" ? -1 : 1,
            handBone,
            fingers,
            basis: null,
            axisProfile: {},
        };
    }

    detectHandBasis(hand) {
        const THREE = window.THREE;
        if (!hand || !hand.handBone || !THREE) return null;
        const indexBase = getBoneWorldPosition(hand.fingers.index && hand.fingers.index.bones[0]);
        const pinkyBase = getBoneWorldPosition(hand.fingers.pinky && hand.fingers.pinky.bones[0]);
        const handPos = getBoneWorldPosition(hand.handBone);
        const across = indexBase && pinkyBase
            ? pinkyBase.clone().sub(indexBase).normalize()
            : new THREE.Vector3(hand.side === "left" ? -1 : 1, 0, 0);
        const forward = averageVectors(
            ["index", "middle", "ring"].map((fingerName) => {
                const finger = hand.fingers[fingerName];
                const base = getBoneWorldPosition(finger && finger.bones[0]);
                const next = getBoneWorldPosition(finger && (finger.bones[1] || finger.bones[0]));
                if (base && next && next.distanceToSquared(base) > 0.000001) return next.sub(base);
                if (base && handPos) return base.sub(handPos);
                return null;
            })
        ) || new THREE.Vector3(0, 1, 0);
        let normal = across.clone().cross(forward);
        if (normal.lengthSq() < 0.000001) {
            normal = new THREE.Vector3(0, 0, hand.side === "left" ? -1 : 1);
        } else {
            normal.normalize();
        }
        return { across, forward, normal };
    }

    buildFingerAxisProfile(hand, fingerName) {
        const finger = hand && hand.fingers ? hand.fingers[fingerName] : null;
        if (!finger || !Array.isArray(finger.bones) || !finger.bones.length || !hand.basis) return null;
        const rootPos = getBoneWorldPosition(finger.bones[0]);
        const nextPos = getBoneWorldPosition(finger.bones[1] || finger.bones[0]);
        let forward = rootPos && nextPos && nextPos.distanceToSquared(rootPos) > 0.000001
            ? nextPos.clone().sub(rootPos).normalize()
            : hand.basis.forward.clone();
        let bend = forward.clone().cross(hand.basis.normal);
        if (bend.lengthSq() < 0.000001) bend = hand.basis.across.clone();
        else bend.normalize();
        return {
            bend: findBestLocalAxisForWorldVector(finger.bones[0], bend),
            spread: findBestLocalAxisForWorldVector(finger.bones[0], hand.basis.normal),
            twist: findBestLocalAxisForWorldVector(finger.bones[0], forward),
            segments: finger.bones.map((bone) => ({
                bend: findBestLocalAxisForWorldVector(bone, bend),
            })),
        };
    }

    buildHandAxisProfile(hand) {
        if (!hand) return null;
        hand.basis = this.detectHandBasis(hand);
        hand.axisProfile = {};
        for (const fingerName of HAND_FINGER_NAMES) {
            hand.axisProfile[fingerName] = this.buildFingerAxisProfile(hand, fingerName);
        }
        return hand;
    }

    supportsGestureHands() {
        return ["left", "right"].every((side) => {
            const hand = this.handRig[side];
            return hand && hand.handBone && HAND_FINGER_NAMES.every((fingerName) => {
                const finger = hand.fingers[fingerName];
                const profile = hand.axisProfile[fingerName];
                return finger && Array.isArray(finger.bones) && finger.bones.length >= 3 && profile && profile.bend;
            });
        });
    }

    detectRigBones() {
        this.bones = {
            torso: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.torso),
            head: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.head),
            leftShoulder: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.leftShoulder),
            rightShoulder: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.rightShoulder),
            leftElbow: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.leftElbow),
            rightElbow: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.rightElbow),
            leftWrist: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.leftWrist),
            rightWrist: findFirstBoneByHints(this.modelRoot, MAKEHUMAN_BONE_HINTS.rightWrist),
        };
        if (this.modelRoot) this.modelRoot.updateMatrixWorld(true);
        this.handRig.left = this.buildHandAxisProfile(this.detectHandRig("left"));
        this.handRig.right = this.buildHandAxisProfile(this.detectHandRig("right"));
        this.captureRestRotations();
    }

    normalizeModelTransform() {
        const THREE = window.THREE;
        if (!this.modelRoot || !THREE) return;
        const box = new THREE.Box3().setFromObject(this.modelRoot);
        const size = new THREE.Vector3();
        const center = new THREE.Vector3();
        box.getSize(size);
        box.getCenter(center);

        if (size.y > 0.001) {
            this.baseModelScale = clamp(3.05 / size.y, 0.45, 2.2);
            this.modelRoot.scale.setScalar(this.baseModelScale);
            box.setFromObject(this.modelRoot);
            box.getCenter(center);
        }

        this.modelRoot.position.x -= center.x;
        this.modelRoot.position.z -= center.z;

        box.setFromObject(this.modelRoot);
        this.baseModelY = -box.min.y - 1.58;
        this.baseGroundOffset = this.baseModelY + 1.58;
        this.currentModelY = this.baseModelY;
        this.modelRoot.position.y = this.baseModelY;
    }

    applyBoneRotation(name, xyz, weight = 1) {
        const THREE = window.THREE;
        const bone = this.bones[name];
        if (!bone || !Array.isArray(xyz) || xyz.length !== 3 || !THREE) return;
        const q = new THREE.Quaternion().setFromEuler(
            new THREE.Euler(xyz[0] * weight, xyz[1] * weight, xyz[2] * weight, "XYZ")
        );
        bone.quaternion.multiply(q);
    }

    applyLocalAxisRotation(bone, axisMeta, radians) {
        const THREE = window.THREE;
        if (!bone || !axisMeta || !axisMeta.axis || !THREE || Math.abs(Number(radians || 0)) < 0.000001) return;
        const axis = axisMeta.axis === "x"
            ? new THREE.Vector3(1, 0, 0)
            : axisMeta.axis === "y"
                ? new THREE.Vector3(0, 1, 0)
                : new THREE.Vector3(0, 0, 1);
        const q = new THREE.Quaternion().setFromAxisAngle(axis, radians * Number(axisMeta.sign || 1));
        bone.quaternion.multiply(q);
    }

    applyFingerPose(hand, fingerName, pose) {
        const finger = hand && hand.fingers ? hand.fingers[fingerName] : null;
        const profile = hand && hand.axisProfile ? hand.axisProfile[fingerName] : null;
        if (!finger || !profile || !Array.isArray(finger.bones) || !finger.bones.length) return;
        const curl = Array.isArray(pose && pose.curl)
            ? pose.curl.map((value) => Number(value || 0))
            : [Number((pose && pose.curl) || 0)];
        const rootCurl = Number(curl[0] || 0);
        const middleCurl = Number(curl[1] !== undefined ? curl[1] : rootCurl * 0.82);
        const tipCurl = Number(curl[2] !== undefined ? curl[2] : middleCurl * 0.85);
        const isThumb = fingerName === "thumb";
        const rootBend = rootCurl * (isThumb ? 0.62 : 0.74) + Number((pose && pose.pitch) || 0) * (isThumb ? 0.9 : 0.7);
        const spread = Number((pose && pose.spread) || 0) * (isThumb ? 1.15 : 0.92);
        const twist = (Number((pose && pose.yaw) || 0) + Number((pose && pose.twist) || 0)) * (isThumb ? 1.0 : 0.7);

        this.applyLocalAxisRotation(finger.bones[0], profile.bend, rootBend);
        this.applyLocalAxisRotation(finger.bones[0], profile.spread, spread);
        this.applyLocalAxisRotation(finger.bones[0], profile.twist, twist);

        const segmentAngles = [rootCurl * 0.22, middleCurl, tipCurl, tipCurl * 0.7];
        for (let index = 1; index < finger.bones.length; index += 1) {
            const amount = Number(segmentAngles[index] || tipCurl);
            const segmentMeta = profile.segments[index] && profile.segments[index].bend
                ? profile.segments[index].bend
                : profile.bend;
            this.applyLocalAxisRotation(finger.bones[index], segmentMeta, amount);
        }
    }

    applyHandPresets() {
        for (const side of ["left", "right"]) {
            const hand = this.handRig[side];
            if (!hand) continue;
            const preset = resolveHandPreset(this.currentHandPresets[side], hand.sideFactor);
            for (const fingerName of HAND_FINGER_NAMES) {
                this.applyFingerPose(hand, fingerName, preset[fingerName] || {});
            }
        }
    }

    setGestureHands(gesture) {
        const presets = getGestureHandPresets(gesture);
        this.currentHandPresets.left = presets.left;
        this.currentHandPresets.right = presets.right;
    }

    applyPose(pose) {
        if (!this.modelRoot) return;
        this.resetToRestRotations();
        this.applyBoneRotation("torso", pose.torso, 0.36);
        this.applyBoneRotation("head", pose.head, 0.88);
        this.applyBoneRotation("leftShoulder", pose.lS, 1.0);
        this.applyBoneRotation("rightShoulder", pose.rS, 1.0);
        this.applyBoneRotation("leftElbow", pose.lE, 1.0);
        this.applyBoneRotation("rightElbow", pose.rE, 1.0);
        this.applyBoneRotation("leftWrist", pose.lW, 0.95);
        this.applyBoneRotation("rightWrist", pose.rW, 0.95);
        this.applyHandPresets();
        this.currentPose = clonePose(pose);
    }

    beforeRenderFrame(_delta, _elapsedTime) {}

    async init() {
        if (this.ready || !this.container) return;
        if (!window.THREE) throw new Error("Three.js unavailable");
        if (!window.THREE.GLTFLoader) throw new Error("GLTFLoader unavailable");
        if (!this.isWebGLAvailable()) throw new Error("WebGL unavailable");

        const THREE = window.THREE;

        this.container.innerHTML = "";
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0b1220);
        this.scene.fog = new THREE.Fog(0x0b1220, 6, 15);
        this.clock = new THREE.Clock();

        const w = Math.max(this.container.clientWidth, 260);
        const h = Math.max(this.container.clientHeight, 260);
        this.camera = new THREE.PerspectiveCamera(30, w / h, 0.1, 50);
        this.camera.position.set(0, 0.68, 3.2);
        this.camera.lookAt(0, 0.18, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
        this.renderer.setSize(w, h, false);
        if ("outputColorSpace" in this.renderer && THREE.SRGBColorSpace) {
            this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        }
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.className = "sign-avatar-canvas";
        this.container.appendChild(this.renderer.domElement);

        const hemi = new THREE.HemisphereLight(0xfffaf3, 0x111827, 0.85);
        const key = new THREE.DirectionalLight(0xffffff, 1.4);
        key.position.set(2.5, 5.0, 3.5);
        key.castShadow = true;
        key.shadow.mapSize.set(2048, 2048);
        key.shadow.camera.near = 0.5;
        key.shadow.camera.far = 15;
        key.shadow.bias = -0.0005;

        const fill = new THREE.DirectionalLight(0x6366f1, 0.85); // Indigo fill
        fill.position.set(-3.0, 2.5, 2.0);

        const rim = new THREE.DirectionalLight(0xec4899, 1.0); // Pink rim
        rim.position.set(-2.5, 3.0, -3.0);

        const rim2 = new THREE.DirectionalLight(0x8b5cf6, 0.8); // Purple back rim
        rim2.position.set(2.5, 2.0, -3.0);

        this.scene.add(hemi, key, fill, rim, rim2);

        const stage = new THREE.Mesh(
            new THREE.CylinderGeometry(1.9, 2.1, 0.18, 42),
            new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.2, metalness: 0.8 })
        );
        stage.position.y = -1.66;
        stage.receiveShadow = true;
        this.scene.add(stage);

        const halo = new THREE.Mesh(
            new THREE.TorusGeometry(1.2, 0.04, 16, 100),
            new THREE.MeshStandardMaterial({ color: 0xec4899, emissive: 0xdb2777, roughness: 0.2, metalness: 0.8, emissiveIntensity: 2.5 })
        );
        halo.rotation.x = -Math.PI / 2;
        halo.position.y = -1.56;
        this.scene.add(halo);

        const loader = new THREE.GLTFLoader();
        const gltf = await new Promise((resolve, reject) => {
            loader.load(this.modelUrl, resolve, undefined, reject);
        });
        this.modelRoot = (gltf && (gltf.scene || (Array.isArray(gltf.scenes) ? gltf.scenes[0] : null))) || null;
        if (!this.modelRoot) throw new Error("Invalid MakeHuman model scene");

        this.modelRoot.traverse((node) => {
            if (node.isMesh) {
                node.castShadow = true;
                node.receiveShadow = true;
            }
        });

        this.scene.add(this.modelRoot);
        this.normalizeModelTransform();
        this.detectRigBones();
        this.setGestureHands("relaxed");
        this.applyPose(HAND_PREVIEW_POSE);

        const resize = () => {
            this.fitToContainer({ reason: "resize" });
        };

        if (typeof ResizeObserver !== "undefined") {
            this.resizeObserver = new ResizeObserver(() => resize());
            this.resizeObserver.observe(this.container);
        } else {
            this.windowResizeHandler = () => resize();
            window.addEventListener("resize", this.windowResizeHandler);
        }
        this.fitToContainer({ reason: "init" });

        const render = () => {
            if (!this.renderer || !this.scene || !this.camera || !this.modelRoot) return;
            const delta = this.clock.getDelta();
            const t = this.clock.elapsedTime;
            this.beforeRenderFrame(delta, t);
            this.modelRoot.rotation.y = Math.sin(t * 0.35) * 0.05;
            this.modelRoot.position.y = this.currentModelY + Math.sin(t * 1.5) * 0.02;
            this.renderer.render(this.scene, this.camera);
            window.requestAnimationFrame(render);
        };
        render();

        this.ready = true;
    }

    pose(overrides) {
        return mergePose(BASE_POSE, overrides);
    }

    async tween(target, duration, runToken) {
        const to = mergePose(BASE_POSE, target);
        const from = clonePose(this.currentPose);
        return new Promise((resolve) => {
            const start = performance.now();
            const step = (now) => {
                if (this.runToken !== runToken) return resolve(false);
                const t = Math.min((now - start) / Math.max(duration, 1), 1);
                this.applyPose(lerpPose(from, to, easeInOut(t)));
                if (t < 1) return window.requestAnimationFrame(step);
                this.applyPose(to);
                resolve(true);
            };
            window.requestAnimationFrame(step);
        });
    }

    gestureFrames(token) {
        return buildGestureFramesForToken(token, (overrides) => this.pose(overrides));
    }

    async showProcessing(runToken) {
        this.runToken = runToken;
        this.setGestureHands("open");
        await this.tween(this.pose({ lS: [-0.34, 0, 0.44], rS: [-0.34, 0, -0.44], lE: [-0.88, 0, 0], rE: [-0.88, 0, 0] }), 180, runToken);
    }

    async showIdle(runToken) {
        this.runToken = runToken;
        this.setGestureHands("relaxed");
        await this.tween(HAND_PREVIEW_POSE, 200, runToken);
    }

    async play(tokens, runToken) {
        this.runToken = runToken;
        this.setGestureHands("relaxed");
        await this.tween(HAND_PREVIEW_POSE, 120, runToken);
        for (const token of tokens) {
            if (this.runToken !== runToken) return false;
            this.setGestureHands(token.gesture || "");
            const frames = this.gestureFrames(token);
            for (const frame of frames) {
                const ok = await this.tween(frame, token.gesture === "fingerspell" ? 140 : 210, runToken);
                if (!ok) return false;
            }
        }
        this.setGestureHands("relaxed");
        await this.tween(HAND_PREVIEW_POSE, 220, runToken);
        return true;
    }
}

class MocapEnhancedMakeHumanAvatar3D extends MakeHumanAvatar3D {
    constructor(container) {
        super(container);
        this.fbxLoader = null;
        this.clipMixer = null;
        this.clipManifest = null;
        this.clipCache = new Map();
        this.activeClipAction = null;
        this.lowerBodyClipPlane = null;
    }

    fitToContainer(options = {}) {
        const fitted = super.fitToContainer(options);
        if (!fitted || !this.camera) return fitted;
        const width = Math.max(this.container ? this.container.clientWidth : 1, 1);
        const height = Math.max(this.container ? this.container.clientHeight : 1, 1);
        const aspect = width / Math.max(height, 1);
        const shortEdge = Math.min(width, height);
        const shortfall = clamp((380 - shortEdge) / 380, 0, 1);
        this.camera.position.set(0, clamp(0.9 - shortfall * 0.04, 0.82, 0.98), clamp(2.5 + shortfall * 0.22 + Math.max(0, 1 - aspect) * 0.2, 2.34, 2.96));
        this.camera.fov = clamp(25 + shortfall * 4 + Math.max(0, 1 - aspect) * 3, 25, 33);
        this.camera.lookAt(0, 0.48, 0);
        this.camera.updateProjectionMatrix();
        return true;
    }

    applyHandFocusStyling() {
        const THREE = window.THREE;
        if (!this.modelRoot || !this.renderer || !THREE) return;
        this.renderer.localClippingEnabled = true;
        this.lowerBodyClipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0.34);
        this.modelRoot.traverse((node) => {
            if (!node || !node.isMesh) return;
            const materials = Array.isArray(node.material) ? node.material : [node.material];
            materials.filter(Boolean).forEach((material) => {
                if ("roughness" in material) material.roughness = Math.max(Number(material.roughness || 0), 0.72);
                if ("metalness" in material) material.metalness = Math.min(Number(material.metalness || 0), 0.08);
                material.clippingPlanes = [this.lowerBodyClipPlane];
                material.clipShadows = true;
                material.needsUpdate = true;
            });
        });
    }

    async init() {
        await super.init();
        if (!window.THREE || !window.THREE.FBXLoader) {
            throw new Error("FBXLoader unavailable");
        }
        this.fbxLoader = new window.THREE.FBXLoader();
        this.clipMixer = new window.THREE.AnimationMixer(this.modelRoot);
        this.clipManifest = await this.loadClipManifest();
        this.applyHandFocusStyling();
        this.fitToContainer({ reason: "mocap init" });
    }

    async loadClipManifest() {
        const response = await fetch(MOCAP_MANIFEST_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Mocap manifest unavailable (${response.status})`);
        }
        const manifest = await response.json();
        if (!manifest || typeof manifest !== "object") {
            throw new Error("Invalid mocap manifest payload");
        }
        return manifest;
    }

    supportsMocapClips() {
        const words = this.clipManifest && this.clipManifest.words;
        const letters = this.clipManifest && this.clipManifest.letters;
        return Boolean(words && letters && Object.keys(words).length && Object.keys(letters).length);
    }

    beforeRenderFrame(delta) {
        if (this.clipMixer) this.clipMixer.update(delta);
    }

    stopActiveClip() {
        if (!this.activeClipAction) return;
        try {
            this.activeClipAction.stop();
        } catch (error) {
            console.warn("[Avatar] Failed to stop active clip cleanly", error);
        }
        this.activeClipAction = null;
    }

    async showProcessing(runToken) {
        this.stopActiveClip();
        return super.showProcessing(runToken);
    }

    async showIdle(runToken) {
        this.stopActiveClip();
        return super.showIdle(runToken);
    }

    getWordClipUrl(word) {
        const key = normalizeClipKey(word);
        const words = this.clipManifest && this.clipManifest.words ? this.clipManifest.words : {};
        return words[key] || null;
    }

    getLetterClipUrl(letter) {
        const letters = this.clipManifest && this.clipManifest.letters ? this.clipManifest.letters : {};
        return letters[String(letter || "").trim().toUpperCase()] || null;
    }

    buildClipPlan(token) {
        if (!token) return [];
        const directWordClip = this.getWordClipUrl(token.word);
        if (directWordClip) {
            return [{ kind: "word", label: token.word, url: directWordClip }];
        }
        if (token.gesture !== "fingerspell") return [];
        const chars = (Array.isArray(token.chars) && token.chars.length
            ? token.chars
            : String(token.word || "").toUpperCase().split(""))
            .map((char) => String(char || "").trim().toUpperCase())
            .filter((char) => /^[A-Z]$/.test(char));
        if (!chars.length) return [];
        const plan = [];
        for (const char of chars) {
            const url = this.getLetterClipUrl(char);
            if (!url) return [];
            plan.push({ kind: "letter", label: char, url });
        }
        return plan;
    }

    async loadAnimationClip(url) {
        if (this.clipCache.has(url)) return this.clipCache.get(url);
        const object = await new Promise((resolve, reject) => {
            this.fbxLoader.load(url, resolve, undefined, reject);
        });
        const clip = (object && Array.isArray(object.animations) && object.animations[0]) || null;
        if (!clip) {
            throw new Error(`No animation clip found in ${url}`);
        }
        this.clipCache.set(url, clip);
        return clip;
    }

    async playMocapClip(url, runToken) {
        if (!this.clipMixer || !this.modelRoot) return false;
        if (this.runToken !== runToken) return false;
        const THREE = window.THREE;
        const clip = await this.loadAnimationClip(url);
        if (this.runToken !== runToken) return false;
        this.stopActiveClip();

        return new Promise((resolve) => {
            let settled = false;
            const finish = (ok) => {
                if (settled) return;
                settled = true;
                window.clearTimeout(timeoutId);
                this.clipMixer.removeEventListener("finished", handleFinished);
                if (this.activeClipAction === action) this.activeClipAction = null;
                try {
                    action.stop();
                } catch (error) {
                    console.warn("[Avatar] Failed to stop finished clip cleanly", error);
                }
                resolve(Boolean(ok) && this.runToken === runToken);
            };

            const action = this.clipMixer.clipAction(clip, this.modelRoot);
            const handleFinished = (event) => {
                if (!event || event.action !== action) return;
                finish(true);
            };

            this.clipMixer.addEventListener("finished", handleFinished);
            action.reset();
            action.enabled = true;
            action.clampWhenFinished = true;
            action.setLoop(THREE.LoopOnce, 1);
            this.activeClipAction = action;
            action.play();

            const timeoutId = window.setTimeout(
                () => finish(true),
                Math.max(240, Math.round((Number(clip.duration || 0.9) + 0.06) * 1000))
            );
        });
    }

    async playProceduralToken(token, runToken) {
        this.setGestureHands(token.gesture || "");
        const frames = this.gestureFrames(token);
        for (const frame of frames) {
            const ok = await this.tween(frame, token.gesture === "fingerspell" ? 140 : 210, runToken);
            if (!ok) return false;
        }
        return true;
    }

    async play(tokens, runToken) {
        this.runToken = runToken;
        this.stopActiveClip();
        this.setGestureHands("relaxed");
        await this.tween(HAND_PREVIEW_POSE, 120, runToken);
        for (const token of tokens) {
            if (this.runToken !== runToken) return false;
            const plan = this.buildClipPlan(token);
            if (plan.length) {
                try {
                    this.setGestureHands("relaxed");
                    this.applyPose(HAND_PREVIEW_POSE);
                    for (const step of plan) {
                        const ok = await this.playMocapClip(step.url, runToken);
                        if (!ok) return false;
                    }
                    this.applyPose(HAND_PREVIEW_POSE);
                    continue;
                } catch (error) {
                    console.warn(`[Avatar] Mocap clip failed for "${token.word}". Falling back to procedural motion.`, error);
                }
            }
            const ok = await this.playProceduralToken(token, runToken);
            if (!ok) return false;
        }
        this.stopActiveClip();
        this.setGestureHands("relaxed");
        await this.tween(HAND_PREVIEW_POSE, 220, runToken);
        return true;
    }
}

class MocapArchiveAvatar3D extends MocapEnhancedMakeHumanAvatar3D {
    constructor(container) {
        super(container);
        this.modelUrl = MOCAP_ARCHIVE_MODEL_URL;
        this.lowerBodyClipPlane = null;
    }

    fitToContainer(options = {}) {
        const fitted = super.fitToContainer(options);
        if (!fitted || !this.camera) return fitted;
        const width = Math.max(this.container ? this.container.clientWidth : 1, 1);
        const height = Math.max(this.container ? this.container.clientHeight : 1, 1);
        const aspect = width / Math.max(height, 1);
        const shortEdge = Math.min(width, height);
        const shortfall = clamp((380 - shortEdge) / 380, 0, 1);
        this.camera.position.set(0, clamp(0.92 - shortfall * 0.04, 0.84, 1.0), clamp(2.45 + shortfall * 0.18 + Math.max(0, 1 - aspect) * 0.18, 2.3, 2.88));
        this.camera.fov = clamp(24 + shortfall * 3 + Math.max(0, 1 - aspect) * 3, 24, 31);
        this.camera.lookAt(0, 0.52, 0);
        this.camera.updateProjectionMatrix();
        if (this.modelRoot) {
            const scale = clamp(this.baseModelScale * (1.18 - shortfall * 0.04), this.baseModelScale * 1.08, this.baseModelScale * 1.24);
            this.modelRoot.scale.setScalar(scale);
            const ratio = scale / Math.max(this.baseModelScale, 0.0001);
            this.currentModelY = -1.92 + this.baseGroundOffset * ratio;
            this.modelRoot.position.y = this.currentModelY;
        }
        return true;
    }

    styleArchiveMaterials() {
        const THREE = window.THREE;
        if (!this.modelRoot || !THREE) return;
        this.lowerBodyClipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0.58);
        this.modelRoot.traverse((node) => {
            if (!node || !node.isMesh) return;
            node.castShadow = true;
            node.receiveShadow = true;
            const materials = Array.isArray(node.material) ? node.material : [node.material];
            materials.filter(Boolean).forEach((material) => {
                if ("roughness" in material) material.roughness = Math.max(Number(material.roughness || 0), 0.74);
                if ("metalness" in material) material.metalness = Math.min(Number(material.metalness || 0), 0.08);
                material.clippingPlanes = [this.lowerBodyClipPlane];
                material.clipShadows = true;
                material.needsUpdate = true;
            });
        });
    }

    async init() {
        if (this.ready || !this.container) return;
        if (!window.THREE) throw new Error("Three.js unavailable");
        if (!window.THREE.FBXLoader) throw new Error("FBXLoader unavailable");
        if (!this.isWebGLAvailable()) throw new Error("WebGL unavailable");

        const THREE = window.THREE;

        this.container.innerHTML = "";
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x08111b);
        this.scene.fog = new THREE.Fog(0x08111b, 4.6, 12.5);
        this.clock = new THREE.Clock();

        const w = Math.max(this.container.clientWidth, 260);
        const h = Math.max(this.container.clientHeight, 260);
        this.camera = new THREE.PerspectiveCamera(26, w / h, 0.1, 50);
        this.camera.position.set(0, 0.92, 2.54);
        this.camera.lookAt(0, 0.52, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
        this.renderer.setSize(w, h, false);
        this.renderer.localClippingEnabled = true;
        if ("outputColorSpace" in this.renderer && THREE.SRGBColorSpace) {
            this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        }
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.02;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.className = "sign-avatar-canvas";
        this.container.appendChild(this.renderer.domElement);

        const hemi = new THREE.HemisphereLight(0xf8fafc, 0x0f172a, 0.96);
        const key = new THREE.DirectionalLight(0xffffff, 1.38);
        key.position.set(2.1, 4.4, 3.2);
        key.castShadow = true;
        key.shadow.mapSize.set(2048, 2048);
        key.shadow.camera.near = 0.5;
        key.shadow.camera.far = 15;
        key.shadow.bias = -0.0005;

        const fill = new THREE.DirectionalLight(0x7dd3fc, 0.9);
        fill.position.set(-2.4, 2.4, 2.4);

        const rim = new THREE.DirectionalLight(0x93c5fd, 0.95);
        rim.position.set(-2.2, 2.8, -2.4);

        this.scene.add(hemi, key, fill, rim);

        const stage = new THREE.Mesh(
            new THREE.CylinderGeometry(1.7, 1.9, 0.14, 42),
            new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.35, metalness: 0.22 })
        );
        stage.position.y = -1.78;
        stage.receiveShadow = true;
        this.scene.add(stage);

        const loader = new THREE.FBXLoader();
        const fbx = await new Promise((resolve, reject) => {
            loader.load(this.modelUrl, resolve, undefined, reject);
        });
        this.modelRoot = fbx || null;
        if (!this.modelRoot) throw new Error("Invalid mocap archive model");

        this.styleArchiveMaterials();
        this.scene.add(this.modelRoot);
        this.normalizeModelTransform();
        this.detectRigBones();
        this.setGestureHands("relaxed");
        this.applyPose(HAND_PREVIEW_POSE);

        this.fbxLoader = loader;
        this.clipMixer = new THREE.AnimationMixer(this.modelRoot);
        this.clipManifest = await this.loadClipManifest();

        const resize = () => {
            this.fitToContainer({ reason: "resize" });
        };

        if (typeof ResizeObserver !== "undefined") {
            this.resizeObserver = new ResizeObserver(() => resize());
            this.resizeObserver.observe(this.container);
        } else {
            this.windowResizeHandler = () => resize();
            window.addEventListener("resize", this.windowResizeHandler);
        }
        this.fitToContainer({ reason: "init" });

        const render = () => {
            if (!this.renderer || !this.scene || !this.camera || !this.modelRoot) return;
            const delta = this.clock.getDelta();
            const t = this.clock.elapsedTime;
            this.beforeRenderFrame(delta, t);
            this.modelRoot.rotation.y = Math.sin(t * 0.22) * 0.03;
            this.modelRoot.position.y = this.currentModelY + Math.sin(t * 1.2) * 0.012;
            this.renderer.render(this.scene, this.camera);
            window.requestAnimationFrame(render);
        };
        render();

        this.ready = true;
    }
}

function getAvatarEnginePreference(container) {
    const fromDataset = container && container.dataset ? String(container.dataset.avatarEngine || "").trim().toLowerCase() : "";
    if (fromDataset) return fromDataset;
    try {
        const fromStorage = String(window.localStorage.getItem("sam_avatar_engine") || "").trim().toLowerCase();
        if (fromStorage) return fromStorage;
    } catch (error) {
        // Ignore localStorage access failures.
    }
    return "auto";
}

async function createAvatarRenderer(container) {
    const preference = getAvatarEnginePreference(container);
    const skipMakeHuman = preference === "procedural";
    if (!skipMakeHuman && window.THREE) {
        if (window.THREE.FBXLoader) {
            const mocapEnhanced = new MocapEnhancedMakeHumanAvatar3D(container);
            try {
                await mocapEnhanced.init();
                if (preference === "auto" && !mocapEnhanced.supportsGestureHands()) {
                    throw new Error("MakeHuman hand rig incomplete for sign animation");
                }
                if (mocapEnhanced.supportsMocapClips()) {
                    return { avatar: mocapEnhanced, engine: "makehuman_mocap" };
                }
            } catch (error) {
                console.warn("[Avatar] Mocap-enhanced MakeHuman load failed. Falling back to hand-rig avatar.", error);
            }
        }
        if (window.THREE.GLTFLoader) {
            const makeHuman = new MakeHumanAvatar3D(container);
            try {
                await makeHuman.init();
                if (preference === "auto" && !makeHuman.supportsGestureHands()) {
                    throw new Error("MakeHuman hand rig incomplete for sign animation");
                }
                return { avatar: makeHuman, engine: "makehuman" };
            } catch (error) {
                console.warn("[Avatar] MakeHuman model load failed. Falling back to procedural avatar.", error);
            }
        }
    }
    const procedural = new Avatar3D(container);
    await procedural.init();
    return { avatar: procedural, engine: "procedural" };
}

document.addEventListener("DOMContentLoaded", async () => {
    const DOM = {
        startBtn: document.getElementById("speechBtn"),
        stopBtn: document.getElementById("stop-live-btn"),
        waveformBox: document.getElementById("waveform-box"),
        status: document.getElementById("partial-status"),
        transcriptText: document.getElementById("transcript-text"),
        interimText: document.getElementById("interim-text"),
        avatarArea: document.getElementById("avatarOutput"),
        replayBtn: document.getElementById("replay-btn"),
        signOutput: document.getElementById("signOutput"),
        toggleUpload: document.getElementById("toggle-upload"),
        uploadArea: document.getElementById("upload-area"),
        uploadBtn: document.getElementById("uploadBtn"),
        audioInput: document.getElementById("audioUpload"),
        sourceMeta: document.getElementById("source-meta"),
        inputLang: document.getElementById("speechInputLang"),
        signLang: document.getElementById("signOutputLang"),
        avatarEngineIndicator: document.getElementById("avatar-engine-indicator"),
    };

    const STATE = {
        recognition: null,
        listening: false,
        runToken: 0,
        lastTokens: [],
        avatarReady: false,
        avatarEngine: "none",
        lastFinalText: "",
        lastFinalAt: 0,
        liveInterimTimer: null,
        lastInterimSentText: "",
        lastInterimSentAt: 0,
        lastDisplayedInterimText: "",
        requestSeq: 0,
        latestFinalSeq: 0,
        latestPartialSeq: 0,
        avatarInitPromise: null,
        avatarWarmupQueued: false,
    };

    let avatar = null;

    function setStatus(message, tone) {
        if (!DOM.status) return;
        DOM.status.innerText = message;
        if (tone === "error") DOM.status.style.color = "#ef4444";
        else if (tone === "success") DOM.status.style.color = "#4ade80";
        else DOM.status.style.color = "";
    }

    function hasAuthenticatedSession() {
        return Boolean(document.body && document.body.dataset && document.body.dataset.authenticated === "true");
    }

    async function ensureAvatarVendorLibraries(container) {
        const urls = getAvatarLibraryUrls(container);
        if (!window.THREE) {
            if (!urls.three) return false;
            await loadScriptOnce(urls.three);
        }
        if (!window.THREE || !window.THREE.GLTFLoader) {
            if (!urls.gltf) return false;
            await loadScriptOnce(urls.gltf);
        }
        if (!window.fflate) {
            if (!urls.fflate) return false;
            await loadScriptOnce(urls.fflate);
        }
        if (!window.THREE || !window.THREE.FBXLoader) {
            if (!urls.fbx) return false;
            await loadScriptOnce(urls.fbx);
        }
        return Boolean(window.THREE && window.THREE.GLTFLoader && window.THREE.FBXLoader);
    }

    function setMicUI(active) {
        if (DOM.startBtn) DOM.startBtn.style.display = active ? "none" : "block";
        if (DOM.stopBtn) {
            DOM.stopBtn.style.display = active ? "flex" : "none";
            DOM.stopBtn.disabled = !active;
        }
        if (DOM.waveformBox) DOM.waveformBox.classList.toggle("active", active);
    }

    function updateMeta() {
        if (!DOM.sourceMeta || !DOM.inputLang || !DOM.signLang) return;
        const inputCode = String(DOM.inputLang.value || "en").split("-")[0].toUpperCase();
        DOM.sourceMeta.innerText = `${inputCode} -> ${DOM.signLang.value}`;
    }

    function setSelectValue(select, value) {
        if (!select) return false;
        const candidate = String(value || "").trim().toLowerCase();
        if (!candidate) return false;
        const option = Array.from(select.options || []).find(
            (item) => String(item.value || "").trim().toLowerCase() === candidate
        );
        if (!option) return false;
        select.value = option.value;
        return true;
    }

    async function persistUserPreferences(patch) {
        if (!hasAuthenticatedSession()) return false;
        const payload = {};
        Object.entries(patch || {}).forEach(([key, value]) => {
            if (value == null) return;
            const clean = String(value).trim();
            if (!clean) return;
            payload[key] = clean;
        });
        if (!Object.keys(payload).length) return false;

        try {
            const response = await fetch("/api/user/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (response.status === 401) return false;
            if (!response.ok) throw new Error(`status ${response.status}`);
            return true;
        } catch (error) {
            console.warn("Could not save user preferences", error);
            return false;
        }
    }

    async function loadUserPreferences() {
        if (!hasAuthenticatedSession()) return;
        try {
            const response = await fetch("/api/user/preferences", { cache: "no-store" });
            if (!response.ok) throw new Error(`status ${response.status}`);

            const preferences = await response.json();
            setSelectValue(DOM.inputLang, preferences.speech_input_language);
            setSelectValue(DOM.signLang, preferences.speech_sign_language);
            updateMeta();
        } catch (error) {
            console.warn("User preferences unavailable", error);
        }
    }

    function shouldIgnoreFinal(text) {
        const normalized = String(text || "").trim().toLowerCase();
        if (!normalized) return true;
        const now = Date.now();
        const duplicate = normalized === STATE.lastFinalText && (now - STATE.lastFinalAt) < 1500;
        STATE.lastFinalText = normalized;
        STATE.lastFinalAt = now;
        return duplicate;
    }

    function hasHandAvatarHook() {
        return typeof window.playHandAvatar === "function";
    }

    function hasLegacyAvatarInstance() {
        return Boolean(STATE.avatarReady && avatar);
    }

    async function ensureAvatarReady(options = {}) {
        if (hasHandAvatarHook()) {
            STATE.avatarReady = true;
            STATE.avatarEngine = "hand_avatar";
            if (DOM.avatarEngineIndicator) {
                DOM.avatarEngineIndicator.innerText = "Avatar engine: hand_avatar";
            }
            return true;
        }

        const background = Boolean(options.background);
        if (STATE.avatarReady) {
            return true;
        }
        if (STATE.avatarInitPromise) {
            await STATE.avatarInitPromise;
            return STATE.avatarReady;
        }

        if (DOM.avatarEngineIndicator) {
            DOM.avatarEngineIndicator.innerText = "Avatar engine: loading...";
        }

        STATE.avatarInitPromise = (async () => {
            try {
                if (!(await ensureAvatarVendorLibraries(DOM.avatarArea))) {
                    throw new Error("Local avatar libraries are not available");
                }
                const avatarSetup = await createAvatarRenderer(DOM.avatarArea);
                avatar = avatarSetup.avatar;
                STATE.avatarEngine = avatarSetup.engine;
                STATE.avatarReady = true;
                if (DOM.avatarEngineIndicator) {
                    DOM.avatarEngineIndicator.innerText = `Avatar engine: ${STATE.avatarEngine}`;
                }
                if (DOM.avatarArea) {
                    DOM.avatarArea.classList.remove("speech-avatar-shell-muted");
                }
                avatar.fitToContainer({ reason: "avatar init" });
                await avatar.showIdle(++STATE.runToken);
                if (!background) setStatus("Hand motion preview ready", "success");
                return true;
            } catch (error) {
                console.error(error);
                STATE.avatarReady = false;
                STATE.avatarEngine = "unavailable";
                if (DOM.avatarEngineIndicator) {
                    DOM.avatarEngineIndicator.innerText = "Avatar engine: unavailable";
                }
                if (DOM.avatarArea) {
                    DOM.avatarArea.innerHTML = '<div class="avatar-placeholder"><p>Hand preview unavailable.</p></div>';
                }
                if (DOM.replayBtn) DOM.replayBtn.style.display = "none";
                return false;
            } finally {
                STATE.avatarInitPromise = null;
            }
        })();

        return STATE.avatarInitPromise;
    }

    function warmAvatarNow() {
        if (hasHandAvatarHook()) return;
        if (STATE.avatarReady || STATE.avatarInitPromise) return;
        STATE.avatarWarmupQueued = true;
        ensureAvatarReady({ background: true }).catch((error) => console.error(error));
    }

    async function playAvatarIfVisible(tokens, signText = "") {
        if (!tokens.length) {
            STATE.lastTokens = [];
            if (DOM.replayBtn) DOM.replayBtn.style.display = "none";
            if (STATE.avatarReady && avatar) {
                await avatar.showIdle(++STATE.runToken);
            }
            return;
        }

        if (hasHandAvatarHook()) {
            STATE.lastTokens = tokens;
            if (DOM.replayBtn) DOM.replayBtn.style.display = "inline-block";
            setStatus("Rendering hand signs...");
            await window.playHandAvatar(tokens, signText);
            setStatus("Sign sequence complete", "success");
            return;
        }

        const ready = await ensureAvatarReady();
        if (!ready || !STATE.avatarReady) return;

        STATE.lastTokens = tokens;
        if (DOM.replayBtn) DOM.replayBtn.style.display = "inline-block";

        const token = ++STATE.runToken;
        avatar.fitToContainer({ reason: "avatar playback" });
        setStatus("Rendering 3D signs...");
        const ok = await avatar.play(tokens, token);
        if (ok && token === STATE.runToken) setStatus("Sign sequence complete", "success");
    }

    function clearInterimTimer() {
        if (!STATE.liveInterimTimer) return;
        window.clearTimeout(STATE.liveInterimTimer);
        STATE.liveInterimTimer = null;
    }

    async function processFromResponse(data, fallbackTranscript, options = {}) {
        const partial = Boolean(options.partial);
        const sourceText = String(data.transcribed_text || fallbackTranscript || "").trim();
        const englishText = String(data.english_text || sourceText).trim();
        const signText = String(
            data.sign_text ||
            data.display_text ||
            data.transcribed_text ||
            sourceText ||
            data.english_text
        ).trim();

        if (DOM.transcriptText) {
            if (!partial && sourceText) {
                DOM.transcriptText.innerText = sourceText;
            } else if (!DOM.transcriptText.innerText || DOM.transcriptText.innerText === "Your speech will appear here...") {
                DOM.transcriptText.innerText = sourceText || "No speech detected";
            }
        }

        if (DOM.interimText) {
            if (partial) {
                DOM.interimText.innerText = sourceText || englishText || "";
            } else {
                DOM.interimText.innerText = "";
            }
        }

        if (DOM.signOutput) DOM.signOutput.innerText = signText || "No sign text generated";

        const tokens = getTokens(data);
        if (!tokens.length) {
            if (!partial) {
                STATE.lastTokens = [];
                if (DOM.replayBtn) DOM.replayBtn.style.display = "none";
                if (STATE.avatarReady && avatar) {
                    await avatar.showIdle(++STATE.runToken);
                }
                setStatus("No supported sign motion resolved", "error");
            }
            return;
        }

        await playAvatarIfVisible(tokens, signText);
    }

    async function sendText(text, options = {}) {
        const clean = String(text || "").trim();
        if (!clean) return;

        const partial = Boolean(options.partial);
        const normalized = clean.toLowerCase();
        const now = Date.now();
        const sendSeq = ++STATE.requestSeq;

        if (partial) {
            const duplicateInterim = normalized === STATE.lastInterimSentText && (now - STATE.lastInterimSentAt) < 700;
            if (duplicateInterim) return;
            STATE.lastInterimSentText = normalized;
            STATE.lastInterimSentAt = now;
            STATE.latestPartialSeq = sendSeq;
            setStatus("Listening... translating live", "success");
        } else {
            STATE.latestFinalSeq = sendSeq;
        }

        const token = partial ? STATE.runToken : ++STATE.runToken;
        if (!partial && hasLegacyAvatarInstance()) {
            await avatar.showProcessing(token);
        }
        if (!partial) setStatus("Translating speech...");

        try {
            const response = await fetch("/api/speech-to-sign", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: clean,
                    input_language: DOM.inputLang ? DOM.inputLang.value : "en-IN",
                    sign_language: DOM.signLang ? DOM.signLang.value : "ISL",
                    render_mode: "3d_avatar_only",
                    realtime_mode: partial ? "partial" : "final",
                }),
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || `Request failed (${response.status})`);
            }
            const data = await response.json();
            if (partial) {
                if (sendSeq < STATE.latestPartialSeq || sendSeq < STATE.latestFinalSeq) return;
            } else if (token !== STATE.runToken || sendSeq < STATE.latestFinalSeq) {
                return;
            }
            await processFromResponse(data, clean, { partial });
        } catch (error) {
            console.error(error);
            if (partial) {
                setStatus("Live translation interrupted", "error");
                return;
            }
            setStatus(`Server error: ${error.message}`, "error");
            if (hasLegacyAvatarInstance()) {
                await avatar.showIdle(++STATE.runToken);
            }
        }
    }

    async function uploadAudio() {
        if (!DOM.audioInput || !DOM.audioInput.files || !DOM.audioInput.files[0]) {
            alert("Please select an audio file.");
            return;
        }

        warmAvatarNow();

        const formData = new FormData();
        formData.append("audio", DOM.audioInput.files[0]);
        formData.append("input_language", DOM.inputLang ? DOM.inputLang.value : "en-IN");
        formData.append("sign_language", DOM.signLang ? DOM.signLang.value : "ISL");
        formData.append("render_mode", "3d_avatar_only");
        formData.append("realtime_mode", "final");

        const token = ++STATE.runToken;
        if (hasLegacyAvatarInstance()) await avatar.showProcessing(token);
        setStatus("Transcribing uploaded audio...");

        try {
            const response = await fetch("/api/speech-to-sign", { method: "POST", body: formData });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || `Upload failed (${response.status})`);
            }
            const data = await response.json();
            if (token !== STATE.runToken) return;
            await processFromResponse(data, "");
        } catch (error) {
            console.error(error);
            setStatus(`Upload failed: ${error.message}`, "error");
            if (hasLegacyAvatarInstance()) {
                await avatar.showIdle(++STATE.runToken);
            }
        }
    }

    function setupRecognition() {
        if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
            setStatus("Browser does not support SpeechRecognition API", "error");
            if (DOM.startBtn) DOM.startBtn.disabled = true;
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        STATE.recognition = new SpeechRecognition();
        STATE.recognition.continuous = true;
        STATE.recognition.interimResults = true;

        STATE.recognition.onstart = () => setStatus("Listening... speak now", "success");

        STATE.recognition.onend = () => {
            if (!STATE.listening) return;
            window.setTimeout(() => {
                if (!STATE.listening || !STATE.recognition) return;
                try {
                    STATE.recognition.start();
                } catch (error) {
                    console.error(error);
                    STATE.listening = false;
                    setMicUI(false);
                    setStatus("Microphone stopped unexpectedly", "error");
                }
            }, 150);
        };

        STATE.recognition.onerror = (event) => {
            console.error(event);
            setStatus(`Microphone error: ${event.error}`, "error");
        };

        STATE.recognition.onresult = (event) => {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const chunk = String(event.results[i][0].transcript || "").trim();
                if (!chunk) continue;
                if (event.results[i].isFinal) {
                    clearInterimTimer();
                    STATE.lastDisplayedInterimText = "";
                    if (!shouldIgnoreFinal(chunk)) sendText(chunk, { partial: false }).catch((err) => console.error(err));
                } else {
                    interim += `${chunk} `;
                }
            }
            const interimText = interim.trim();
            if (DOM.interimText) DOM.interimText.innerText = interimText;
            if (!interimText) return;

            const normalizedInterim = interimText.toLowerCase();
            if (normalizedInterim === STATE.lastDisplayedInterimText) return;
            STATE.lastDisplayedInterimText = normalizedInterim;

            clearInterimTimer();
            STATE.liveInterimTimer = window.setTimeout(() => {
                sendText(interimText, { partial: true }).catch((err) => console.error(err));
            }, 120);
        };
    }

    function startMic() {
        if (!STATE.recognition || STATE.listening) return;
        try {
            warmAvatarNow();
            clearInterimTimer();
            STATE.lastDisplayedInterimText = "";
            STATE.lastInterimSentText = "";
            STATE.lastInterimSentAt = 0;
            STATE.requestSeq = 0;
            STATE.latestPartialSeq = 0;
            STATE.latestFinalSeq = 0;
            STATE.recognition.lang = DOM.inputLang ? DOM.inputLang.value : "en-IN";
            STATE.listening = true;
            setMicUI(true);
            if (DOM.interimText) DOM.interimText.innerText = "";
            STATE.recognition.start();
        } catch (error) {
            console.error(error);
            STATE.listening = false;
            setMicUI(false);
            setStatus("Unable to start microphone", "error");
        }
    }

    function stopMic() {
        STATE.listening = false;
        clearInterimTimer();
        STATE.lastDisplayedInterimText = "";
        STATE.lastInterimSentText = "";
        STATE.lastInterimSentAt = 0;
        STATE.requestSeq = 0;
        STATE.latestPartialSeq = 0;
        STATE.latestFinalSeq = 0;
        if (STATE.recognition) {
            try {
                STATE.recognition.stop();
            } catch (error) {
                console.error(error);
            }
        }
        if (DOM.interimText) DOM.interimText.innerText = "";
        setMicUI(false);
        setStatus("Microphone stopped");
    }

    setupRecognition();
    updateMeta();
    setMicUI(false);
    loadUserPreferences().catch((error) => console.error(error));
    if (DOM.avatarEngineIndicator) {
        DOM.avatarEngineIndicator.innerText = "Avatar engine: on demand";
    }
    setStatus("Ready to listen. Hand motion preview loads on first use.", "success");

    if (DOM.startBtn) DOM.startBtn.addEventListener("click", startMic);
    if (DOM.stopBtn) DOM.stopBtn.addEventListener("click", stopMic);
    if (DOM.inputLang) {
        DOM.inputLang.addEventListener("change", () => {
            updateMeta();
            persistUserPreferences({ speech_input_language: DOM.inputLang.value }).catch((error) => console.error(error));
            if (STATE.listening) {
                stopMic();
                startMic();
            }
        });
    }
    if (DOM.signLang) {
        DOM.signLang.addEventListener("change", () => {
            updateMeta();
            persistUserPreferences({ speech_sign_language: DOM.signLang.value }).catch((error) => console.error(error));
        });
    }

    if (DOM.toggleUpload) {
        DOM.toggleUpload.addEventListener("click", () => {
            if (!DOM.uploadArea) return;
            const hidden = DOM.uploadArea.style.display === "none";
            DOM.uploadArea.style.display = hidden ? "block" : "none";
            DOM.toggleUpload.innerHTML = hidden
                ? '<i class="fas fa-chevron-up"></i> Hide upload'
                : '<i class="fas fa-paperclip"></i> Or upload audio file';
        });
    }
    if (DOM.uploadBtn) DOM.uploadBtn.addEventListener("click", () => uploadAudio().catch((err) => console.error(err)));

    if (DOM.replayBtn) {
        DOM.replayBtn.addEventListener("click", async () => {
            if (!STATE.lastTokens.length) return;
            if (hasHandAvatarHook()) {
                setStatus("Replaying signs...");
                await window.playHandAvatar(STATE.lastTokens, DOM.signOutput ? DOM.signOutput.innerText : "");
                setStatus("Replay complete", "success");
                return;
            }
            const ready = await ensureAvatarReady();
            if (!ready || !STATE.avatarReady) return;
            const token = ++STATE.runToken;
            setStatus("Replaying signs...");
            await avatar.play(STATE.lastTokens, token);
            if (token === STATE.runToken) setStatus("Replay complete", "success");
        });
    }
});
