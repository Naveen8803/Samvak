$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$projectRoot = "e:\sam"
$bundleRoot = "e:\sam_runtime_bundle_$timestamp"
$zipPath = "e:\sam_runtime_bundle_$timestamp.zip"

$items = @(
    "app.py",
    "auth.py",
    "config.py",
    "dictionary.py",
    "extensions.py",
    "models.py",
    "sign.py",
    "speech.py",
    "model_assets.py",
    "fingerspell_recognizer.py",
    "geometry_brain.py",
    "grammar_helper.py",
    "requirements.txt",
    "README_ML.md",
    "verify_realtime.py",
    "verify_site.py",
    "verify_speech.py",
    "verify_supported_signs.py",
    "verify_translation_dataset.py",
    "sign_language.h5",
    "translation_model.keras",
    "templates",
    "static",
    "model_data\production_classes.json",
    "model_data\data_audit.json",
    "model_data\translation_data_audit.json",
    "model_data\translation_phrase_set.json",
    "model_data\isign_retrieval_index.npz",
    "model_data\isign_retrieval_meta.json"
)

New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null

foreach ($item in $items) {
    $source = Join-Path $projectRoot $item
    if (!(Test-Path $source)) {
        continue
    }

    $dest = Join-Path $bundleRoot $item
    if (Test-Path $source -PathType Container) {
        Copy-Item -Path $source -Destination $dest -Recurse -Force
        continue
    }

    $destDir = Split-Path -Parent $dest
    if ($destDir -and !(Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Path $source -Destination $dest -Force
}

$note = @"
Samvak runtime bundle

Run on another Windows device:
1. Extract this zip.
2. Create a venv and install requirements:
   pip install -r requirements.txt
3. Start the app:
   python -m app

Included:
- active Flask app code
- templates and static assets
- active sign and translation model files
- retrieval index needed by sign-to-text
- verification scripts

Not included:
- training datasets
- temporary output folders
- external archives
- SQLite user database
"@

Set-Content -Path (Join-Path $bundleRoot "RUN_ON_OTHER_DEVICE.txt") -Value $note -Encoding UTF8

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path $bundleRoot -DestinationPath $zipPath -Force

$zipSizeMb = [math]::Round(((Get-Item $zipPath).Length / 1MB), 2)
Write-Output "BUNDLE_DIR=$bundleRoot"
Write-Output "ZIP_PATH=$zipPath"
Write-Output "ZIP_SIZE_MB=$zipSizeMb"
