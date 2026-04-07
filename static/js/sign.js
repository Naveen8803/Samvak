document.addEventListener("DOMContentLoaded", () => {
    const DOM = {
        video: document.getElementById("signVideo"),
        canvas: document.getElementById("overlay"),
        ctx: document.getElementById("overlay") ? document.getElementById("overlay").getContext("2d") : null,
        signBtn: document.getElementById("signBtn"),
        stopBtn: document.getElementById("stop-live-btn"),
        transcriptBox: document.getElementById("signTranscript"),
        translatedBox: document.getElementById("translated-box"),
        partialStatus: document.getElementById("partial-status"),
        sourceMeta: document.getElementById("source-meta"),
        targetMeta: document.getElementById("target-meta"),
        outLangSelect: document.getElementById("outLang"),
        signLangSelect: document.getElementById("signLang"),
        modeAccuracyBtn: document.getElementById("mode-accuracy-btn"),
        modeFallbackBtn: document.getElementById("mode-fallback-btn"),
        modeHelperText: document.getElementById("mode-helper-text"),
        badgeStable: document.getElementById("badge-stable"),
        badgeGuess: document.getElementById("badge-guess"),
        badgeModel: document.getElementById("badge-model"),
        badgeHand: document.getElementById("badge-hand"),
        badgeEngine: document.getElementById("badge-engine"),
        challengeContainer: document.getElementById("challenge-mode-container"),
        challengeTarget: document.getElementById("challenge-target"),
        challengeFeedback: document.getElementById("challenge-feedback"),
        audioBars: document.getElementById("audio-bars"),
        audioContainer: document.querySelector(".audio-player-new"),
        audioOutput: document.getElementById("audio-output"),
        topPredictions: document.getElementById("top-predictions"),
        sessionTranscript: document.getElementById("session-transcript"),
        sessionEnglish: document.getElementById("session-english"),
        sessionSpeakBtn: document.getElementById("session-speak-btn"),
        sessionClearBtn: document.getElementById("session-clear-btn"),
        liveConfidenceValue: document.getElementById("live-confidence-value"),
        liveConfidenceFill: document.getElementById("live-confidence-fill"),
        liveEngineInline: document.getElementById("live-engine-inline"),
        liveEngineText: document.getElementById("live-engine-text"),
        voiceModeNote: document.getElementById("voice-mode-note"),
        supportedSignCount: document.getElementById("supported-sign-count"),
        supportedSignSummary: document.getElementById("supported-sign-summary"),
        supportedSignList: document.getElementById("supported-sign-list"),
        supportedSignCaution: document.getElementById("supported-sign-caution"),
        debugOutput: document.getElementById("sign-debug-output"),
    };

    const STATE = {
        isLive: false,
        outputMode: "Text",
        model: null,
        labels: [],
        labelsReady: false,
        sequenceBuffer: [],
        recentFrameBuffer: [],
        predictionHistory: [],
        stablePrediction: "",
        signChangeCandidate: "",
        signChangeCandidateCount: 0,
        transitionPrimedLabel: "",
        transitionPrimedAt: 0,
        lastTranslatedText: "",
        cameraStream: null,
        cameraInstance: null,
        challengeWord: new URLSearchParams(window.location.search).get("challenge"),
        challengeSolved: false,
        challengeSupported: true,
        inferenceBusy: false,
        fallbackBusy: false,
        lastInferAt: 0,
        lastFallbackAt: 0,
        lastCandidateAt: 0,
        lastStableAt: 0,
        lastHandSeenAt: 0,
        lastNoHandStatusAt: 0,
        handDropFrames: 0,
        runtimeEpoch: 0,
        lastTranslationReqId: 0,
        latestAppliedReqId: 0,
        adaptiveMode: "accuracy",
        backendModelReady: false,
        backendModelLoading: false,
        backendModelError: "",
        backendStatusPollTimer: null,
        lastEngine: "none",
        lastReason: "",
        ttsAnimTimer: null,
        modelRegistry: null,
        schemaManifest: null,
        schemaValidation: null,
        serverSchemaValidation: null,
        modelVersion: "",
        classSetVersion: "",
        thresholdVersion: "",
        featureSchema: "holistic_1662_v1",
        inputFeatureSize: 1662,
        localModelUrl: "/static/models/tfjs_lstm/model.json",
        localEngineEnabled: false,
        localEngineReason: "pending",
        localEngineBackend: "",
        localSelfTest: null,
        classThresholds: {},
        classThresholdDefault: 0.7,
        translationModelReady: false,
        translationModelLoading: false,
        translationMaxFrames: 120,
        translationConfidenceThreshold: 0.45,
        isignRetrievalReady: false,
        isignRetrievalClipCount: 0,
        isignRetrievalUniqueTexts: 0,
        frameCaptureCanvas: null,
        sessionSegments: [],
        lastSessionCommitAt: 0,
        supportedFinalLabels: [],
        cautionLabels: [],
        blockedLabels: [],
        activeAudio: null,
        lastCommittedKey: "",
        lastCommittedAt: 0,
        lastCommittedTranslatedText: "",
        activeCommittedGestureKey: "",
        localDebug: {},
        backendDebug: {},
        runtimeEvents: [],
    };

    const FULL_FEATURE_SIZE = 1662;
    const SEQUENCE_LENGTH = 30;
    const STABLE_HISTORY_SIZE = 4;
    const STABLE_MAJORITY = 3;
    const HIGH_CONFIDENCE_STABLE_MAJORITY = 2;
    const LOCAL_CONFIDENCE_THRESHOLD_ACCURACY = 0.48;
    const LOCAL_CONFIDENCE_THRESHOLD_FALLBACK = 0.32;
    const LOCAL_FAST_COMMIT_EXPERIMENTAL = true;
    const LOCAL_TRUST_BRIDGE_EXPERIMENTAL = true;
    const LOCAL_TRUST_MIN_CONFIDENCE = 0.76;
    const LOCAL_TRUST_MIN_MARGIN = 0.22;
    const LOCAL_MIN_SEQUENCE_FRAMES = 10;
    const LOCAL_PARTIAL_CONFIDENCE_FLOOR = 0.70;
    const LOCAL_PARTIAL_MARGIN_FLOOR = 0.20;
    const SIGN_CHANGE_CONFIRMATIONS = 2;
    const SIGN_CHANGE_SOFT_MIN_CONFIDENCE = 0.50;
    const SIGN_CHANGE_SOFT_MIN_MARGIN = 0.30;
    const SIGN_CHANGE_MIN_CONFIDENCE = 0.68;
    const SIGN_CHANGE_MIN_MARGIN = 0.22;
    const SIGN_CHANGE_REPRIME_FRAMES = 12;
    const SIGN_CHANGE_PRIMED_WINDOW_MS = 1600;
    const TRANSITION_FAST_TRACK_CONFIDENCE = 0.64;
    const TRANSITION_FAST_TRACK_MARGIN = 0.5;
    const TRANSITION_LOCAL_CONFIDENCE_FLOOR = 0.64;
    const TRANSITION_LOCAL_MARGIN_FLOOR = 0.45;
    const RECENT_FRAME_BUFFER_MAX = 16;
    const LOCAL_INFER_INTERVAL_MS = 55;
    const FAST_TRACK_STABILITY_CONFIDENCE = 0.8;
    const BASIC_GEOMETRY_FALLBACK_ENABLED = true;
    const BACKEND_FALLBACK_INTERVAL_MS = 250;
    const TRANSLATION_BACKEND_INTERVAL_MS = 220;
    const DETECTION_IDLE_MS = 2000;
    const REPEAT_SIGN_COOLDOWN_MS = 500;
    const BACKEND_DUPLICATE_SUPPRESSION_MS = 800;
    const HAND_IDLE_MS = 2500;
    const HAND_GRACE_FRAMES = 12;
    const BACKEND_MIN_SEQUENCE_FRAMES = 6;
    const FRAME_CAPTURE_MAX_WIDTH = 300;
    const CAMERA_WIDTH = 640;
    const CAMERA_HEIGHT = 480;
    const POSE_START = 1404;
    const POSE_END = 1536;
    const LEFT_HAND_START = POSE_END;
    const LEFT_HAND_END = LEFT_HAND_START + 63;
    const RIGHT_HAND_START = LEFT_HAND_END;
    const RIGHT_HAND_END = RIGHT_HAND_START + 63;
    const DEFAULT_TFJS_MODEL_URL = "/static/models/tfjs_lstm/model.json";
    const DEFAULT_SCHEMA_MANIFEST_URL = "/static/models/schema_manifest.json";

    const LANG_CODE = {
        english: "EN",
        hindi: "HI",
        telugu: "TE",
        tamil: "TA",
        kannada: "KN",
        malayalam: "ML",
        spanish: "ES",
        french: "FR",
    };

    const TTS_LANG = {
        english: "en-US",
        hindi: "hi-IN",
        telugu: "te-IN",
        tamil: "ta-IN",
        kannada: "kn-IN",
        malayalam: "ml-IN",
        spanish: "es-ES",
        french: "fr-FR",
    };

    function setStatus(message, tone) {
        if (!DOM.partialStatus) return;
        DOM.partialStatus.innerText = message;
        if (tone === "error") DOM.partialStatus.style.color = "#ef4444";
        else if (tone === "success") DOM.partialStatus.style.color = "#4ade80";
        else DOM.partialStatus.style.color = "";
    }

    function hasAuthenticatedSession() {
        return Boolean(document.body && document.body.dataset && document.body.dataset.authenticated === "true");
    }

    function setBadge(el, text, tone = "neutral", visible = true) {
        if (!el) return;

        const palette = {
            neutral: { color: "#94a3b8", bg: "rgba(15, 23, 42, 0.45)", border: "rgba(148, 163, 184, 0.25)" },
            success: { color: "#86efac", bg: "rgba(34, 197, 94, 0.15)", border: "rgba(74, 222, 128, 0.45)" },
            warn: { color: "#fde68a", bg: "rgba(180, 83, 9, 0.22)", border: "rgba(251, 191, 36, 0.35)" },
            danger: { color: "#fecaca", bg: "rgba(239, 68, 68, 0.2)", border: "rgba(248, 113, 113, 0.4)" },
            info: { color: "#bfdbfe", bg: "rgba(37, 99, 235, 0.2)", border: "rgba(96, 165, 250, 0.4)" },
        };
        const style = palette[tone] || palette.neutral;

        el.innerText = text;
        el.style.display = visible ? "inline-flex" : "none";
        el.style.color = style.color;
        el.style.background = style.bg;
        el.style.border = `1px solid ${style.border}`;
    }

    function setModeButtonVisual(button, active, tone = "neutral") {
        if (!button) return;
        if (active) {
            if (tone === "success") {
                button.style.border = "1px solid rgba(74, 222, 128, 0.45)";
                button.style.background = "rgba(34, 197, 94, 0.15)";
                button.style.color = "#86efac";
            } else {
                button.style.border = "1px solid rgba(251, 191, 36, 0.45)";
                button.style.background = "rgba(180, 83, 9, 0.22)";
                button.style.color = "#fde68a";
            }
        } else {
            button.style.border = "1px solid rgba(148, 163, 184, 0.25)";
            button.style.background = "rgba(15, 23, 42, 0.45)";
            button.style.color = "#94a3b8";
        }
    }

    function updateModeUI() {
        const accuracy = STATE.adaptiveMode === "accuracy";
        setModeButtonVisual(DOM.modeAccuracyBtn, accuracy, "success");
        setModeButtonVisual(DOM.modeFallbackBtn, !accuracy, "warn");

        if (DOM.modeHelperText) {
            DOM.modeHelperText.innerText = accuracy
                ? "Accuracy suppresses uncertain guesses. Best for reliability."
                : "Fallback allows best-effort guesses when confidence is low.";
        }
    }

    function setAdaptiveMode(mode, silent = false) {
        STATE.adaptiveMode = mode === "fallback" ? "fallback" : "accuracy";
        updateModeUI();
        if (!silent) {
            setStatus(
                STATE.adaptiveMode === "accuracy"
                    ? "Accuracy mode enabled"
                    : "Fallback mode enabled (guesses allowed)",
                "success"
            );
        }
    }

    function getAllowGeometryFallback() {
        return BASIC_GEOMETRY_FALLBACK_ENABLED || STATE.adaptiveMode === "fallback";
    }

    function getLocalConfidenceThreshold() {
        return STATE.adaptiveMode === "fallback"
            ? LOCAL_CONFIDENCE_THRESHOLD_FALLBACK
            : LOCAL_CONFIDENCE_THRESHOLD_ACCURACY;
    }

    function getBackendMinConfidence({ trustLocalPrediction = false } = {}) {
        if (STATE.adaptiveMode === "fallback") return 0.50;
        return trustLocalPrediction ? 0.82 : 0.62;
    }

    function getBackendSequenceLength() {
        return Math.max(
            SEQUENCE_LENGTH,
            Math.min(Number(STATE.translationMaxFrames || SEQUENCE_LENGTH), 45)
        );
    }

    function getBackendFallbackInterval() {
        return STATE.translationModelReady ? TRANSLATION_BACKEND_INTERVAL_MS : BACKEND_FALLBACK_INTERVAL_MS;
    }

    function shouldCaptureTranslationFrame() {
        return STATE.adaptiveMode === "fallback" || !STATE.translationModelReady || !hasUsableLocalModel();
    }

    function hasUsableLocalModel() {
        return Boolean(STATE.model && STATE.labelsReady && STATE.labels.length);
    }

    function getBackendMinSequenceFrames() {
        if (STATE.adaptiveMode === "fallback") return Math.max(12, BACKEND_MIN_SEQUENCE_FRAMES);
        return hasUsableLocalModel() ? SEQUENCE_LENGTH : BACKEND_MIN_SEQUENCE_FRAMES;
    }

    function getLocalMinSequenceFrames() {
        return LOCAL_FAST_COMMIT_EXPERIMENTAL ? LOCAL_MIN_SEQUENCE_FRAMES : SEQUENCE_LENGTH;
    }

    function shouldUseBackendSequenceFallback({ force = false } = {}) {
        if (STATE.sequenceBuffer.length === 0) return false;
        if (force) return true;
        if (STATE.sequenceBuffer.length < getBackendMinSequenceFrames()) return false;
        if (!hasUsableLocalModel()) return true;

        const now = Date.now();
        if (STATE.stablePrediction && (now - STATE.lastStableAt) < REPEAT_SIGN_COOLDOWN_MS) {
            return false;
        }
        if (STATE.adaptiveMode === "accuracy") {
            if (STATE.sequenceBuffer.length < Math.max(24, getBackendMinSequenceFrames())) {
                return false;
            }
            return (now - STATE.lastCandidateAt) >= 1000;
        }
        return (now - STATE.lastCandidateAt) >= 600;
    }

    function normalizeEngineLabel(engine) {
        return String(engine || "none").replace(/_/g, " ");
    }

    function isLowConfidenceResult(dataOrEngine, maybeReason = "") {
        const engine = typeof dataOrEngine === "object" && dataOrEngine !== null
            ? String(dataOrEngine.engine || "")
            : String(dataOrEngine || "");
        const reason = typeof dataOrEngine === "object" && dataOrEngine !== null
            ? String(dataOrEngine.reason || "")
            : String(maybeReason || "");
        return engine.endsWith("_low_confidence") || reason === "low_confidence";
    }

    function setLiveConfidence(confidence = 0, tone = "neutral") {
        const raw = Number(confidence || 0);
        const normalized = Math.max(0, Math.min(raw > 1 ? raw / 100 : raw, 1));
        const percent = Math.round(normalized * 100);

        if (DOM.liveConfidenceValue) {
            DOM.liveConfidenceValue.innerText = `${percent}%`;
        }
        if (DOM.liveConfidenceFill) {
            DOM.liveConfidenceFill.style.width = `${percent}%`;
            if (tone === "success") {
                DOM.liveConfidenceFill.style.background = "linear-gradient(90deg, rgba(96, 165, 250, 0.9), rgba(74, 222, 128, 0.95))";
            } else if (tone === "warn") {
                DOM.liveConfidenceFill.style.background = "linear-gradient(90deg, rgba(251, 191, 36, 0.9), rgba(249, 115, 22, 0.95))";
            } else if (tone === "danger") {
                DOM.liveConfidenceFill.style.background = "linear-gradient(90deg, rgba(248, 113, 113, 0.9), rgba(239, 68, 68, 0.95))";
            } else {
                DOM.liveConfidenceFill.style.background = "linear-gradient(90deg, rgba(100, 116, 139, 0.9), rgba(148, 163, 184, 0.92))";
            }
        }
    }

    function updateVoiceModeNote() {
        if (!DOM.voiceModeNote) return;
        DOM.voiceModeNote.innerText = STATE.outputMode === "Audio"
            ? "Voice Mode is active and will speak the accepted phrase."
            : "Text output is primary. Switch to Voice Mode to speak the accepted phrase.";
    }

    function updateLiveSignalSummary({ engine = "none", reason = "", confidence = 0, isGuess = false } = {}) {
        const tone = engine === "geometry_fallback" || isGuess || isLowConfidenceResult(engine, reason)
            ? "warn"
            : engine === "no_hand" || reason === "no_hand"
                ? "neutral"
                : engine === "none"
                    ? "neutral"
                    : "success";

        const resolvedConfidence = (engine === "no_hand" || reason === "no_hand") ? 0 : confidence;
        setLiveConfidence(resolvedConfidence, tone);

        if (DOM.liveEngineText) {
            const engineCopy = engine === "no_hand" || reason === "no_hand"
                ? "Waiting for a hand"
                : isLowConfidenceResult(engine, reason)
                    ? "Waiting for a confident translation"
                : engine === "none"
                    ? "Engine idle"
                    : `Engine: ${titleCase(normalizeEngineLabel(engine))}`;
            DOM.liveEngineText.innerText = engineCopy;
        }
    }

    function applyPredictionMeta(data) {
        const engine = String(data && data.engine ? data.engine : "none");
        const reason = String(data && data.reason ? data.reason : "");
        const modelReady = Boolean(data && data.model_ready);
        const isGuess = Boolean(data && data.is_guess);
        let confidence = Number(data && (data.raw_confidence ?? data.confidence));
        if (!Number.isFinite(confidence)) confidence = 0;
        STATE.modelVersion = String((data && data.model_version) || STATE.modelVersion || "");
        STATE.classSetVersion = String((data && data.class_set_version) || STATE.classSetVersion || "");

        STATE.lastEngine = engine;
        STATE.lastReason = reason;
        STATE.backendModelReady = modelReady || STATE.backendModelReady;
        if (data && data.debug) {
            STATE.backendDebug = data.debug;
            console.debug("[sign-debug][backend]", data.debug);
        }

        setBadge(
            DOM.badgeEngine,
            `Engine: ${normalizeEngineLabel(engine)}`,
            (engine === "translation_backend" || engine === "hf_sequence_backend" || engine === "hf_image_backend" || engine === "lstm_backend" || engine === "local_prediction" || engine === "fingerspell_backend")
                || engine === "isign_retrieval_backend"
                ? "success"
                : isLowConfidenceResult(engine, reason)
                    ? "warn"
                : engine === "geometry_fallback"
                    ? "warn"
                    : "neutral"
        );
        setBadge(DOM.badgeGuess, "Guess", "warn", isGuess);
        setBadge(DOM.badgeModel, modelReady ? "Model ready" : "Model warming", modelReady ? "success" : "warn");

        if (engine === "no_hand" || reason === "no_hand") {
            setBadge(DOM.badgeHand, "No hand", "warn");
        } else if (STATE.isLive) {
            setBadge(DOM.badgeHand, "Hand detected", "success");
        } else {
            setBadge(DOM.badgeHand, "No hand", "neutral");
        }

        if (reason === "model_warming" && !modelReady) {
            setStatus("Model warming...", "");
        }
        updateLiveSignalSummary({ engine, reason, confidence, isGuess });
        if (Array.isArray(data && data.top3)) {
            renderTopPredictions(data.top3);
        } else if (engine === "no_hand" || reason === "no_hand") {
            renderTopPredictions([]);
        }
        updateDebugPanel();
    }

    function extractTentativeTranslation(data, fallbackEnglish = "") {
        const tentativeEnglish = titleCase(
            (data && data.tentative_english_text)
            || (Array.isArray(data && data.top3) && data.top3[0] && data.top3[0].label)
            || (data && data.english_text)
            || (data && data.prediction)
            || fallbackEnglish
            || ""
        );
        const tentativeTranslated = String(
            (data && data.tentative_translated_text)
            || (data && data.translated_text)
            || tentativeEnglish
            || ""
        ).trim();
        return { tentativeEnglish, tentativeTranslated };
    }

    function applyTentativeTranslationState(data, fallbackEnglish = "") {
        const { tentativeEnglish, tentativeTranslated } = extractTentativeTranslation(data, fallbackEnglish);
        if (DOM.transcriptBox) {
            DOM.transcriptBox.innerText = tentativeEnglish || "Hold sign steady";
        }
        if (DOM.translatedBox) {
            DOM.translatedBox.innerText = tentativeTranslated
                ? `Tentative: ${tentativeTranslated}`
                : "Hold sign steady for a confident translation";
        }
        STATE.lastTranslatedText = tentativeTranslated || tentativeEnglish || "";
        setStatus(
            tentativeEnglish
                ? "Tentative translation shown. Hold the sign steady to confirm."
                : "Hold sign steady for a confident translation"
        );
        return { tentativeEnglish, tentativeTranslated };
    }

    function hasHandSignal(features) {
        if (!Array.isArray(features) || features.length < 1662) return false;
        for (let i = 1536; i < 1662; i += 1) {
            if (Math.abs(Number(features[i] || 0)) > 1e-6) return true;
        }
        return false;
    }

    async function refreshBackendStatus() {
        try {
            const response = await fetch("/predict-sign-status", { cache: "no-store" });
            if (!response.ok) throw new Error(`status ${response.status}`);
            const data = await response.json();
            STATE.backendModelReady = Boolean(data.model_ready);
            STATE.backendModelLoading = Boolean(data.model_loading);
            STATE.backendModelError = String(data.model_error || "");
            STATE.translationModelReady = Boolean(data.translation_model_ready);
            STATE.translationModelLoading = Boolean(data.translation_model_loading);
            STATE.isignRetrievalReady = Boolean(data.isign_retrieval_ready);
            STATE.modelVersion = String(data.model_version || STATE.modelVersion || "");
            STATE.classSetVersion = String(data.class_set_version || STATE.classSetVersion || "");
            STATE.thresholdVersion = String(data.threshold_version || STATE.thresholdVersion || "");
            if (data.model_registry && typeof data.model_registry === "object") {
                STATE.featureSchema = String(data.model_registry.feature_schema || STATE.featureSchema);
                STATE.inputFeatureSize = Number(data.model_registry.input_feature_size || STATE.inputFeatureSize);
            }
            if (data.schema_manifest && typeof data.schema_manifest === "object") {
                STATE.schemaManifest = {
                    ...(STATE.schemaManifest || {}),
                    ...data.schema_manifest,
                };
                STATE.localModelUrl = toAbsoluteAssetPath(
                    data.schema_manifest.tfjs_model_path,
                    STATE.localModelUrl || DEFAULT_TFJS_MODEL_URL
                );
            }
            if (data.schema_validation && typeof data.schema_validation === "object") {
                STATE.serverSchemaValidation = data.schema_validation;
            }
            if (data.translation_registry && typeof data.translation_registry === "object") {
                STATE.translationMaxFrames = Number(data.translation_registry.max_video_frames || STATE.translationMaxFrames || 120);
                STATE.translationConfidenceThreshold = Number(
                    data.translation_registry.min_confidence || STATE.translationConfidenceThreshold || 0.45
                );
            }
            if (data.isign_retrieval && typeof data.isign_retrieval === "object") {
                STATE.isignRetrievalClipCount = Number(data.isign_retrieval.clip_count || STATE.isignRetrievalClipCount || 0);
                STATE.isignRetrievalUniqueTexts = Number(data.isign_retrieval.unique_text_count || STATE.isignRetrievalUniqueTexts || 0);
            }
            if (data.class_thresholds && typeof data.class_thresholds === "object") {
                STATE.classThresholdDefault = Number(data.class_thresholds.default || STATE.classThresholdDefault || 0.7);
            }
            if (data.supported_signs && typeof data.supported_signs === "object") {
                STATE.supportedFinalLabels = Array.isArray(data.supported_signs.final_labels) ? data.supported_signs.final_labels : [];
                STATE.cautionLabels = Array.isArray(data.supported_signs.caution_labels) ? data.supported_signs.caution_labels : [];
                STATE.blockedLabels = Array.isArray(data.supported_signs.blocked_labels) ? data.supported_signs.blocked_labels : [];
                renderSupportedSigns();
                evaluateChallengeCompatibility();
            }
            const anyModelReady = STATE.translationModelReady || STATE.backendModelReady;
            setBadge(
                DOM.badgeModel,
                anyModelReady ? "Model ready" : "Model warming",
                anyModelReady ? "success" : "warn"
            );
            if (!anyModelReady && (STATE.backendModelLoading || STATE.translationModelLoading)) {
                setStatus("Model warming...", "");
            }
            refreshLocalSchemaValidation();
        } catch (error) {
            console.warn("Backend warm-up status unavailable", error);
            if (!STATE.backendModelReady) {
                setBadge(DOM.badgeModel, "Model status unavailable", "neutral");
            }
        }
    }

    function startBackendStatusPolling() {
        refreshBackendStatus().catch(() => {});
        if (STATE.backendStatusPollTimer) {
            window.clearInterval(STATE.backendStatusPollTimer);
        }
        STATE.backendStatusPollTimer = window.setInterval(() => {
            if (!document.hidden || !STATE.backendModelReady) {
                refreshBackendStatus().catch(() => {});
            }
        }, 3000);
    }

    function titleCase(text) {
        return String(text || "")
            .replace(/_/g, " ")
            .trim()
            .replace(/\s+/g, " ")
            .split(" ")
            .filter(Boolean)
            .map((word) => word[0].toUpperCase() + word.slice(1).toLowerCase())
            .join(" ");
    }

    function normalizeLabel(text) {
        return String(text || "").replace(/_/g, " ").trim().toLowerCase().replace(/\s+/g, " ");
    }

    function normalizeLabelKey(text) {
        return normalizeLabel(text).replace(/\s+/g, "_");
    }

    function toAbsoluteAssetPath(value, fallback = "") {
        const raw = String(value || fallback || "").trim();
        if (!raw) return "";
        if (/^https?:\/\//i.test(raw)) return raw;
        return raw.startsWith("/") ? raw : `/${raw.replace(/^\.?\//, "")}`;
    }

    function normalizeLabelList(values) {
        return Array.isArray(values) ? values.map((item) => normalizeLabel(item)) : [];
    }

    function refreshLocalSchemaValidation() {
        const manifest = STATE.schemaManifest;
        const errors = [];

        if (!manifest || typeof manifest !== "object") {
            errors.push("schema_manifest_missing");
        } else {
            const manifestFeatureSchema = String(manifest.feature_schema || "");
            const manifestFeatureSize = Number(manifest.input_feature_size || 0);
            const manifestSequenceLength = Number(manifest.sequence_length || 0);
            const manifestClassCount = Number(manifest.class_count || 0);

            if (manifestFeatureSchema && STATE.featureSchema && manifestFeatureSchema !== STATE.featureSchema) {
                errors.push(`feature_schema_mismatch:${STATE.featureSchema}->${manifestFeatureSchema}`);
            }
            if (manifestFeatureSize && STATE.inputFeatureSize && manifestFeatureSize !== STATE.inputFeatureSize) {
                errors.push(`feature_size_mismatch:${STATE.inputFeatureSize}->${manifestFeatureSize}`);
            }
            if (manifestSequenceLength && manifestSequenceLength !== SEQUENCE_LENGTH) {
                errors.push(`sequence_length_mismatch:${SEQUENCE_LENGTH}->${manifestSequenceLength}`);
            }
            if (STATE.labelsReady) {
                const actualLabels = normalizeLabelList(STATE.labels);
                const expectedLabels = normalizeLabelList(manifest.labels || []);
                if (manifestClassCount && actualLabels.length !== manifestClassCount) {
                    errors.push(`labels_count_mismatch:${actualLabels.length}->${manifestClassCount}`);
                }
                if (expectedLabels.length && JSON.stringify(actualLabels) !== JSON.stringify(expectedLabels)) {
                    errors.push("labels_order_mismatch");
                }
            }
        }

        if (STATE.serverSchemaValidation && Array.isArray(STATE.serverSchemaValidation.errors)) {
            STATE.serverSchemaValidation.errors.forEach((error) => {
                const value = String(error || "").trim();
                if (value && !errors.includes(value)) {
                    errors.push(value);
                }
            });
        }

        STATE.schemaValidation = {
            ok: errors.length === 0,
            errors,
        };
        return STATE.schemaValidation;
    }

    function roundNumber(value, digits = 4) {
        const num = Number(value);
        if (!Number.isFinite(num)) return 0;
        return Number(num.toFixed(digits));
    }

    function summarizeNumericArray(values) {
        const list = Array.isArray(values)
            ? values.map((item) => Number(item)).filter((item) => Number.isFinite(item))
            : [];
        if (!list.length) {
            return { min: 0, max: 0, mean: 0, nonzero: 0 };
        }

        let min = list[0];
        let max = list[0];
        let sum = 0;
        let nonzero = 0;
        list.forEach((value) => {
            if (value < min) min = value;
            if (value > max) max = value;
            sum += value;
            if (Math.abs(value) > 1e-6) nonzero += 1;
        });

        return {
            min: roundNumber(min),
            max: roundNumber(max),
            mean: roundNumber(sum / list.length),
            nonzero,
        };
    }

    function expandSyntheticFrame(frame) {
        const numericFrame = Array.isArray(frame)
            ? frame.map((value) => Number(value) || 0)
            : [];
        if (numericFrame.length === (RIGHT_HAND_END - POSE_START)) {
            return [
                ...new Array(POSE_START).fill(0),
                ...numericFrame,
            ];
        }
        return numericFrame;
    }

    function buildTopKPredictions(probabilities, labels, limit = 3) {
        const rows = Array.from(probabilities || []).map((confidence, index) => ({
            label: titleCase(labels[index] || `Class ${index}`),
            confidence: roundNumber(confidence),
        }));
        rows.sort((left, right) => Number(right.confidence || 0) - Number(left.confidence || 0));
        return rows.slice(0, Math.max(1, limit));
    }

    function getTopPredictionMargin(rows) {
        const topRows = Array.isArray(rows) ? rows : [];
        if (topRows.length >= 2) {
            return roundNumber(Number(topRows[0].confidence || 0) - Number(topRows[1].confidence || 0));
        }
        if (topRows.length === 1) {
            return roundNumber(Number(topRows[0].confidence || 0));
        }
        return 0;
    }

    function getStableCandidateFromHistory(requiredCount = STABLE_MAJORITY) {
        if (!Array.isArray(STATE.predictionHistory) || !STATE.predictionHistory.length) {
            return "";
        }
        const latest = STATE.predictionHistory[STATE.predictionHistory.length - 1];
        if (!latest) return "";

        let count = 0;
        STATE.predictionHistory.forEach((item) => {
            if (item === latest) count += 1;
        });
        return count >= Math.max(1, Number(requiredCount || STABLE_MAJORITY)) ? latest : "";
    }

    function recordRuntimeEvent(type, payload = {}) {
        const perfNow = window.performance && typeof window.performance.now === "function"
            ? window.performance.now()
            : 0;
        const event = {
            type: String(type || "event"),
            ts_ms: Date.now(),
            perf_ms: roundNumber(perfNow, 3),
            ...payload,
        };
        STATE.runtimeEvents.push(event);
        if (STATE.runtimeEvents.length > 240) {
            STATE.runtimeEvents.splice(0, STATE.runtimeEvents.length - 240);
        }
        return event;
    }

    function getRuntimeEventsSince(perfMs) {
        const threshold = Number(perfMs || 0);
        return STATE.runtimeEvents.filter((event) => Number(event.perf_ms || 0) >= threshold);
    }

    async function waitForRunCompletion(runStartPerf, timeoutMs, requireSpeech) {
        const perfNow = () => (window.performance && typeof window.performance.now === "function"
            ? window.performance.now()
            : 0);
        const deadline = perfNow() + Math.max(250, Number(timeoutMs || 2500));
        while (perfNow() < deadline) {
            const events = getRuntimeEventsSince(runStartPerf);
            const commitEvent = events.find((event) => event.type === "translation_committed");
            const speechTriggerEvent = events.find(
                (event) => event.type === "tts_request" || event.type === "tts_play" || event.type === "tts_browser_play"
            );
            const speechPlayEvent = events.find((event) => event.type === "tts_play" || event.type === "tts_browser_play");
            if (commitEvent && (!requireSpeech || speechTriggerEvent)) {
                return { commitEvent, speechTriggerEvent, speechPlayEvent, events };
            }
            await new Promise((resolve) => window.setTimeout(resolve, 20));
        }
        const events = getRuntimeEventsSince(runStartPerf);
        return {
            commitEvent: events.find((event) => event.type === "translation_committed") || null,
            speechTriggerEvent: events.find(
                (event) => event.type === "tts_request" || event.type === "tts_play" || event.type === "tts_browser_play"
            ) || null,
            speechPlayEvent: events.find((event) => event.type === "tts_play" || event.type === "tts_browser_play") || null,
            events,
        };
    }

    function percentile(values, pct) {
        const list = Array.isArray(values)
            ? values.map((value) => Number(value)).filter((value) => Number.isFinite(value)).sort((left, right) => left - right)
            : [];
        if (!list.length) return 0;
        const clamped = Math.max(0, Math.min(100, Number(pct || 0)));
        const index = Math.min(list.length - 1, Math.max(0, Math.ceil((clamped / 100) * list.length) - 1));
        return roundNumber(list[index], 2);
    }

    function updateDebugPanel(extra = {}) {
        if (!DOM.debugOutput) return;
        const runtime = {
            sequence_buffer_frames: STATE.sequenceBuffer.length,
            prediction_history: STATE.predictionHistory.slice(),
            stable_prediction: STATE.stablePrediction,
            last_translated_text: STATE.lastTranslatedText,
            active_committed_gesture: STATE.activeCommittedGestureKey,
            adaptive_mode: STATE.adaptiveMode,
            output_mode: STATE.outputMode,
            backend_model_ready: STATE.backendModelReady,
            translation_model_ready: STATE.translationModelReady,
            local_model_ready: hasUsableLocalModel(),
            local_engine: {
                enabled: STATE.localEngineEnabled,
                reason: STATE.localEngineReason,
                backend: STATE.localEngineBackend,
                model_url: STATE.localModelUrl,
            },
            last_engine: STATE.lastEngine,
            last_reason: STATE.lastReason,
            translation_trigger_state: {
                should_use_backend_fallback: shouldUseBackendSequenceFallback(),
                last_candidate_at: STATE.lastCandidateAt,
                last_stable_at: STATE.lastStableAt,
                last_committed_at: STATE.lastCommittedAt,
                last_committed_key: STATE.lastCommittedKey,
            },
            recent_events: STATE.runtimeEvents.slice(-8),
        };

        const snapshot = {
            runtime,
            schema: {
                manifest: STATE.schemaManifest || {},
                browser_validation: STATE.schemaValidation || {},
                server_validation: STATE.serverSchemaValidation || {},
                self_test: STATE.localSelfTest || {},
            },
            local: STATE.localDebug || {},
            backend: STATE.backendDebug || {},
            ...extra,
        };
        DOM.debugOutput.textContent = JSON.stringify(snapshot, null, 2);
    }

    function renderSupportedSigns() {
        const finalLabels = Array.isArray(STATE.supportedFinalLabels) ? STATE.supportedFinalLabels : [];
        const cautionLabels = Array.isArray(STATE.cautionLabels) ? STATE.cautionLabels : [];
        const blockedLabels = Array.isArray(STATE.blockedLabels) ? STATE.blockedLabels : [];

        if (DOM.supportedSignCount) {
            DOM.supportedSignCount.innerText = finalLabels.length ? String(finalLabels.length) : "--";
        }
        if (DOM.supportedSignSummary) {
            if (finalLabels.length) {
                const cautionCopy = cautionLabels.length
                    ? ` ${cautionLabels.length} phrases need a steadier hold.`
                    : "";
                const referenceCopy = STATE.isignRetrievalReady && STATE.isignRetrievalClipCount
                    ? ` Full iSign reference: ${STATE.isignRetrievalClipCount.toLocaleString()} clips across ${Math.max(STATE.isignRetrievalUniqueTexts, 0).toLocaleString()} imported texts.`
                    : "";
                DOM.supportedSignSummary.innerText = `${finalLabels.length} local phrases are approved for live use.${cautionCopy}${referenceCopy}`;
            } else {
                DOM.supportedSignSummary.innerText = STATE.isignRetrievalReady && STATE.isignRetrievalClipCount
                    ? `Local phrase coverage metadata is still loading. Full iSign reference: ${STATE.isignRetrievalClipCount.toLocaleString()} clips across ${Math.max(STATE.isignRetrievalUniqueTexts, 0).toLocaleString()} imported texts.`
                    : "Local phrase coverage metadata is still loading.";
            }
        }
        if (DOM.supportedSignList) {
            if (!finalLabels.length) {
                DOM.supportedSignList.innerHTML = '<span class="supported-sign-chip">Loading...</span>';
            } else {
                DOM.supportedSignList.innerHTML = finalLabels
                    .map((row) => {
                        const label = titleCase(row.label || "");
                        const caution = cautionLabels.some((item) => normalizeLabel(item.label) === normalizeLabel(row.label));
                        return `<span class="supported-sign-chip${caution ? " caution" : ""}">${label}</span>`;
                    })
                    .join("");
            }
        }
        if (DOM.supportedSignCaution) {
            if (blockedLabels.length) {
                DOM.supportedSignCaution.innerText = `Hidden from final output until retrained: ${blockedLabels.map((item) => titleCase(item.label || "")).join(", ")}.`;
            } else if (cautionLabels.length) {
                DOM.supportedSignCaution.innerText = `Steadier hold recommended for: ${cautionLabels.slice(0, 6).map((item) => titleCase(item.label || "")).join(", ")}${cautionLabels.length > 6 ? "..." : ""}`;
            } else {
                DOM.supportedSignCaution.innerText = "All listed phrases are currently in the reliable live set.";
            }
        }
    }

    function projectFrameForModel(frame) {
        if (!Array.isArray(frame)) return [];
        if (STATE.featureSchema === "pose_hands_258_v1" && frame.length >= FULL_FEATURE_SIZE) {
            return frame
                .slice(POSE_START, POSE_END)
                .concat(frame.slice(LEFT_HAND_START, LEFT_HAND_END), frame.slice(RIGHT_HAND_START, RIGHT_HAND_END));
        }
        if (frame.length >= STATE.inputFeatureSize) {
            return frame.slice(0, STATE.inputFeatureSize);
        }
        return frame.slice();
    }

    function projectSequenceForModel(sequence) {
        return sequence.map((frame) => projectFrameForModel(frame));
    }

    function getThresholdForLabel(label, minThreshold = 0) {
        const key = normalizeLabelKey(label);
        const configured = Number(STATE.classThresholds[key]);
        const baseThreshold = Number.isFinite(configured) ? configured : Number(STATE.classThresholdDefault || 0.7);
        const floor = Number(minThreshold || 0);
        return Math.max(baseThreshold, floor);
    }

    async function loadModelMetadata() {
        try {
            const response = await fetch(DEFAULT_SCHEMA_MANIFEST_URL, { cache: "no-store" });
            if (response.ok) {
                const manifest = await response.json();
                STATE.schemaManifest = manifest;
                STATE.localModelUrl = toAbsoluteAssetPath(manifest.tfjs_model_path, STATE.localModelUrl || DEFAULT_TFJS_MODEL_URL);
            }
        } catch (error) {
            console.warn("Schema manifest unavailable", error);
        }

        try {
            const response = await fetch("/static/models/model_registry.json", { cache: "no-store" });
            if (response.ok) {
                const registry = await response.json();
                STATE.modelRegistry = registry;
                STATE.modelVersion = String(registry.model_version || "");
                STATE.classSetVersion = String(registry.class_set_version || "");
                STATE.thresholdVersion = String(registry.threshold_version || "");
                STATE.featureSchema = String(registry.feature_schema || STATE.featureSchema);
                STATE.inputFeatureSize = Number(registry.input_feature_size || STATE.inputFeatureSize || FULL_FEATURE_SIZE);
                STATE.localModelUrl = toAbsoluteAssetPath(registry.tfjs_model_path, STATE.localModelUrl || DEFAULT_TFJS_MODEL_URL);
            }
        } catch (error) {
            console.warn("Model registry unavailable", error);
        }

        try {
            const response = await fetch("/static/models/tfjs_lstm/class_thresholds.json", { cache: "no-store" });
            if (response.ok) {
                const payload = await response.json();
                const rawThresholds = payload && typeof payload === "object" ? (payload.thresholds || payload) : {};
                const parsedThresholds = {};
                Object.entries(rawThresholds || {}).forEach(([label, value]) => {
                    const num = Number(value);
                    if (Number.isFinite(num)) {
                        parsedThresholds[normalizeLabelKey(label)] = num;
                    }
                });
                STATE.classThresholds = parsedThresholds;
                STATE.classThresholdDefault = Number(payload.default_threshold || STATE.classThresholdDefault || 0.7);
                if (payload.threshold_version) {
                    STATE.thresholdVersion = String(payload.threshold_version);
                }
            }
        } catch (error) {
            console.warn("Threshold metadata unavailable", error);
        }

        refreshLocalSchemaValidation();
    }

    async function loadSentenceLabels() {
        try {
            const labelsRes = await fetch("/static/models/tfjs_lstm/labels.json");
            if (!labelsRes.ok) throw new Error(`labels fetch failed (${labelsRes.status})`);
            const labels = await labelsRes.json();
            STATE.labels = Array.isArray(labels) ? labels : [];
            STATE.labelsReady = STATE.labels.length > 0;
            evaluateChallengeCompatibility();
            refreshLocalSchemaValidation();
        } catch (error) {
            console.warn(error);
            if (STATE.modelRegistry && Array.isArray(STATE.modelRegistry.labels)) {
                STATE.labels = STATE.modelRegistry.labels.slice();
                STATE.labelsReady = STATE.labels.length > 0;
            } else {
                STATE.labels = [];
                STATE.labelsReady = false;
            }
            refreshLocalSchemaValidation();
        }
    }

    function evaluateChallengeCompatibility() {
        if (!STATE.challengeWord || !STATE.labelsReady) return;

        const target = normalizeLabel(STATE.challengeWord);
        const preferredLabels = STATE.supportedFinalLabels.length
            ? STATE.supportedFinalLabels.map((row) => row.label)
            : STATE.labels;
        const available = new Set(preferredLabels.map(normalizeLabel));
        if (available.has(target)) return;

        STATE.challengeSupported = false;
        if (DOM.challengeFeedback) {
            DOM.challengeFeedback.style.display = "flex";
            DOM.challengeFeedback.style.background = "rgba(245, 158, 11, 0.16)";
            DOM.challengeFeedback.style.border = "1px solid rgba(245, 158, 11, 0.45)";
            DOM.challengeFeedback.innerHTML = '<i class="fas fa-exclamation-triangle" style="color: #fbbf24;"></i> This challenge is not available in the ISL sentence model.';
        }
    }

    function updateMetaLabels() {
        if (DOM.signLangSelect && DOM.sourceMeta) {
            DOM.sourceMeta.innerText = DOM.signLangSelect.value.toUpperCase().slice(0, 3);
        }
        if (DOM.outLangSelect && DOM.targetMeta) {
            DOM.targetMeta.innerText = LANG_CODE[DOM.outLangSelect.value] || "EN";
        }
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
            setSelectValue(DOM.signLangSelect, preferences.sign_input_language);
            setSelectValue(DOM.outLangSelect, preferences.sign_output_language);

            const preferredMode = String(preferences.sign_detection_mode || "").trim().toLowerCase();
            if (preferredMode) {
                setAdaptiveMode(preferredMode, true);
            }

            updateMetaLabels();
            renderSessionPhrase();
        } catch (error) {
            console.warn("User preferences unavailable", error);
        }
    }

    function renderTopPredictions(top3 = []) {
        if (!DOM.topPredictions) return;
        DOM.topPredictions.innerHTML = "";

        if (!Array.isArray(top3) || !top3.length) {
            const empty = document.createElement("span");
            empty.style.display = "inline-flex";
            empty.style.alignItems = "center";
            empty.style.gap = "0.35rem";
            empty.style.padding = "0.45rem 0.7rem";
            empty.style.borderRadius = "999px";
            empty.style.background = "rgba(15, 23, 42, 0.55)";
            empty.style.border = "1px solid rgba(148, 163, 184, 0.18)";
            empty.style.color = "#94a3b8";
            empty.style.fontSize = "0.78rem";
            empty.innerText = "Waiting for a stable sign";
            DOM.topPredictions.appendChild(empty);
            return;
        }

        top3.slice(0, 3).forEach((item, index) => {
            const chip = document.createElement("span");
            const confidence = Math.round(Number(item && item.confidence ? item.confidence : 0) * 100);
            const caution = String(item && item.reliability ? item.reliability : "") === "caution";
            chip.style.display = "inline-flex";
            chip.style.alignItems = "center";
            chip.style.gap = "0.45rem";
            chip.style.padding = "0.45rem 0.72rem";
            chip.style.borderRadius = "999px";
            chip.style.background = caution
                ? "rgba(180, 83, 9, 0.18)"
                : index === 0
                    ? "rgba(34, 197, 94, 0.14)"
                    : "rgba(15, 23, 42, 0.55)";
            chip.style.border = caution
                ? "1px solid rgba(251, 191, 36, 0.35)"
                : index === 0
                    ? "1px solid rgba(74, 222, 128, 0.28)"
                    : "1px solid rgba(148, 163, 184, 0.18)";
            chip.style.color = caution ? "#fde68a" : index === 0 ? "#bbf7d0" : "#cbd5e1";
            chip.style.fontSize = "0.78rem";
            chip.style.fontWeight = index === 0 ? "600" : "500";
            chip.innerText = `${titleCase(item && item.label ? item.label : "")} ${confidence}%`;
            DOM.topPredictions.appendChild(chip);
        });
    }

    function getSessionPhraseText() {
        return STATE.sessionSegments.map((segment) => segment.translated).filter(Boolean).join(" ").trim();
    }

    function renderSessionPhrase() {
        const translatedPhrase = getSessionPhraseText();
        const englishPhrase = STATE.sessionSegments.map((segment) => segment.english).filter(Boolean).join(" ").trim();
        if (DOM.sessionTranscript) {
            DOM.sessionTranscript.innerText = translatedPhrase || "No phrase yet";
        }
        if (DOM.sessionEnglish) {
            const outputLanguage = String((DOM.outLangSelect && DOM.outLangSelect.value) || "english").toLowerCase();
            if (!englishPhrase) {
                DOM.sessionEnglish.innerText = "Accepted signs will build a running phrase here.";
            } else if (outputLanguage === "english") {
                DOM.sessionEnglish.innerText = "Accepted signs are added as each sign stabilizes.";
            } else {
                DOM.sessionEnglish.innerText = `English source: ${englishPhrase}`;
            }
        }
        if (DOM.sessionSpeakBtn) DOM.sessionSpeakBtn.disabled = !translatedPhrase;
        if (DOM.sessionClearBtn) DOM.sessionClearBtn.disabled = STATE.sessionSegments.length === 0;
    }

    function clearSessionPhrase(silent = false) {
        stopSpeaking();
        STATE.sessionSegments = [];
        STATE.lastSessionCommitAt = 0;
        STATE.lastCommittedKey = "";
        STATE.lastCommittedAt = 0;
        STATE.lastCommittedTranslatedText = "";
        renderSessionPhrase();
        updateDebugPanel();
        if (!silent) setStatus("Session phrase cleared");
    }

    function commitSessionPhrase(englishText, translatedText) {
        const english = titleCase(englishText);
        const translated = String(translatedText || english).trim();
        if (!english || english === "No Sign Detected" || !translated) return;

        const normalized = normalizeLabel(english);
        const now = Date.now();
        const last = STATE.sessionSegments[STATE.sessionSegments.length - 1];
        if (last && last.key === normalized && (now - STATE.lastSessionCommitAt) < REPEAT_SIGN_COOLDOWN_MS) {
            return;
        }

        STATE.sessionSegments.push({ key: normalized, english, translated });
        if (STATE.sessionSegments.length > 18) {
            STATE.sessionSegments.shift();
        }
        STATE.lastSessionCommitAt = now;
        renderSessionPhrase();
    }

    function setModeText() {
        const translationNodes = document.querySelectorAll('[data-tab-content="translationTab"]');
        const audioNodes = document.querySelectorAll('[data-tab-content="audioTab"]');
        translationNodes.forEach((node) => {
            node.style.display = "";
        });
        audioNodes.forEach((node) => {
            node.style.display = "none";
        });
        updateVoiceModeNote();
    }

    function setModeAudio() {
        const translationNodes = document.querySelectorAll('[data-tab-content="translationTab"]');
        const audioNodes = document.querySelectorAll('[data-tab-content="audioTab"]');
        translationNodes.forEach((node) => {
            node.style.display = "none";
        });
        audioNodes.forEach((node) => {
            node.style.display = "flex";
        });
        updateVoiceModeNote();
    }

    function clearTTSAnimation() {
        if (STATE.ttsAnimTimer) {
            window.clearInterval(STATE.ttsAnimTimer);
            STATE.ttsAnimTimer = null;
        }
        if (!DOM.audioBars) return;
        DOM.audioBars.querySelectorAll(".bar").forEach((bar) => {
            bar.style.height = "30%";
        });
    }

    function animateTTSBars() {
        if (!DOM.audioBars) return;
        const bars = DOM.audioBars.querySelectorAll(".bar");
        clearTTSAnimation();
        STATE.ttsAnimTimer = window.setInterval(() => {
            bars.forEach((bar) => {
                const h = 25 + Math.floor(Math.random() * 75);
                bar.style.height = `${h}%`;
            });
        }, 120);
    }

    function stopSpeaking() {
        clearTTSAnimation();
        if (STATE.activeAudio) {
            try {
                STATE.activeAudio.pause();
            } catch (error) {
                console.warn("Could not pause active audio", error);
            }
            STATE.activeAudio = null;
        }
        if (DOM.audioOutput) {
            try {
                DOM.audioOutput.pause();
                DOM.audioOutput.removeAttribute("src");
                DOM.audioOutput.load();
            } catch (error) {
                console.warn("Could not reset audio output", error);
            }
        }
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    }

    async function speakText(text) {
        const cleanText = String(text || "").trim();
        if (!cleanText) return;
        stopSpeaking();
        const requestStartedAt = window.performance && typeof window.performance.now === "function"
            ? window.performance.now()
            : 0;
        const language = (DOM.outLangSelect && DOM.outLangSelect.value) || "english";
        recordRuntimeEvent("tts_request", {
            text: cleanText,
            language,
        });

        if ("speechSynthesis" in window) {
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = TTS_LANG[language] || "en-US";
            utterance.rate = 1;
            utterance.onstart = () => {
                animateTTSBars();
                recordRuntimeEvent("tts_browser_play", {
                    text: cleanText,
                    language,
                    engine: "browser_speech",
                    latency_ms: roundNumber((window.performance.now() - requestStartedAt), 2),
                });
            };
            utterance.onend = clearTTSAnimation;
            utterance.onerror = () => {
                clearTTSAnimation();
                recordRuntimeEvent("tts_browser_error", {
                    text: cleanText,
                    language,
                });
            };
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
            return;
        }

        try {
            const response = await fetch("/text-to-speech", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: cleanText,
                    language,
                }),
            });
            if (!response.ok) throw new Error(`status ${response.status}`);
            const data = await response.json();
            recordRuntimeEvent("tts_response", {
                ok: true,
                text: cleanText,
                language,
                latency_ms: roundNumber((window.performance.now() - requestStartedAt), 2),
                audio_base64_length: Number((data && data.audio_base64 && data.audio_base64.length) || 0),
            });
            if (data.audio_base64 && data.audio_base64.length > 0) {
                const audio = DOM.audioOutput || new Audio();
                audio.src = `data:audio/mpeg;base64,${data.audio_base64}`;
                audio.onplay = animateTTSBars;
                audio.onended = () => {
                    STATE.activeAudio = null;
                    clearTTSAnimation();
                };
                audio.onerror = () => {
                    STATE.activeAudio = null;
                    clearTTSAnimation();
                };
                STATE.activeAudio = audio;
                await audio.play().catch((error) => {
                    throw error;
                });
                recordRuntimeEvent("tts_play", {
                    text: cleanText,
                    language,
                    engine: "server_audio",
                    latency_ms: roundNumber((window.performance.now() - requestStartedAt), 2),
                });
                return;
            }
            throw new Error("No audio data received from server");
        } catch (error) {
            console.warn("Server TTS unavailable, falling back to browser speech", error);
            recordRuntimeEvent("tts_error", {
                text: cleanText,
                language,
                error: String(error && error.message ? error.message : error),
                latency_ms: roundNumber((window.performance.now() - requestStartedAt), 2),
            });
        }
    }

    function updateDetectionHeartbeat() {
        if (!STATE.isLive) return;
        if (Date.now() - STATE.lastHandSeenAt > HAND_IDLE_MS) {
            setBadge(DOM.badgeHand, "No hand", "warn");
            if (Date.now() - STATE.lastNoHandStatusAt > 1200) {
                setStatus("No hand detected");
                STATE.lastNoHandStatusAt = Date.now();
            }
            return;
        }
        if (Date.now() - STATE.lastCandidateAt > DETECTION_IDLE_MS) {
            setStatus("Detecting sign...");
            setBadge(DOM.badgeStable, "Stable", "neutral");
        }
    }

    function resetSignChangeTracker() {
        STATE.signChangeCandidate = "";
        STATE.signChangeCandidateCount = 0;
    }

    function clearTransitionPrime() {
        STATE.transitionPrimedLabel = "";
        STATE.transitionPrimedAt = 0;
    }

    function primeTransition(label, reason = "transition_candidate", confidence = 0, top1Margin = 0) {
        const normalizedLabel = normalizeLabel(label);
        if (!normalizedLabel) return false;
        const now = Date.now();
        const alreadyPrimed =
            STATE.transitionPrimedLabel === normalizedLabel
            && (now - STATE.transitionPrimedAt) <= SIGN_CHANGE_PRIMED_WINDOW_MS;
        STATE.transitionPrimedLabel = normalizedLabel;
        STATE.transitionPrimedAt = now;
        if (!alreadyPrimed) {
            recordRuntimeEvent("transition_prime", {
                label: titleCase(normalizedLabel),
                reason,
                confidence: roundNumber(confidence),
                top1_margin: roundNumber(top1Margin),
            });
        }
        return true;
    }

    function reprimeForSignChange(nextLabel, activeGestureKey, confidence, top1Margin, reason = "sign_change") {
        const reprimeFrames = STATE.recentFrameBuffer.slice(-Math.max(getLocalMinSequenceFrames(), SIGN_CHANGE_REPRIME_FRAMES));
        if (reprimeFrames.length) {
            STATE.sequenceBuffer = reprimeFrames.map((frame) => (Array.isArray(frame) ? frame.slice() : frame));
        }
        STATE.predictionHistory = [];
        STATE.stablePrediction = "";
        STATE.lastStableAt = 0;
        STATE.lastCandidateAt = Date.now() - 1000;
        STATE.activeCommittedGestureKey = "";
        primeTransition(nextLabel, reason, confidence, top1Margin);
        recordRuntimeEvent("sign_change_reprime", {
            from: titleCase(activeGestureKey),
            to: titleCase(nextLabel),
            preserved_frames: STATE.sequenceBuffer.length,
            confidence: roundNumber(confidence),
            top1_margin: roundNumber(top1Margin),
            reason,
        });
        resetSignChangeTracker();
        updateDebugPanel();
    }

    function clearDetectionBuffers() {
        STATE.sequenceBuffer = [];
        STATE.recentFrameBuffer = [];
        STATE.predictionHistory = [];
        STATE.activeCommittedGestureKey = "";
        resetSignChangeTracker();
        clearTransitionPrime();
        STATE.runtimeEpoch += 1;
        updateDebugPanel();
    }

    function extractFeatures(results) {
        const featureList = [];

        if (results.faceLandmarks) {
            for (const lm of results.faceLandmarks) featureList.push(lm.x, lm.y, lm.z);
        } else {
            featureList.push(...new Array(1404).fill(0));
        }

        if (results.poseLandmarks) {
            for (const lm of results.poseLandmarks) featureList.push(lm.x, lm.y, lm.z, lm.visibility || 0);
        } else {
            featureList.push(...new Array(132).fill(0));
        }

        if (results.leftHandLandmarks) {
            for (const lm of results.leftHandLandmarks) featureList.push(lm.x, lm.y, lm.z);
        } else {
            featureList.push(...new Array(63).fill(0));
        }

        if (results.rightHandLandmarks) {
            for (const lm of results.rightHandLandmarks) featureList.push(lm.x, lm.y, lm.z);
        } else {
            featureList.push(...new Array(63).fill(0));
        }

        return featureList;
    }

    function drawHands(results) {
        if (!DOM.ctx || !DOM.canvas) return;
        const HAND_LINKS = window.HAND_CONNECTIONS || (window.Holistic && window.Holistic.HAND_CONNECTIONS) || [];

        DOM.ctx.save();
        DOM.ctx.clearRect(0, 0, DOM.canvas.width, DOM.canvas.height);

        if (results.leftHandLandmarks) {
            if (HAND_LINKS.length) {
                drawConnectors(DOM.ctx, results.leftHandLandmarks, HAND_LINKS, { color: "rgba(165, 180, 252, 0.4)", lineWidth: 2 });
            }
            drawLandmarks(DOM.ctx, results.leftHandLandmarks, { color: "#ffffff", fillColor: "#818cf8", lineWidth: 1, radius: 3 });
        }
        if (results.rightHandLandmarks) {
            if (HAND_LINKS.length) {
                drawConnectors(DOM.ctx, results.rightHandLandmarks, HAND_LINKS, { color: "rgba(244, 114, 182, 0.4)", lineWidth: 2 });
            }
            drawLandmarks(DOM.ctx, results.rightHandLandmarks, { color: "#ffffff", fillColor: "#ec4899", lineWidth: 1, radius: 3 });
        }

        DOM.ctx.restore();
    }

    async function loadLocalModel() {
        if (!(window.tf && tf.loadLayersModel)) {
            STATE.localEngineEnabled = false;
            STATE.localEngineReason = "tfjs_runtime_unavailable";
            STATE.localDebug = { error: "tfjs_runtime_unavailable" };
            updateDebugPanel();
            setStatus(
                STATE.backendModelReady
                    ? "TFJS unavailable. Using backend inference."
                    : "TFJS unavailable. Waiting for backend inference.",
                STATE.backendModelReady ? "" : "error"
            );
            return;
        }
        if (!(window.SamvakTfjsSelfTest && typeof window.SamvakTfjsSelfTest.runSelfTest === "function")) {
            STATE.localEngineEnabled = false;
            STATE.localEngineReason = "tfjs_self_test_unavailable";
            STATE.localDebug = { error: "tfjs_self_test_unavailable" };
            updateDebugPanel();
            setStatus(
                STATE.backendModelReady
                    ? "Local TFJS disabled. Using backend inference."
                    : "Local TFJS self-test unavailable.",
                STATE.backendModelReady ? "" : "error"
            );
            return;
        }

        const schemaValidation = refreshLocalSchemaValidation();
        if (!schemaValidation.ok) {
            STATE.model = null;
            STATE.localEngineEnabled = false;
            STATE.localEngineBackend = "";
            STATE.localEngineReason = `schema_validation_failed: ${schemaValidation.errors.join(", ")}`;
            STATE.localDebug = {
                error: STATE.localEngineReason,
                schema_validation: schemaValidation,
            };
            updateDebugPanel();
            setStatus(
                STATE.backendModelReady
                    ? "Local TFJS disabled. Using backend inference."
                    : "Local TFJS schema mismatch.",
                STATE.backendModelReady ? "" : "error"
            );
            return;
        }

        try {
            const modelUrl = toAbsoluteAssetPath(STATE.localModelUrl, DEFAULT_TFJS_MODEL_URL);
            setStatus("Running local AI self-test...");
            const selfTest = await window.SamvakTfjsSelfTest.runSelfTest({
                modelUrl,
                backends: ["webgl", "cpu"],
            });
            STATE.localSelfTest = selfTest;
            if (!selfTest.ok) {
                STATE.model = null;
                STATE.localEngineEnabled = false;
                STATE.localEngineBackend = "";
                STATE.localEngineReason = `self_test_failed: ${selfTest.error}`;
                STATE.localDebug = {
                    error: STATE.localEngineReason,
                    self_test: selfTest,
                };
                updateDebugPanel();
                setStatus(
                    STATE.backendModelReady
                        ? "Local TFJS disabled. Using backend inference."
                        : "Local TFJS self-test failed.",
                    STATE.backendModelReady ? "" : "error"
                );
                return;
            }

            setStatus("Initializing local AI...");
            const activeBackend = String(selfTest.passedBackend || "cpu");
            await tf.setBackend(activeBackend);
            await tf.ready();

            STATE.model = await tf.loadLayersModel(modelUrl, { strict: true });
            const inputShape = Array.isArray(STATE.model.inputs) && STATE.model.inputs[0]
                ? STATE.model.inputs[0].shape
                : null;
            const loadedFeatureSize = Array.isArray(inputShape) ? Number(inputShape[2] || 0) : 0;
            if (loadedFeatureSize > 0 && loadedFeatureSize !== STATE.inputFeatureSize) {
                STATE.inputFeatureSize = loadedFeatureSize;
                STATE.featureSchema = loadedFeatureSize === FULL_FEATURE_SIZE ? "holistic_1662_v1" : "pose_hands_258_v1";
            }
            STATE.localEngineEnabled = true;
            STATE.localEngineReason = "ready";
            STATE.localEngineBackend = activeBackend;
            STATE.localDebug = {
                model: "tfjs_lstm",
                loaded: true,
                backend: activeBackend,
                model_url: modelUrl,
                input_tensor: {
                    shape: [1, SEQUENCE_LENGTH, STATE.inputFeatureSize],
                    dtype: "float32",
                },
                label_count: STATE.labels.length,
                feature_schema: STATE.featureSchema,
                self_test: selfTest,
            };
            updateDebugPanel();
            setStatus("AI ready. Start camera.", "success");
        } catch (error) {
            console.warn(error);
            STATE.model = null;
            STATE.localEngineEnabled = false;
            STATE.localEngineBackend = "";
            STATE.localEngineReason = `load_failed: ${String(error && error.message ? error.message : error)}`;
            STATE.localDebug = {
                error: STATE.localEngineReason,
                self_test: STATE.localSelfTest || null,
            };
            updateDebugPanel();
            setStatus(
                STATE.backendModelReady
                    ? "Local TFJS disabled. Using backend inference."
                    : "Preparing backend AI...",
                STATE.backendModelReady ? "success" : ""
            );
        }
    }

    async function translatePrediction(prediction, confidence) {
        const requestEpoch = STATE.runtimeEpoch;
        const reqId = ++STATE.lastTranslationReqId;
        try {
            const targetLanguage = (DOM.outLangSelect ? DOM.outLangSelect.value : "english") || "english";
            const localTop3 = Array.isArray(STATE.localDebug && STATE.localDebug.top3) ? STATE.localDebug.top3 : [];
            const localTop1Margin = getTopPredictionMargin(localTop3);
            const normalizedPrediction = normalizeLabel(prediction);
            const transitionTrustBoost =
                Boolean(STATE.transitionPrimedLabel)
                && normalizedPrediction === STATE.transitionPrimedLabel
                && (Date.now() - STATE.transitionPrimedAt) <= SIGN_CHANGE_PRIMED_WINDOW_MS;
            const localConfidenceFloor = transitionTrustBoost
                ? Math.min(LOCAL_TRUST_MIN_CONFIDENCE, TRANSITION_LOCAL_CONFIDENCE_FLOOR)
                : LOCAL_TRUST_MIN_CONFIDENCE;
            const localMarginFloor = transitionTrustBoost
                ? Math.max(LOCAL_TRUST_MIN_MARGIN, TRANSITION_LOCAL_MARGIN_FLOOR)
                : LOCAL_TRUST_MIN_MARGIN;
            const meetsLocalTrustSignal =
                Number(confidence || 0) >= Math.max(getLocalConfidenceThreshold(), localConfidenceFloor)
                && localTop1Margin >= localMarginFloor;
            const useLocalTrustBridge =
                LOCAL_TRUST_BRIDGE_EXPERIMENTAL
                && hasUsableLocalModel()
                && STATE.adaptiveMode === "accuracy"
                && meetsLocalTrustSignal;
            const needsBackendConfirmation = !useLocalTrustBridge;
            const useHybridAssist = needsBackendConfirmation && (
                !hasUsableLocalModel()
                || STATE.adaptiveMode === "fallback"
                || STATE.sequenceBuffer.length >= 36
            );
            const canFastCommitLocally =
                LOCAL_FAST_COMMIT_EXPERIMENTAL
                && useLocalTrustBridge
                && String(targetLanguage).toLowerCase() === "english"
                && meetsLocalTrustSignal;
            if (canFastCommitLocally) {
                const localText = titleCase(prediction || "");
                const fastData = {
                    english_text: localText,
                    translated_text: localText,
                    prediction: localText,
                    confidence: Number(confidence || 0),
                    raw_confidence: Number(confidence || 0),
                    top3: localTop3,
                    engine: "local_prediction",
                    reason: "fast_local_english",
                    model_ready: STATE.backendModelReady,
                    is_guess: false,
                };
                recordRuntimeEvent("local_fast_commit", {
                    prediction: localText,
                    confidence: roundNumber(confidence),
                });
                applyPredictionMeta(fastData);
                applyConfirmedTranslation(fastData, prediction);
                return;
            }
            const currentFrame = useHybridAssist && shouldCaptureTranslationFrame() ? captureCurrentFrameDataUrl() : "";
            const recentSequence = needsBackendConfirmation ? STATE.sequenceBuffer.slice(-getBackendSequenceLength()) : [];
            const requestBody = {
                prediction,
                confidence,
                target_language: targetLanguage,
                mode: STATE.adaptiveMode,
                debug: true,
                min_confidence: getBackendMinConfidence({ trustLocalPrediction: useLocalTrustBridge }),
                allow_geometry_fallback: getAllowGeometryFallback(),
                prefer_trained_translation: STATE.adaptiveMode !== "fallback",
                allow_prediction_echo: STATE.adaptiveMode === "fallback",
                use_isign_retrieval: STATE.adaptiveMode === "fallback",
                sequence_priority: STATE.adaptiveMode === "fallback" ? "retrieval_first" : "lstm_first",
                use_hf_image: useHybridAssist && Boolean(currentFrame),
                use_fingerspell_router: !useLocalTrustBridge,
                trust_local_prediction: useLocalTrustBridge,
                local_top1_margin: localTop1Margin,
                local_margin_threshold: localMarginFloor,
                local_confidence_floor: localConfidenceFloor,
            };
            if (recentSequence.length) {
                requestBody.sequence = recentSequence;
            }
            if (currentFrame) {
                requestBody.image_base64 = currentFrame;
                requestBody.prefer_image_translation = useHybridAssist;
            }
            const response = await fetch("/predict-sign", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(requestBody),
            });
            if (!response.ok) throw new Error(`Translation failed (${response.status})`);

            const data = await response.json();
            if (requestEpoch !== STATE.runtimeEpoch) return;
            applyPredictionMeta(data);
            if (reqId < STATE.latestAppliedReqId) return;
            STATE.latestAppliedReqId = reqId;
            const lowConfidence = isLowConfidenceResult(data) && STATE.adaptiveMode === "accuracy";
            const { tentativeEnglish, tentativeTranslated } = extractTentativeTranslation(data, prediction);
            const englishText = lowConfidence ? tentativeEnglish : titleCase(data.english_text || data.prediction || prediction);
            const translatedText = lowConfidence
                ? (tentativeTranslated ? `Tentative: ${tentativeTranslated}` : "No confident translation yet")
                : String(data.translated_text || englishText || "").trim();

            if (DOM.transcriptBox) {
                DOM.transcriptBox.innerText = englishText || (lowConfidence ? "Hold sign steady" : "Waiting...");
            }
            if (DOM.translatedBox) {
                DOM.translatedBox.innerText = translatedText || "Translation unavailable";
            }

            if (lowConfidence) {
                applyTentativeTranslationState(data, prediction);
                return;
            }
            applyConfirmedTranslation(data, prediction);
        } catch (error) {
            console.error(error);
            setStatus("Translation request failed", "error");
        }
    }

    function registerCandidate(text, confidence, meta = null, onStable = null) {
        const clean = String(text || "").trim();
        if (!clean || clean === "No Sign Detected") return;

        STATE.lastCandidateAt = Date.now();
        STATE.predictionHistory.push(clean);
        if (STATE.predictionHistory.length > STABLE_HISTORY_SIZE) {
            STATE.predictionHistory.shift();
        }

        const requiredStability = Number(confidence || 0) >= FAST_TRACK_STABILITY_CONFIDENCE
            ? HIGH_CONFIDENCE_STABLE_MAJORITY
            : STABLE_MAJORITY;
        const normalizedClean = normalizeLabel(clean);
        const transitionPrimed =
            Boolean(STATE.transitionPrimedLabel)
            && normalizedClean === STATE.transitionPrimedLabel
            && (Date.now() - STATE.transitionPrimedAt) <= SIGN_CHANGE_PRIMED_WINDOW_MS;
        const currentTop1Margin = Number((STATE.localDebug && STATE.localDebug.top1_margin) || 0);
        const transitionFastTrack =
            transitionPrimed
            && Number(confidence || 0) >= TRANSITION_FAST_TRACK_CONFIDENCE
            && currentTop1Margin >= TRANSITION_FAST_TRACK_MARGIN;
        const effectiveRequiredStability = transitionFastTrack
            ? 1
            : transitionPrimed
                ? Math.min(requiredStability, 2)
                : requiredStability;
        if (STATE.predictionHistory.length < effectiveRequiredStability) {
            updateDebugPanel();
            return;
        }
        const stableCandidate = getStableCandidateFromHistory(effectiveRequiredStability);
        if (!stableCandidate) {
            updateDebugPanel();
            return;
        }

        const now = Date.now();
        const normalizedStableCandidate = normalizeLabel(stableCandidate);
        const heldCommittedSign =
            Boolean(normalizedStableCandidate)
            && normalizedStableCandidate === STATE.activeCommittedGestureKey;
        if (heldCommittedSign) {
            recordRuntimeEvent("stable_candidate_suppressed", {
                candidate: stableCandidate,
                confidence: roundNumber(confidence),
                reason: "same_sign_hold",
            });
            return;
        }
        const repeatedTooSoon =
            stableCandidate === STATE.stablePrediction
            && normalizedStableCandidate === normalizeLabel(STATE.activeCommittedGestureKey || STATE.lastCommittedKey || "")
            && (now - STATE.lastStableAt) < REPEAT_SIGN_COOLDOWN_MS;
        if (repeatedTooSoon) {
            recordRuntimeEvent("stable_candidate_suppressed", {
                candidate: stableCandidate,
                confidence: roundNumber(confidence),
                reason: "cooldown",
            });
            return;
        }

        STATE.stablePrediction = stableCandidate;
        STATE.lastStableAt = now;
        recordRuntimeEvent("stable_candidate", {
            candidate: stableCandidate,
            confidence: roundNumber(confidence),
            required_stability: effectiveRequiredStability,
            prediction_history: STATE.predictionHistory.slice(),
        });
        if (meta) applyPredictionMeta(meta);
        setBadge(DOM.badgeStable, "Stable", "success");
        setStatus("Sign detected", "success");
        updateDebugPanel();
        if (typeof onStable === "function") {
            onStable(stableCandidate, confidence);
            return;
        }
        translatePrediction(stableCandidate, confidence).catch((error) => console.error(error));
    }

    function applyConfirmedTranslation(data, fallbackEnglish = "") {
        const englishText = titleCase((data && (data.english_text || data.prediction)) || fallbackEnglish || "");
        const translatedText = String((data && data.translated_text) || englishText || "").trim();
        if (!englishText || englishText === "No Sign Detected") return false;

        const now = Date.now();
        const normalized = normalizeLabel(englishText);
        const translatedKey = normalizeLabel(translatedText || englishText);
        const engineName = String((data && data.engine) || STATE.lastEngine || "");
        const duplicateCooldownMs = /backend/i.test(engineName)
            ? Math.max(REPEAT_SIGN_COOLDOWN_MS, BACKEND_DUPLICATE_SUPPRESSION_MS)
            : REPEAT_SIGN_COOLDOWN_MS;
        const repeatedCommitTooSoon =
            STATE.lastCommittedKey === normalized
            && STATE.lastCommittedTranslatedText === translatedKey
            && (now - STATE.lastCommittedAt) < duplicateCooldownMs;
        recordRuntimeEvent("translation_commit_decision", {
            english_text: englishText,
            translated_text: translatedText || englishText,
            duplicate_suppressed: repeatedCommitTooSoon,
            engine: STATE.lastEngine,
            reason: STATE.lastReason,
            duplicate_cooldown_ms: duplicateCooldownMs,
        });

        if (repeatedCommitTooSoon) {
            recordRuntimeEvent("translation_duplicate_suppressed", {
                english_text: englishText,
                translated_text: translatedText || englishText,
                reason: "cooldown",
                duplicate_cooldown_ms: duplicateCooldownMs,
            });
            updateDebugPanel();
            return false;
        }

        STATE.stablePrediction = englishText;
        STATE.lastStableAt = now;
        STATE.predictionHistory = [englishText];

        if (DOM.transcriptBox) {
            DOM.transcriptBox.innerText = englishText;
        }
        if (DOM.translatedBox) {
            DOM.translatedBox.innerText = translatedText || englishText;
        }

        setBadge(DOM.badgeStable, "Stable", "success");
        if (String((data && data.prediction_reliability_status) || "") === "caution") {
            setStatus("Supported sign detected. Hold it steady for best reliability.");
        } else {
            setStatus("Sign detected", "success");
        }

        STATE.lastTranslatedText = translatedText || englishText;
        STATE.lastCommittedKey = normalized;
        STATE.lastCommittedAt = now;
        STATE.lastCommittedTranslatedText = translatedKey;
        STATE.activeCommittedGestureKey = normalized;
        clearTransitionPrime();
        commitSessionPhrase(englishText, translatedText || englishText);
        checkChallenge(englishText);
        recordRuntimeEvent("translation_committed", {
            english_text: englishText,
            translated_text: translatedText || englishText,
            output_mode: STATE.outputMode,
            engine: STATE.lastEngine,
            reason: STATE.lastReason,
        });

        if (STATE.outputMode === "Audio") {
            speakText(translatedText || englishText).catch((error) => console.error(error));
        }
        updateDebugPanel();
        return true;
    }

    async function maybePredictLocal() {
        if (STATE.adaptiveMode === "fallback") {
            maybePredictFallback({ force: true }).catch((err) => console.error(err));
            return;
        }
        if (!hasUsableLocalModel() || STATE.sequenceBuffer.length < getLocalMinSequenceFrames() || STATE.inferenceBusy) return;
        const now = Date.now();
        if (now - STATE.lastInferAt < LOCAL_INFER_INTERVAL_MS) return;

        STATE.lastInferAt = now;
        STATE.inferenceBusy = true;

        try {
            const rawWindow = STATE.sequenceBuffer.slice(-SEQUENCE_LENGTH);
            if (!rawWindow.length) return;
            const paddedWindow = rawWindow.slice();
            const lastFrame = paddedWindow[paddedWindow.length - 1];
            while (paddedWindow.length < SEQUENCE_LENGTH) {
                paddedWindow.push(Array.isArray(lastFrame) ? lastFrame.slice() : lastFrame);
            }

            const inputData = projectSequenceForModel(paddedWindow);
            const inputTensor = tf.tensor3d([inputData], [1, SEQUENCE_LENGTH, STATE.inputFeatureSize]);
            const predTensor = STATE.model.predict(inputTensor);
            const probs = await predTensor.data();
            tf.dispose([inputTensor, predTensor]);

            let maxIdx = 0;
            for (let i = 1; i < probs.length; i += 1) {
                if (probs[i] > probs[maxIdx]) maxIdx = i;
            }
            const confidence = probs[maxIdx] || 0;
            const label = titleCase(STATE.labels[maxIdx] || `Class ${maxIdx}`);
            const threshold = getThresholdForLabel(label, getLocalConfidenceThreshold());
            const top3 = buildTopKPredictions(probs, STATE.labels, 3);
            const top1Margin = getTopPredictionMargin(top3);
            const sourceFrameCount = rawWindow.length;
            const usingPartialWindow = sourceFrameCount < SEQUENCE_LENGTH;
            const partialThreshold = usingPartialWindow
                ? Math.max(threshold, LOCAL_PARTIAL_CONFIDENCE_FLOOR)
                : threshold;
            const partialMarginRequired = usingPartialWindow ? LOCAL_PARTIAL_MARGIN_FLOOR : 0;

            STATE.localDebug = {
                model: "tfjs_lstm",
                input_tensor: {
                    shape: inputTensor.shape ? Array.from(inputTensor.shape) : [1, SEQUENCE_LENGTH, STATE.inputFeatureSize],
                    dtype: String(inputTensor.dtype || "float32"),
                },
                normalization: {
                    kind: "none",
                    raw_sequence_stats: summarizeNumericArray(rawWindow.flat()),
                    projected_sequence_stats: summarizeNumericArray(inputData.flat()),
                    feature_order: [
                        "pose[1404:1536]",
                        "left_hand[1536:1599]",
                        "right_hand[1599:1662]",
                    ],
                    padding: "repeat_last_frame",
                    truncation: "keep_last_frames",
                },
                output_kind: "softmax_probabilities",
                raw_probabilities: Array.from(probs).map((value) => roundNumber(value)),
                top3,
                predicted_class: label,
                confidence: roundNumber(confidence),
                confidence_threshold: roundNumber(partialThreshold),
                top1_margin: roundNumber(top1Margin),
                runtime_gate: {
                    fast_commit_enabled: LOCAL_FAST_COMMIT_EXPERIMENTAL,
                    trust_bridge_enabled: LOCAL_TRUST_BRIDGE_EXPERIMENTAL,
                    trust_min_confidence: LOCAL_TRUST_MIN_CONFIDENCE,
                    trust_min_margin: LOCAL_TRUST_MIN_MARGIN,
                    min_sequence_frames: getLocalMinSequenceFrames(),
                    partial_sequence: usingPartialWindow,
                    partial_margin_floor: partialMarginRequired,
                },
                sentence_buffer: {
                    frames: STATE.sequenceBuffer.length,
                    source_frames: sourceFrameCount,
                    stable_prediction: STATE.stablePrediction,
                    prediction_history: STATE.predictionHistory.slice(),
                },
            };
            recordRuntimeEvent("local_prediction", {
                predicted_class: label,
                confidence: roundNumber(confidence),
                confidence_threshold: roundNumber(partialThreshold),
                top1_margin: roundNumber(top1Margin),
                source_frames: sourceFrameCount,
                accepted: confidence >= partialThreshold && top1Margin >= partialMarginRequired,
                top3,
            });
            console.debug("[sign-debug][local]", STATE.localDebug);
            updateDebugPanel();
            const normalizedLabel = normalizeLabel(label);
            const activeGestureKey = normalizeLabel(STATE.activeCommittedGestureKey || "");
            const acceptedLocalPrediction = confidence >= partialThreshold && top1Margin >= partialMarginRequired;
            const alternateLabelDetected =
                Boolean(activeGestureKey)
                && Boolean(normalizedLabel)
                && normalizedLabel !== activeGestureKey;
            const softSignChange =
                alternateLabelDetected
                && acceptedLocalPrediction
                && confidence >= SIGN_CHANGE_SOFT_MIN_CONFIDENCE
                && top1Margin >= SIGN_CHANGE_SOFT_MIN_MARGIN;
            const strongSignChange =
                alternateLabelDetected
                && confidence >= SIGN_CHANGE_MIN_CONFIDENCE
                && top1Margin >= SIGN_CHANGE_MIN_MARGIN;

            if (softSignChange) {
                if (STATE.signChangeCandidate === normalizedLabel) {
                    STATE.signChangeCandidateCount += 1;
                } else {
                    STATE.signChangeCandidate = normalizedLabel;
                    STATE.signChangeCandidateCount = 1;
                }
                primeTransition(label, "adaptive_sign_change", confidence, top1Margin);

                if (strongSignChange && STATE.signChangeCandidateCount >= SIGN_CHANGE_CONFIRMATIONS) {
                    reprimeForSignChange(label, activeGestureKey, confidence, top1Margin, "strong_sign_change");
                    return;
                }
            } else if (!activeGestureKey || normalizedLabel === activeGestureKey) {
                resetSignChangeTracker();
            } else if (confidence < SIGN_CHANGE_SOFT_MIN_CONFIDENCE || top1Margin < SIGN_CHANGE_SOFT_MIN_MARGIN) {
                resetSignChangeTracker();
            }

            if (acceptedLocalPrediction) {
                registerCandidate(label, confidence, {
                    engine: "local_prediction",
                    model_ready: STATE.backendModelReady,
                    is_guess: false,
                    reason: usingPartialWindow ? "fast_local_english" : "",
                });
            } else if (!hasUsableLocalModel()) {
                maybePredictFallback({ force: true }).catch((err) => console.error(err));
            }
        } catch (error) {
            console.error(error);
        } finally {
            STATE.inferenceBusy = false;
        }
    }

    function captureCurrentFrameDataUrl() {
        if (!DOM.video || !DOM.video.videoWidth || !DOM.video.videoHeight) return "";

        const sourceWidth = Number(DOM.video.videoWidth || 0);
        const sourceHeight = Number(DOM.video.videoHeight || 0);
        if (!sourceWidth || !sourceHeight) return "";

        const scale = Math.min(1, FRAME_CAPTURE_MAX_WIDTH / sourceWidth);
        const targetWidth = Math.max(1, Math.round(sourceWidth * scale));
        const targetHeight = Math.max(1, Math.round(sourceHeight * scale));

        if (!STATE.frameCaptureCanvas) {
            STATE.frameCaptureCanvas = document.createElement("canvas");
        }
        const canvas = STATE.frameCaptureCanvas;
        canvas.width = targetWidth;
        canvas.height = targetHeight;

        const ctx = canvas.getContext("2d", { willReadFrequently: false });
        if (!ctx) return "";
        ctx.drawImage(DOM.video, 0, 0, targetWidth, targetHeight);
        return canvas.toDataURL("image/jpeg", 0.78);
    }

    async function maybePredictFallback(options = {}) {
        if (STATE.fallbackBusy || !shouldUseBackendSequenceFallback(options)) return;
        const now = Date.now();
        if (now - STATE.lastFallbackAt < getBackendFallbackInterval()) return;

        const requestEpoch = STATE.runtimeEpoch;
        STATE.lastFallbackAt = now;
        STATE.fallbackBusy = true;

        try {
            const currentFrame = shouldCaptureTranslationFrame() ? captureCurrentFrameDataUrl() : "";
            const response = await fetch("/predict-sign", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sequence: STATE.sequenceBuffer.slice(-getBackendSequenceLength()),
                    image_base64: currentFrame || undefined,
                    target_language: DOM.outLangSelect ? DOM.outLangSelect.value : "english",
                    debug: true,
                    min_confidence: getBackendMinConfidence({ trustLocalPrediction: false }),
                    allow_geometry_fallback: getAllowGeometryFallback(),
                    mode: STATE.adaptiveMode,
                    prefer_trained_translation: STATE.adaptiveMode !== "fallback",
                    allow_prediction_echo: STATE.adaptiveMode === "fallback",
                    use_isign_retrieval: STATE.adaptiveMode === "fallback",
                    sequence_priority: STATE.adaptiveMode === "fallback" ? "retrieval_first" : "lstm_first",
                    use_hf_image: Boolean(currentFrame),
                    use_fingerspell_router: STATE.adaptiveMode === "fallback",
                }),
            });
            if (!response.ok) throw new Error(`Fallback predict failed (${response.status})`);
            const data = await response.json();
            if (requestEpoch !== STATE.runtimeEpoch) return;
            applyPredictionMeta(data);
            const lowConfidence = isLowConfidenceResult(data) && STATE.adaptiveMode === "accuracy";
            recordRuntimeEvent("backend_prediction", {
                predicted_class: titleCase((data && (data.english_text || data.prediction)) || ""),
                translated_text: String((data && data.translated_text) || "").trim(),
                confidence: roundNumber(Number(data && (data.raw_confidence ?? data.confidence) || 0)),
                low_confidence: lowConfidence,
                engine: data && data.engine,
                reason: data && data.reason,
            });
            if (lowConfidence) {
                applyTentativeTranslationState(data);
                return;
            }
            registerCandidate(
                titleCase((data && (data.english_text || data.prediction)) || ""),
                Number(data && (data.raw_confidence ?? data.confidence) || 0),
                data,
                () => applyConfirmedTranslation(data)
            );
        } catch (error) {
            console.error(error);
        } finally {
            STATE.fallbackBusy = false;
        }
    }

    function checkChallenge(englishText) {
        if (!STATE.challengeWord || STATE.challengeSolved || !STATE.challengeSupported) return;
        const target = STATE.challengeWord.toLowerCase().replace(/_/g, " ").trim();
        const current = String(englishText || "").toLowerCase().replace(/_/g, " ").trim();
        if (!target || !current || target !== current) return;

        STATE.challengeSolved = true;
        if (DOM.challengeFeedback) DOM.challengeFeedback.style.display = "flex";

        fetch("/api/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ word: target }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (!DOM.challengeFeedback) return;
                DOM.challengeFeedback.innerHTML = `<i class="fas fa-check-circle" style="color: #4ade80;"></i> <span style="color: #fff; font-weight: bold;">Correct! +${data.points_earned || 0} XP</span>`;
            })
            .catch(() => {});
    }

    function resetRuntimeState() {
        STATE.runtimeEpoch += 1;
        STATE.sequenceBuffer = [];
        STATE.recentFrameBuffer = [];
        STATE.predictionHistory = [];
        STATE.stablePrediction = "";
        STATE.lastInferAt = 0;
        STATE.lastFallbackAt = 0;
        STATE.lastCandidateAt = Date.now();
        STATE.lastStableAt = 0;
        STATE.lastHandSeenAt = 0;
        STATE.lastNoHandStatusAt = 0;
        STATE.handDropFrames = 0;
        STATE.lastEngine = "none";
        STATE.lastReason = "";
        STATE.lastTranslationReqId = 0;
        STATE.latestAppliedReqId = 0;
        STATE.sessionSegments = [];
        STATE.lastSessionCommitAt = 0;
        STATE.lastCommittedKey = "";
        STATE.lastCommittedAt = 0;
        STATE.lastCommittedTranslatedText = "";
        STATE.activeCommittedGestureKey = "";
        resetSignChangeTracker();
        clearTransitionPrime();
        STATE.localDebug = {};
        STATE.backendDebug = {};
        setBadge(DOM.badgeStable, "Stable", "neutral");
        setBadge(DOM.badgeGuess, "Guess", "warn", false);
        setBadge(DOM.badgeHand, "No hand", "neutral");
        setBadge(DOM.badgeEngine, "Engine: none", "neutral");
        updateLiveSignalSummary({ engine: "none", reason: "", confidence: 0, isGuess: false });
        renderTopPredictions([]);
        renderSessionPhrase();
        updateDebugPanel();
    }

    if (STATE.challengeWord && DOM.challengeContainer && DOM.challengeTarget) {
        DOM.challengeContainer.style.display = "block";
        DOM.challengeTarget.innerText = STATE.challengeWord.replace(/_/g, " ");
    }

    if (typeof Holistic === "undefined" || typeof Camera === "undefined") {
        setStatus("MediaPipe failed to load. Check internet and refresh.", "error");
        if (DOM.signBtn) DOM.signBtn.disabled = true;
        if (DOM.stopBtn) DOM.stopBtn.disabled = true;
        return;
    }

    const holistic = new Holistic({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`,
    });

    holistic.setOptions({
        modelComplexity: 0,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        refineFaceLandmarks: false,
        minDetectionConfidence: 0.4,
        minTrackingConfidence: 0.35,
    });

    holistic.onResults((results) => {
        if (!STATE.isLive) return;

        if (DOM.canvas && DOM.video) {
            if (DOM.canvas.width !== DOM.video.videoWidth || DOM.canvas.height !== DOM.video.videoHeight) {
                DOM.canvas.width = DOM.video.videoWidth || 1280;
                DOM.canvas.height = DOM.video.videoHeight || 720;
            }
        }

        drawHands(results);
        const features = extractFeatures(results);
        const handPresent = Boolean(results.leftHandLandmarks || results.rightHandLandmarks) || hasHandSignal(features);

        if (!handPresent) {
            STATE.handDropFrames += 1;
            const withinGraceWindow =
                STATE.lastHandSeenAt > 0
                && (Date.now() - STATE.lastHandSeenAt) <= HAND_IDLE_MS
                && STATE.handDropFrames <= HAND_GRACE_FRAMES;

            if (withinGraceWindow) {
                setBadge(DOM.badgeHand, "Tracking...", "info");
                updateDetectionHeartbeat();
                return;
            }

            clearDetectionBuffers();
            setBadge(DOM.badgeStable, "Stable", "neutral");
            STATE.backendDebug = {
                route_result: {
                    engine: "no_hand",
                    reason: "no_hand",
                    prediction: "No sign detected",
                },
            };
            applyPredictionMeta({
                engine: "no_hand",
                reason: "no_hand",
                model_ready: STATE.backendModelReady,
                is_guess: false,
            });
            updateDetectionHeartbeat();
            return;
        }

        STATE.lastHandSeenAt = Date.now();
        STATE.handDropFrames = 0;
        setBadge(DOM.badgeHand, "Hand detected", "success");
        STATE.sequenceBuffer.push(features);
        if (STATE.sequenceBuffer.length > getBackendSequenceLength()) {
            STATE.sequenceBuffer.shift();
        }
        STATE.recentFrameBuffer.push(features);
        if (STATE.recentFrameBuffer.length > RECENT_FRAME_BUFFER_MAX) {
            STATE.recentFrameBuffer.shift();
        }

        if (hasUsableLocalModel()) {
            maybePredictLocal().catch((err) => console.error(err));
            if (shouldUseBackendSequenceFallback()) {
                maybePredictFallback().catch((err) => console.error(err));
            }
        } else {
            maybePredictFallback().catch((err) => console.error(err));
        }
        updateDetectionHeartbeat();
    });

    async function startCamera() {
        if (STATE.isLive || STATE.cameraInstance) return;
        try {
            STATE.cameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: CAMERA_WIDTH, height: CAMERA_HEIGHT } });
            if (DOM.video) {
                DOM.video.srcObject = STATE.cameraStream;
                await DOM.video.play().catch(() => {});
            }

            STATE.cameraInstance = new Camera(DOM.video, {
                onFrame: async () => {
                    if (STATE.isLive) {
                        await holistic.send({ image: DOM.video });
                    }
                },
                width: CAMERA_WIDTH,
                height: CAMERA_HEIGHT,
            });

            resetRuntimeState();
            STATE.isLive = true;
            STATE.lastCandidateAt = Date.now();
            STATE.lastHandSeenAt = Date.now();
            await STATE.cameraInstance.start();

            if (DOM.stopBtn) DOM.stopBtn.disabled = false;
            setStatus("Listening for signs...", "success");
            updateMetaLabels();
        } catch (error) {
            console.error(error);
            STATE.isLive = false;
            if (STATE.cameraStream) {
                STATE.cameraStream.getTracks().forEach((track) => track.stop());
                STATE.cameraStream = null;
            }
            setStatus("Camera error or permission denied.", "error");
        }
    }

    function stopCamera() {
        if (!STATE.isLive && !STATE.cameraInstance) return;
        STATE.isLive = false;

        if (STATE.cameraInstance) {
            STATE.cameraInstance.stop();
            STATE.cameraInstance = null;
        }
        if (STATE.cameraStream) {
            STATE.cameraStream.getTracks().forEach((track) => track.stop());
            STATE.cameraStream = null;
        }
        if (DOM.video) DOM.video.srcObject = null;
        if (DOM.ctx && DOM.canvas) DOM.ctx.clearRect(0, 0, DOM.canvas.width, DOM.canvas.height);

        stopSpeaking();
        resetRuntimeState();

        if (DOM.stopBtn) DOM.stopBtn.disabled = true;
        setStatus("Camera stopped.");
    }

    async function runSyntheticSequence(sequence, options = {}) {
        const frames = Array.isArray(sequence)
            ? sequence
                .filter((frame) => Array.isArray(frame))
                .map((frame) => expandSyntheticFrame(frame))
            : [];
        if (!frames.length) {
            throw new Error("Synthetic sequence is empty");
        }

        STATE.runtimeEvents = [];
        stopSpeaking();
        resetRuntimeState();
        STATE.sequenceBuffer = frames.slice(-getBackendSequenceLength());
        STATE.lastCandidateAt = Date.now() - 2000;
        STATE.lastHandSeenAt = Date.now();
        setBadge(DOM.badgeHand, "Hand detected", "success");
        const runStartPerf = window.performance && typeof window.performance.now === "function"
            ? window.performance.now()
            : 0;

        const requestedMode = String(options.outputMode || "Text").toLowerCase();
        if (requestedMode === "audio") {
            STATE.outputMode = "Audio";
            setModeAudio();
        } else {
            STATE.outputMode = "Text";
            setModeText();
        }

        if (options.targetLanguage && DOM.outLangSelect) {
            DOM.outLangSelect.value = String(options.targetLanguage).toLowerCase();
            updateMetaLabels();
        }

        const requestedEngine = String(options.engine || "backend").toLowerCase();
        recordRuntimeEvent("synthetic_run_started", {
            expected_label: titleCase(options.expectedLabel || ""),
            engine: requestedEngine,
            frame_count: frames.length,
            output_mode: STATE.outputMode,
            target_language: (DOM.outLangSelect && DOM.outLangSelect.value) || "english",
        });
        const repeats = Math.max(3, Number(options.repeats || 4));
        const delayMs = Math.max(0, Number(options.delayMs || (requestedEngine === "backend" ? 30 : LOCAL_INFER_INTERVAL_MS)));
        const hasSatisfiedOutcome = () => {
            const events = getRuntimeEventsSince(runStartPerf);
            const commitEvent = events.find((event) => event.type === "translation_committed");
            const speechTriggerEvent = events.find(
                (event) => event.type === "tts_request" || event.type === "tts_play" || event.type === "tts_browser_play"
            );
            return Boolean(commitEvent && (requestedMode !== "audio" || speechTriggerEvent));
        };
        for (let i = 0; i < repeats; i += 1) {
            if ((requestedEngine === "local" || requestedEngine === "auto") && hasUsableLocalModel()) {
                STATE.lastInferAt = 0;
                await maybePredictLocal();
                if (hasSatisfiedOutcome()) break;
            }
            if (
                requestedEngine === "backend"
                || (requestedEngine === "auto" && shouldUseBackendSequenceFallback())
            ) {
                STATE.lastFallbackAt = 0;
                await maybePredictFallback({ force: requestedEngine === "backend" });
                if (hasSatisfiedOutcome()) break;
            }
            if (delayMs > 0) {
                await new Promise((resolve) => window.setTimeout(resolve, delayMs));
                if (hasSatisfiedOutcome()) break;
            }
        }

        const outcome = await waitForRunCompletion(runStartPerf, Number(options.timeoutMs || 3000), requestedMode === "audio");
        const events = outcome.events || [];
        const stableEvent = events.find((event) => event.type === "stable_candidate") || null;
        const commitEvent = outcome.commitEvent || null;
        const speechTriggerEvent = outcome.speechTriggerEvent || null;
        const speechPlayEvent = outcome.speechPlayEvent || null;
        const latestPrediction = [...events].reverse().find(
            (event) => event.type === "local_prediction" || event.type === "backend_prediction"
        ) || null;
        const expectedNormalized = normalizeLabel(options.expectedLabel || "");
        const committedEnglish = String((commitEvent && commitEvent.english_text) || "").trim();
        const translatedText = String((commitEvent && commitEvent.translated_text) || (DOM.translatedBox ? DOM.translatedBox.innerText : "") || "").trim();
        const commitLatency = commitEvent ? roundNumber(commitEvent.perf_ms - runStartPerf, 2) : 0;
        const speechTriggerLatency = speechTriggerEvent ? roundNumber(speechTriggerEvent.perf_ms - runStartPerf, 2) : 0;
        const speechPlayLatency = speechPlayEvent ? roundNumber(speechPlayEvent.perf_ms - runStartPerf, 2) : 0;
        recordRuntimeEvent("synthetic_run_finished", {
            expected_label: titleCase(options.expectedLabel || ""),
            commit_result: Boolean(commitEvent),
            speech_result: Boolean(speechTriggerEvent),
            commit_latency_ms: commitLatency,
            speech_trigger_latency_ms: speechTriggerLatency,
            speech_play_latency_ms: speechPlayLatency,
            final_engine: STATE.lastEngine,
            final_reason: STATE.lastReason,
        });

        return {
            expected_label: titleCase(options.expectedLabel || ""),
            stable_prediction: STATE.stablePrediction,
            transcript: DOM.transcriptBox ? DOM.transcriptBox.innerText : "",
            translated: DOM.translatedBox ? DOM.translatedBox.innerText : "",
            session_phrase: STATE.sessionSegments.map((segment) => segment.translated).filter(Boolean).join(" ").trim(),
            output_mode: STATE.outputMode,
            last_engine: STATE.lastEngine,
            last_reason: STATE.lastReason,
            engine_requested: requestedEngine,
            predicted_class: latestPrediction ? String(latestPrediction.predicted_class || "") : "",
            predicted_confidence: latestPrediction ? roundNumber(Number(latestPrediction.confidence || 0), 4) : 0,
            commit_result: Boolean(commitEvent),
            translation_text: translatedText,
            tts_triggered: Boolean(speechTriggerEvent),
            stable_latency_ms: stableEvent ? roundNumber(stableEvent.perf_ms - runStartPerf, 2) : 0,
            commit_latency_ms: commitLatency,
            speech_trigger_latency_ms: speechTriggerLatency,
            speech_play_latency_ms: speechPlayLatency,
            duplicate_suppressions: events.filter((event) => event.type === "translation_duplicate_suppressed").length,
            correct_commit: Boolean(commitEvent) && (!expectedNormalized || normalizeLabel(committedEnglish) === expectedNormalized),
            runtime_events: events,
            backend_debug: STATE.backendDebug,
            local_debug: STATE.localDebug,
        };
    }

    async function runSyntheticBatch(sequenceMap, options = {}) {
        const entries = [];
        if (Array.isArray(sequenceMap)) {
            sequenceMap.forEach((row, index) => {
                if (row && Array.isArray(row.sequence)) {
                    entries.push({
                        label: String(row.label || row.expectedLabel || `sample_${index + 1}`),
                        sequence: row.sequence,
                    });
                }
            });
        } else if (sequenceMap && typeof sequenceMap === "object") {
            Object.entries(sequenceMap).forEach(([label, value]) => {
                if (Array.isArray(value) && Array.isArray(value[0]) && Array.isArray(value[0][0])) {
                    value.forEach((sequence) => {
                        entries.push({ label, sequence });
                    });
                } else if (Array.isArray(value)) {
                    entries.push({ label, sequence: value });
                }
            });
        }

        const attempts = [];
        for (let index = 0; index < entries.length; index += 1) {
            const entry = entries[index];
            const result = await runSyntheticSequence(entry.sequence, {
                ...options,
                expectedLabel: entry.label,
            });
            attempts.push({
                attempt: index + 1,
                label: titleCase(entry.label),
                ...result,
            });
        }

        const committed = attempts.filter((attempt) => attempt.commit_result);
        const correct = committed.filter((attempt) => attempt.correct_commit);
        const falsePositives = committed.length - correct.length;
        const duplicateSuppressions = attempts.reduce((sum, attempt) => sum + Number(attempt.duplicate_suppressions || 0), 0);
        const commitLatencies = committed.map((attempt) => Number(attempt.commit_latency_ms || 0)).filter((value) => value > 0);
        const speechTriggerLatencies = attempts.map((attempt) => Number(attempt.speech_trigger_latency_ms || 0)).filter((value) => value > 0);
        const speechPlayLatencies = attempts.map((attempt) => Number(attempt.speech_play_latency_ms || 0)).filter((value) => value > 0);

        return {
            attempts,
            metrics: {
                total_attempts: attempts.length,
                committed_attempts: committed.length,
                committed_accuracy: committed.length ? roundNumber(correct.length / committed.length, 4) : 0,
                false_positives: falsePositives,
                duplicate_suppressions: duplicateSuppressions,
                avg_commit_latency_ms: commitLatencies.length
                    ? roundNumber(commitLatencies.reduce((sum, value) => sum + value, 0) / commitLatencies.length, 2)
                    : 0,
                p95_commit_latency_ms: percentile(commitLatencies, 95),
                avg_speech_latency_ms: speechTriggerLatencies.length
                    ? roundNumber(speechTriggerLatencies.reduce((sum, value) => sum + value, 0) / speechTriggerLatencies.length, 2)
                    : 0,
                p95_speech_latency_ms: percentile(speechTriggerLatencies, 95),
                avg_tts_play_latency_ms: speechPlayLatencies.length
                    ? roundNumber(speechPlayLatencies.reduce((sum, value) => sum + value, 0) / speechPlayLatencies.length, 2)
                    : 0,
                p95_tts_play_latency_ms: percentile(speechPlayLatencies, 95),
            },
        };
    }

    async function runSyntheticSession(sequenceMap, options = {}) {
        const entries = [];
        if (Array.isArray(sequenceMap)) {
            sequenceMap.forEach((row, index) => {
                if (row && Array.isArray(row.sequence)) {
                    entries.push({
                        label: String(row.label || row.expectedLabel || `sample_${index + 1}`),
                        sequence: row.sequence,
                    });
                }
            });
        } else if (sequenceMap && typeof sequenceMap === "object") {
            Object.entries(sequenceMap).forEach(([label, value]) => {
                if (Array.isArray(value) && Array.isArray(value[0]) && Array.isArray(value[0][0])) {
                    value.forEach((sequence) => {
                        entries.push({ label, sequence });
                    });
                } else if (Array.isArray(value)) {
                    entries.push({ label, sequence: value });
                }
            });
        }

        STATE.runtimeEvents = [];
        stopSpeaking();
        resetRuntimeState();

        const requestedMode = String(options.outputMode || "Text").toLowerCase();
        if (requestedMode === "audio") {
            STATE.outputMode = "Audio";
            setModeAudio();
        } else {
            STATE.outputMode = "Text";
            setModeText();
        }

        if (options.targetLanguage && DOM.outLangSelect) {
            DOM.outLangSelect.value = String(options.targetLanguage).toLowerCase();
            updateMetaLabels();
        }

        const requestedEngine = String(options.engine || "backend").toLowerCase();
        const timeoutMs = Math.max(1000, Number(options.timeoutMs || 4500));
        const repeats = Math.max(3, Number(options.repeats || 4));
        const delayMs = Math.max(0, Number(options.delayMs || (requestedEngine === "backend" ? 30 : LOCAL_INFER_INTERVAL_MS)));
        const attempts = [];

        for (let index = 0; index < entries.length; index += 1) {
            const entry = entries[index];
            const frames = Array.isArray(entry.sequence)
                ? entry.sequence
                    .filter((frame) => Array.isArray(frame))
                    .map((frame) => expandSyntheticFrame(frame))
                : [];
            if (!frames.length) {
                attempts.push({
                    attempt: index + 1,
                    label: titleCase(entry.label),
                    commit_result: false,
                    error: "Synthetic sequence is empty",
                });
                continue;
            }

            clearDetectionBuffers();
            STATE.sequenceBuffer = frames.slice(-getBackendSequenceLength());
            STATE.lastCandidateAt = Date.now() - 2000;
            STATE.lastHandSeenAt = Date.now();
            setBadge(DOM.badgeHand, "Hand detected", "success");

            const runStartPerf = window.performance && typeof window.performance.now === "function"
                ? window.performance.now()
                : 0;
            recordRuntimeEvent("synthetic_session_step_started", {
                expected_label: titleCase(entry.label),
                engine: requestedEngine,
                frame_count: frames.length,
                attempt: index + 1,
            });

            const hasSatisfiedOutcome = () => {
                const events = getRuntimeEventsSince(runStartPerf);
                const commitEvent = events.find((event) => event.type === "translation_committed");
                const speechTriggerEvent = events.find(
                    (event) => event.type === "tts_request" || event.type === "tts_play" || event.type === "tts_browser_play"
                );
                return Boolean(commitEvent && (requestedMode !== "audio" || speechTriggerEvent));
            };

            for (let i = 0; i < repeats; i += 1) {
                if ((requestedEngine === "local" || requestedEngine === "auto") && hasUsableLocalModel()) {
                    STATE.lastInferAt = 0;
                    await maybePredictLocal();
                    if (hasSatisfiedOutcome()) break;
                }
                if (
                    requestedEngine === "backend"
                    || (requestedEngine === "auto" && shouldUseBackendSequenceFallback({ force: requestedEngine === "backend" }))
                ) {
                    STATE.lastFallbackAt = 0;
                    await maybePredictFallback({ force: requestedEngine === "backend" });
                    if (hasSatisfiedOutcome()) break;
                }
                if (delayMs > 0) {
                    await new Promise((resolve) => window.setTimeout(resolve, delayMs));
                    if (hasSatisfiedOutcome()) break;
                }
            }

            const outcome = await waitForRunCompletion(runStartPerf, timeoutMs, requestedMode === "audio");
            const commitEvent = outcome.commitEvent || null;
            const speechTriggerEvent = outcome.speechTriggerEvent || null;
            attempts.push({
                attempt: index + 1,
                label: titleCase(entry.label),
                commit_result: Boolean(commitEvent),
                stable_prediction: STATE.stablePrediction,
                translated: DOM.translatedBox ? DOM.translatedBox.innerText : "",
                session_phrase: getSessionPhraseText(),
                tts_triggered: Boolean(speechTriggerEvent),
                last_engine: STATE.lastEngine,
                last_reason: STATE.lastReason,
            });

            clearDetectionBuffers();
            await new Promise((resolve) => window.setTimeout(resolve, 60));
        }

        return {
            attempts,
            session_phrase: getSessionPhraseText(),
            runtime_events: STATE.runtimeEvents.slice(),
            output_mode: STATE.outputMode,
            last_engine: STATE.lastEngine,
            last_reason: STATE.lastReason,
        };
    }

    async function runContinuousSyntheticHold(sequence, options = {}) {
        const initial = await runSyntheticSequence(sequence, options);
        const requestedEngine = String(options.engine || initial.engine_requested || "backend").toLowerCase();
        const frames = Array.isArray(sequence)
            ? sequence
                .filter((frame) => Array.isArray(frame))
                .map((frame) => expandSyntheticFrame(frame))
            : [];
        const passes = Math.max(4, Number(options.passes || 8));
        const delayMs = Math.max(0, Number(options.delayMs || (requestedEngine === "backend" ? 30 : LOCAL_INFER_INTERVAL_MS)));
        const followupStartPerf = window.performance && typeof window.performance.now === "function"
            ? window.performance.now()
            : 0;

        recordRuntimeEvent("continuous_hold_started", {
            engine: requestedEngine,
            passes,
        });
        for (let index = 0; index < passes; index += 1) {
            STATE.sequenceBuffer = frames.slice(-getBackendSequenceLength());
            if ((requestedEngine === "local" || requestedEngine === "auto") && hasUsableLocalModel()) {
                STATE.lastInferAt = 0;
                await maybePredictLocal();
            }
            if (
                requestedEngine === "backend"
                || (requestedEngine === "auto" && (!STATE.lastCommittedAt || !hasUsableLocalModel()))
            ) {
                STATE.lastFallbackAt = 0;
                await maybePredictFallback({ force: true });
            }
            if (delayMs > 0) {
                await new Promise((resolve) => window.setTimeout(resolve, delayMs));
            }
        }

        const followupEvents = getRuntimeEventsSince(followupStartPerf);
        return {
            ...initial,
            repeated_prediction_events: followupEvents.filter((event) => event.type === "local_prediction" || event.type === "backend_prediction").length,
            followup_commits: followupEvents.filter((event) => event.type === "translation_committed").length,
            followup_tts_triggers: followupEvents.filter((event) => event.type === "tts_request").length,
            followup_tts_play_events: followupEvents.filter(
                (event) => event.type === "tts_play" || event.type === "tts_browser_play"
            ).length,
            duplicate_suppressions: followupEvents.filter((event) => event.type === "translation_duplicate_suppressed" || event.type === "stable_candidate_suppressed").length,
            followup_events: followupEvents,
        };
    }

    async function runContinuousSyntheticTransition(sequenceEntries, options = {}) {
        const entries = Array.isArray(sequenceEntries) ? sequenceEntries : [];
        STATE.runtimeEvents = [];
        stopSpeaking();
        resetRuntimeState();

        const requestedMode = String(options.outputMode || "Text").toLowerCase();
        if (requestedMode === "audio") {
            STATE.outputMode = "Audio";
            setModeAudio();
        } else {
            STATE.outputMode = "Text";
            setModeText();
        }

        if (options.targetLanguage && DOM.outLangSelect) {
            DOM.outLangSelect.value = String(options.targetLanguage).toLowerCase();
            updateMetaLabels();
        }

        const attempts = [];
        const requestedEngine = String(options.engine || "auto").toLowerCase();
        const frameDelayMs = Math.max(0, Number(options.delayMs || 18));
        const timeoutMs = Math.max(1000, Number(options.timeoutMs || 4000));

        for (let index = 0; index < entries.length; index += 1) {
            const entry = entries[index] || {};
            const frames = Array.isArray(entry.sequence)
                ? entry.sequence.filter((frame) => Array.isArray(frame)).map((frame) => expandSyntheticFrame(frame))
                : [];
            const expectedLabel = titleCase(entry.label || entry.expectedLabel || `segment_${index + 1}`);
            const runStartPerf = window.performance && typeof window.performance.now === "function"
                ? window.performance.now()
                : 0;

            recordRuntimeEvent("continuous_transition_started", {
                expected_label: expectedLabel,
                attempt: index + 1,
                frame_count: frames.length,
                engine: requestedEngine,
            });

            for (let frameIndex = 0; frameIndex < frames.length; frameIndex += 1) {
                const frame = frames[frameIndex];
                STATE.lastHandSeenAt = Date.now();
                setBadge(DOM.badgeHand, "Hand detected", "success");
                STATE.sequenceBuffer.push(frame);
                if (STATE.sequenceBuffer.length > getBackendSequenceLength()) {
                    STATE.sequenceBuffer.shift();
                }
                STATE.recentFrameBuffer.push(frame);
                if (STATE.recentFrameBuffer.length > RECENT_FRAME_BUFFER_MAX) {
                    STATE.recentFrameBuffer.shift();
                }

                if (requestedEngine === "auto" || requestedEngine === "local") {
                    STATE.lastInferAt = 0;
                    await maybePredictLocal();
                }
                if (requestedEngine === "backend") {
                    STATE.lastFallbackAt = 0;
                    await maybePredictFallback({ force: true });
                }
                if (frameDelayMs > 0) {
                    await new Promise((resolve) => window.setTimeout(resolve, frameDelayMs));
                }
            }

            const outcome = await waitForRunCompletion(runStartPerf, timeoutMs, requestedMode === "audio");
            attempts.push({
                attempt: index + 1,
                label: expectedLabel,
                commit_result: Boolean(outcome.commitEvent),
                stable_prediction: STATE.stablePrediction,
                translated: DOM.translatedBox ? DOM.translatedBox.innerText : "",
                session_phrase: getSessionPhraseText(),
                last_engine: STATE.lastEngine,
                last_reason: STATE.lastReason,
            });
        }

        return {
            attempts,
            session_phrase: getSessionPhraseText(),
            final_state: window.__SAMVAK_SIGN_DEBUG__ ? window.__SAMVAK_SIGN_DEBUG__.getState() : {},
        };
    }

    window.__SAMVAK_SIGN_DEBUG__ = {
        runSyntheticSequence,
        runSyntheticBatch,
        runSyntheticSession,
        runContinuousSyntheticHold,
        runContinuousSyntheticTransition,
        getState: () => ({
            stablePrediction: STATE.stablePrediction,
            lastTranslatedText: STATE.lastTranslatedText,
            sessionPhrase: getSessionPhraseText(),
            outputMode: STATE.outputMode,
            backendModelReady: STATE.backendModelReady,
            translationModelReady: STATE.translationModelReady,
            localModelReady: hasUsableLocalModel(),
            localEngineEnabled: STATE.localEngineEnabled,
            localEngineReason: STATE.localEngineReason,
            localEngineBackend: STATE.localEngineBackend,
            localSelfTest: STATE.localSelfTest,
            lastEngine: STATE.lastEngine,
            lastReason: STATE.lastReason,
            localDebug: STATE.localDebug,
            backendDebug: STATE.backendDebug,
            runtimeEvents: STATE.runtimeEvents.slice(),
        }),
    };

    if (DOM.signBtn) DOM.signBtn.addEventListener("click", () => {
        startCamera().catch((error) => console.error(error));
    });
    if (DOM.stopBtn) DOM.stopBtn.addEventListener("click", stopCamera);
    if (DOM.sessionClearBtn) {
        DOM.sessionClearBtn.addEventListener("click", () => {
            clearSessionPhrase();
        });
    }
    if (DOM.sessionSpeakBtn) {
        DOM.sessionSpeakBtn.addEventListener("click", () => {
            const phrase = getSessionPhraseText();
            if (!phrase) return;
            speakText(phrase).catch((error) => console.error(error));
        });
    }

    if (DOM.outLangSelect) {
        DOM.outLangSelect.addEventListener("change", () => {
            updateMetaLabels();
            clearSessionPhrase(true);
            persistUserPreferences({ sign_output_language: DOM.outLangSelect.value }).catch((error) => console.error(error));
            if (STATE.stablePrediction) {
                translatePrediction(STATE.stablePrediction, 1).catch((error) => console.error(error));
            }
        });
    }
    if (DOM.signLangSelect) {
        DOM.signLangSelect.addEventListener("change", () => {
            updateMetaLabels();
            persistUserPreferences({ sign_input_language: DOM.signLangSelect.value }).catch((error) => console.error(error));
        });
    }
    if (DOM.modeAccuracyBtn) {
        DOM.modeAccuracyBtn.addEventListener("click", () => {
            if (STATE.adaptiveMode !== "accuracy") {
                setAdaptiveMode("accuracy");
                resetRuntimeState();
                persistUserPreferences({ sign_detection_mode: "accuracy" }).catch((error) => console.error(error));
            }
        });
    }
    if (DOM.modeFallbackBtn) {
        DOM.modeFallbackBtn.addEventListener("click", () => {
            if (STATE.adaptiveMode !== "fallback") {
                setAdaptiveMode("fallback");
                resetRuntimeState();
                persistUserPreferences({ sign_detection_mode: "fallback" }).catch((error) => console.error(error));
            }
        });
    }

    const tabs = document.querySelectorAll(".tab-btn");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            const tabName = tab.getAttribute("data-tab");
            if (tabName === "translationTab") {
                STATE.outputMode = "Text";
                stopSpeaking();
                setModeText();
            } else {
                STATE.outputMode = "Audio";
                setModeAudio();
                const phrase = getSessionPhraseText();
                if (phrase) {
                    speakText(phrase).catch((error) => console.error(error));
                } else if (STATE.lastTranslatedText) {
                    speakText(STATE.lastTranslatedText).catch((error) => console.error(error));
                }
            }
        });
    });

    setAdaptiveMode("fallback", true);
    resetRuntimeState();
    startBackendStatusPolling();
    updateMetaLabels();
    setModeText();
    loadUserPreferences().catch((error) => console.error(error));
    loadModelMetadata()
        .catch((error) => console.error(error))
        .finally(() => {
            loadSentenceLabels()
                .catch((error) => console.error(error))
                .finally(() => {
                    refreshBackendStatus()
                        .catch((error) => console.error(error))
                        .finally(() => {
                            loadLocalModel()
                                .catch((error) => console.error(error))
                                .finally(() => {
                                    setStatus(
                                        hasUsableLocalModel() || STATE.backendModelReady
                                            ? "AI ready. Start camera."
                                            : "Preparing backend AI..."
                                    );
                                    updateDebugPanel();
                                });
                        });
                });
        });

    window.addEventListener("beforeunload", () => {
        if (STATE.backendStatusPollTimer) {
            window.clearInterval(STATE.backendStatusPollTimer);
            STATE.backendStatusPollTimer = null;
        }
        stopSpeaking();
    });
});
