(function () {
    function getTfVersion() {
        if (!(window.tf && tf.version)) return "";
        return String(tf.version.tfjs || "");
    }

    function toErrorMessage(error) {
        if (!error) return "Unknown error";
        if (typeof error === "string") return error;
        if (error && typeof error.message === "string") return error.message;
        try {
            return JSON.stringify(error);
        } catch (_err) {
            return String(error);
        }
    }

    function normalizeShape(shape) {
        if (!Array.isArray(shape)) return [];
        return shape.map((value) => (value == null ? null : Number(value)));
    }

    function readPrimaryTensor(output) {
        if (Array.isArray(output)) {
            return output[0] || null;
        }
        return output || null;
    }

    async function runBackendSelfTest(modelUrl, backend) {
        const result = {
            backend: String(backend || ""),
            ok: false,
            error: "",
            modelUrl: String(modelUrl || ""),
            runtimeVersion: getTfVersion(),
            inputShape: [],
            outputShape: [],
            outputPreview: [],
        };

        let model = null;
        let inputTensor = null;
        let outputTensor = null;
        try {
            await tf.setBackend(backend);
            await tf.ready();

            model = await tf.loadLayersModel(modelUrl, { strict: true });
            const inputShape = normalizeShape(
                Array.isArray(model.inputs) && model.inputs[0]
                    ? model.inputs[0].shape
                    : []
            );
            if (inputShape.length < 3) {
                throw new Error(`Unexpected input shape: ${JSON.stringify(inputShape)}`);
            }

            const sequenceLength = Number(inputShape[1] || 0);
            const featureSize = Number(inputShape[2] || 0);
            if (sequenceLength <= 0 || featureSize <= 0) {
                throw new Error(`Invalid model contract: ${JSON.stringify(inputShape)}`);
            }

            inputTensor = tf.zeros([1, sequenceLength, featureSize], "float32");
            outputTensor = readPrimaryTensor(model.predict(inputTensor));
            if (!outputTensor || typeof outputTensor.data !== "function") {
                throw new Error("Model predict() did not return a tensor");
            }

            const outputData = Array.from(await outputTensor.data()).slice(0, 5);
            result.ok = true;
            result.inputShape = inputShape;
            result.outputShape = normalizeShape(outputTensor.shape);
            result.outputPreview = outputData.map((value) => Number(Number(value).toFixed(6)));
        } catch (error) {
            result.error = toErrorMessage(error);
        } finally {
            if (outputTensor && typeof outputTensor.dispose === "function") outputTensor.dispose();
            if (inputTensor && typeof inputTensor.dispose === "function") inputTensor.dispose();
            if (model && typeof model.dispose === "function") model.dispose();
        }

        return result;
    }

    async function runSelfTest(options = {}) {
        if (!(window.tf && tf.loadLayersModel)) {
            return {
                ok: false,
                error: "TensorFlow.js runtime unavailable",
                runtimeVersion: getTfVersion(),
                attempts: [],
            };
        }

        const modelUrl = String(options.modelUrl || "").trim();
        if (!modelUrl) {
            return {
                ok: false,
                error: "Missing modelUrl",
                runtimeVersion: getTfVersion(),
                attempts: [],
            };
        }

        const backends = Array.isArray(options.backends) && options.backends.length
            ? options.backends.map((value) => String(value || "").trim()).filter(Boolean)
            : ["webgl", "cpu"];

        const attempts = [];
        for (const backend of backends) {
            const attempt = await runBackendSelfTest(modelUrl, backend);
            attempts.push(attempt);
            if (attempt.ok && options.stopOnSuccess !== false) {
                break;
            }
        }

        const passedAttempt = attempts.find((attempt) => attempt.ok) || null;
        return {
            ok: Boolean(passedAttempt),
            runtimeVersion: getTfVersion(),
            modelUrl,
            attempts,
            passedBackend: passedAttempt ? passedAttempt.backend : "",
            error: passedAttempt ? "" : (attempts.map((attempt) => `${attempt.backend}: ${attempt.error}`).join(" | ") || "Self-test failed"),
        };
    }

    window.SamvakTfjsSelfTest = {
        runSelfTest,
    };
})();
