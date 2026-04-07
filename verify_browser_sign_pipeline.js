const fs = require("fs");
const path = require("path");

function resolveFirstPath(candidates, description) {
    for (const candidate of candidates) {
        if (!candidate) continue;
        if (fs.existsSync(candidate)) {
            return candidate;
        }
    }
    throw new Error(`Could not resolve ${description}`);
}

function parseArgs(argv) {
    const parsed = {};
    argv.forEach((arg) => {
        if (!arg.startsWith("--")) return;
        const eq = arg.indexOf("=");
        if (eq === -1) {
            parsed[arg.slice(2)] = "true";
            return;
        }
        parsed[arg.slice(2, eq)] = arg.slice(eq + 1);
    });
    return parsed;
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    const repoRoot = __dirname;
    const outputDir = path.join(repoRoot, "output");
    fs.mkdirSync(outputDir, { recursive: true });

    const playwrightCorePath = resolveFirstPath([
        process.env.PLAYWRIGHT_CORE_PATH,
        "C:/Users/navee/AppData/Local/npm-cache/_npx/31e32ef8478fbf80/node_modules/playwright-core",
    ], "playwright-core");
    const chromiumExecutable = resolveFirstPath([
        process.env.PLAYWRIGHT_CHROMIUM_PATH,
        "C:/Users/navee/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe",
    ], "Playwright Chromium executable");

    const { chromium } = require(playwrightCorePath);
    const browser = await chromium.launch({
        headless: String(args.headed || "false").toLowerCase() !== "true",
        executablePath: chromiumExecutable,
    });

    const url = args.url || "http://127.0.0.1:5056/sign-to-text";
    const sequenceUrl = args.sequenceUrl || "/static/debug/hardening_sequences_5x10.json";
    const outputMode = args.outputMode || "Audio";
    const targetLanguage = args.targetLanguage || "english";
    const engines = String(args.engines || "local,auto")
        .split(",")
        .map((value) => value.trim().toLowerCase())
        .filter(Boolean);
    const repeats = Math.max(3, Number(args.repeats || 10));
    const timeoutMs = Math.max(1000, Number(args.timeoutMs || 3200));
    const warmup = String(args.warmup || "true").toLowerCase() !== "false";

    const aggregate = {
        timestamp: new Date().toISOString(),
        url,
        sequence_url: sequenceUrl,
        output_mode: outputMode,
        target_language: targetLanguage,
        warmup,
        engines: {},
    };

    for (const engine of engines) {
        const page = await browser.newPage();
        await page.goto(url, { waitUntil: "networkidle" });

        const result = await page.evaluate(
            async ({ sequenceUrl: seqUrl, runEngine, requestedOutputMode, requestedLanguage, runRepeats, runTimeoutMs, shouldWarmup }) => {
                const payload = await fetch(seqUrl).then((response) => response.json());
                const sampleMap = {};
                for (const [label, entry] of Object.entries(payload.samples || {})) {
                    sampleMap[label] = (entry && entry.attempts) || [];
                }

                const labels = Object.keys(sampleMap);
                const firstLabel = labels[0] || "";
                const warmSequence = firstLabel && sampleMap[firstLabel] ? sampleMap[firstLabel][0] : null;
                if (shouldWarmup && warmSequence) {
                    await window.__SAMVAK_SIGN_DEBUG__.runSyntheticSequence(warmSequence, {
                        engine: runEngine,
                        outputMode: requestedOutputMode,
                        targetLanguage: requestedLanguage,
                        expectedLabel: firstLabel,
                        repeats: Math.min(6, runRepeats),
                        timeoutMs: runTimeoutMs,
                    });
                }

                const batch = await window.__SAMVAK_SIGN_DEBUG__.runSyntheticBatch(sampleMap, {
                    engine: runEngine,
                    outputMode: requestedOutputMode,
                    targetLanguage: requestedLanguage,
                    repeats: runRepeats,
                    timeoutMs: runTimeoutMs,
                });

                const duplicateChecks = [];
                for (const label of labels) {
                    const sequence = sampleMap[label] && sampleMap[label][0];
                    if (!sequence) continue;
                    duplicateChecks.push(await window.__SAMVAK_SIGN_DEBUG__.runContinuousSyntheticHold(sequence, {
                        engine: runEngine,
                        outputMode: requestedOutputMode,
                        targetLanguage: requestedLanguage,
                        expectedLabel: label,
                        passes: 8,
                        timeoutMs: runTimeoutMs,
                    }));
                }

                return {
                    state: window.__SAMVAK_SIGN_DEBUG__.getState(),
                    batch,
                    duplicateChecks,
                };
            },
            {
                sequenceUrl,
                runEngine: engine,
                requestedOutputMode: outputMode,
                requestedLanguage: targetLanguage,
                runRepeats: repeats,
                runTimeoutMs: timeoutMs,
                shouldWarmup: warmup,
            }
        );

        const engineMetricsPath = path.join(outputDir, `${engine}_engine_metrics.json`);
        const duplicateMetricsPath = path.join(outputDir, `${engine}_duplicate_check_metrics.json`);
        fs.writeFileSync(engineMetricsPath, JSON.stringify(result.batch, null, 2));
        fs.writeFileSync(duplicateMetricsPath, JSON.stringify({ checks: result.duplicateChecks }, null, 2));

        aggregate.engines[engine] = {
            metrics_file: path.relative(repoRoot, engineMetricsPath),
            duplicate_file: path.relative(repoRoot, duplicateMetricsPath),
            metrics: result.batch.metrics,
            duplicate_summary: result.duplicateChecks.map((row) => ({
                label: row.expected_label,
                followup_commits: row.followup_commits,
                followup_tts_triggers: row.followup_tts_triggers,
                followup_tts_play_events: row.followup_tts_play_events,
                duplicate_suppressions: row.duplicate_suppressions,
                last_engine: row.last_engine,
            })),
            self_test: result.state ? result.state.localSelfTest || null : null,
            local_model_ready: Boolean(result.state && result.state.localModelReady),
            local_engine_enabled: Boolean(result.state && result.state.localEngineEnabled),
            local_engine_reason: result.state ? result.state.localEngineReason || "" : "",
            local_engine_backend: result.state ? result.state.localEngineBackend || "" : "",
            last_engine: result.state ? result.state.lastEngine : "",
            last_reason: result.state ? result.state.lastReason : "",
        };

        await page.close();
    }

    const reportPath = path.join(outputDir, "browser_validation_report.json");
    fs.writeFileSync(reportPath, JSON.stringify(aggregate, null, 2));
    console.log(JSON.stringify(aggregate, null, 2));
    await browser.close();
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
