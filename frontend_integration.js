
// frontend_integration.js
// Logic for Client-Side Sign Language Recognition (TFJS + MediaPipe)

let model = null;
let labels = []; // Load this dynamically or hardcode for now based on training

// --- 1. Load Model ---
async function loadModel() {
    console.log("⏳ Loading TFJS Model...");
    try {
        // Adjust path to where you saved the model.json
        model = await tf.loadLayersModel('/static/models/tfjs_lstm/model.json');
        console.log("✅ Model Loaded Successfully!");

        // OPTIONAL: Warm up model
        // model.predict(tf.zeros([1, 30, 1662])).dispose();

    } catch (err) {
        console.error("❌ Failed to load model:", err);
    }
}

// --- 2. Prediction Logic ---
// This function should be called inside your existing MediaPipe `onResults` loop
// We need to maintain a history of frames for the LSTM (Sequence Length = 30)

let sequence = [];

async function predictSign(results) {
    if (!model) return;

    // A. Extract Landmarks (Must match Python `extract_keypoints`)
    const keypoints = extractKeypoints(results);

    // B. Manage Sequence Window
    sequence.push(keypoints);
    if (sequence.length > 30) {
        sequence.shift(); // Keep last 30 frames
    }

    // C. Predict when we have enough frames
    if (sequence.length === 30) {
        // Convert to Tensor: Shape [1, 30, 1662]
        const inputTensor = tf.tensor3d([sequence]);

        const prediction = model.predict(inputTensor);
        const data = await prediction.data();
        const maxProbIndex = data.indexOf(Math.max(...data));

        prediction.dispose(); // Cleanup tensor memory!
        inputTensor.dispose();

        const predictedClass = labels[maxProbIndex];
        const confidence = data[maxProbIndex];

        // D. Threshold & Update UI
        if (confidence > 0.7) {
            console.log(`🤟 Prediction: ${predictedClass} (${(confidence * 100).toFixed(1)}%)`);
            updateUI(predictedClass, confidence);
        }
    }
}

function extractKeypoints(results) {
    // Helper to flattening arrays
    const getCoords = (res) => res ? [res.x, res.y, res.z] : [0, 0, 0];
    const getPoseCoords = (res) => res ? [res.x, res.y, res.z, res.visibility] : [0, 0, 0, 0];

    // Face (1404)
    let face = new Array(1404).fill(0);
    if (results.faceLandmarks) {
        face = results.faceLandmarks.flatMap(getCoords);
    }

    // Pose (132)
    let pose = new Array(132).fill(0);
    if (results.poseLandmarks) {
        pose = results.poseLandmarks.flatMap(getPoseCoords);
    }

    // Left Hand (63)
    let lh = new Array(63).fill(0);
    if (results.leftHandLandmarks) {
        lh = results.leftHandLandmarks.flatMap(getCoords);
    }

    // Right Hand (63)
    let rh = new Array(63).fill(0);
    if (results.rightHandLandmarks) {
        rh = results.rightHandLandmarks.flatMap(getCoords);
    }

    return [...face, ...pose, ...lh, ...rh];
}

function updateUI(label, confidence) {
    // Update your existing UI elements here
    const transcriptBox = document.getElementById("signTranscript");
    if (transcriptBox) {
        transcriptBox.innerText = label;
        transcriptBox.style.color = "#22c55e";
    }
}

// Export functions if using modules, or just expose globally
window.loadModel = loadModel;
window.predictSign = predictSign;
