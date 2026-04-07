# Samvak ML Workflow

## Overview
- Runtime uses a hybrid path: local TFJS inference first, backend fallback second.
- The production training path now targets a frozen `40`-class set with a `PoseHands-TCN` model.
- The trainer, runtime, and frontend all read shared metadata from:
  - `model_data/data_manifest.json`
  - `model_data/production_classes.json`
  - `static/models/model_registry.json`
  - `static/models/tfjs_lstm/class_thresholds.json`
- The backend translation path also reads:
  - `translation_model.keras`
  - `static/models/translation_registry.json`
  - `static/models/translation_vocab.json`
- The manifest now merges both:
  - `model_data/` for collected local clips
  - `dataset_imports/` for imported external datasets

## Current State
- The production pipeline is implemented.
- The current model trains and loads correctly.
- The current dataset is still below release quality gates. More clip collection is required.

## Dependencies
- MediaPipe currently works with:
```bash
pip install protobuf==4.25.3
```

## Data Collection
- Print the current backlog:
```bash
python collect_training_data.py --print-backlog
```
- Record new production clips:
```bash
python collect_training_data.py
```
- The collector records sequence clips, writes `.npy` clip files plus JSON sidecars, and refreshes:
  - `model_data/data_manifest.json`
  - `model_data/data_audit.json`

## External Dataset Import
- List built-in dataset profiles:
```bash
python import_external_data.py --print-profiles
```
- Rebuild the local raw `ISL_CSLRT_Corpus` safely through the same importer pipeline:
```bash
python preprocess_data.py --dry-run --limit 10
```
- If you explicitly want that rebuilt corpus to participate in training, write it under `dataset_imports/`:
```bash
python preprocess_data.py --use-training-root --only-production-classes
```
- Import a labeled video corpus organized as `input_root/<class_name>/<video files>`:
```bash
python import_external_data.py \
  --profile gov_isl_dictionary \
  --input-root path/to/extracted_dataset \
  --only-production-classes \
  --refresh-manifest
```
- Import using a CSV path-to-label file:
```bash
python import_external_data.py \
  --profile islvt_mendeley \
  --input-root path/to/dataset_root \
  --labels-csv path/to/labels.csv \
  --path-column path \
  --label-column label \
  --refresh-manifest
```
- Notes:
  - Imported clips go to `dataset_imports/`.
  - Every imported clip gets a sidecar with `source_dataset`, `license_tag`, `source_url`, `import_profile`, and source-path metadata.
  - Re-running the importer with the same dataset and source paths is deterministic and will skip existing clips unless `--overwrite` is used.
  - `--only-production-classes` is the safest default for demo reliability.

## Audit Progress
- Generate a fresh coverage report:
```bash
python audit_dataset.py --refresh-manifest
```
- Target collection goals per class:
  - `25` clips
  - `5` signers
  - `3` backgrounds
  - `2` camera angles

## Training
- Train the production model:
```bash
python train_lstm.py
```
- The trainer now filters manifest rows by license/source before class selection.
- Default allowed license tags:
  - `local_internal`
  - `government_open_data_india`
  - `cc_by_4_0`
- Override if needed:
```bash
$env:MODEL_ALLOWED_LICENSE_TAGS="local_internal,government_open_data_india,cc_by_4_0"
python train_lstm.py
```
- Outputs:
  - `sign_language.h5`
  - `static/models/tfjs_lstm/model.json`
  - `static/models/tfjs_lstm/labels.json`
  - `static/models/tfjs_lstm/class_thresholds.json`
  - `static/models/model_registry.json`

## Translation Training
- The translation trainer now supports two modes:
  - `sequence`, preferred for imported sentence-level datasets such as `iSign` and `ISLTranslate`
  - `image`, kept as a fallback for small phrase-labeled image sets
- Auto mode prefers sentence-level sequence data when the shared manifest contains imported translation clips.
- Sequence training now supports two model families:
  - `sequence_classification` for frozen phrase sets
  - `sequence_ctc` for open-ended sentence corpora such as `iSign`
- If you do not set `TRANSLATION_ALLOWED_SOURCE_DATASETS`, the trainer now prefers `iSign` first and `ISLTranslate` second when both are present in the manifest.
- Import a sentence-level dataset first:
```bash
python import_translation_dataset.py --profile isign_video_research --input-root path/to/iSign --refresh-manifest
```
- Preferred `iSign` bootstrap path:
```bash
python bootstrap_isign_translation.py --input-root path/to/iSign
```
- The bootstrap script defaults to `isign_pose_research`, trains a `sequence_ctc` backend, restricts training to `source_dataset=isign`, and runs the realtime/site verifiers afterward.
- If you need raw videos instead of pose files:
```bash
python bootstrap_isign_translation.py --profile isign_video_research --input-root path/to/iSign
```
- Or use the smaller ISLTranslate profile:
```bash
python import_translation_dataset.py --profile isltranslate_repo --input-root path/to/ISLTranslate --refresh-manifest
```
- Collect or import phrase-labeled images into `Tensorflow/workspace/images/collectedimages` only if you explicitly want image fallback training:
```bash
python collect_images.py --source-mode local-frames
```
- One-shot auto pipeline:
```bash
python run_translation_pipeline.py --source-kind auto
```
- Force sequence training:
```bash
python run_translation_pipeline.py --source-kind sequence
```
- Force the sequence trainer to use CTC explicitly:
```bash
$env:TRANSLATION_SEQUENCE_MODEL_TYPE="ctc"
python train_translation.py
```
- Force phrase-set classification explicitly:
```bash
$env:TRANSLATION_SEQUENCE_MODEL_TYPE="classification"
python train_translation.py
```
- Build the frozen production phrase set and audit the translation corpus:
```bash
python audit_translation_dataset.py --refresh-manifest
```
- If you are using the local `ISL_CSLRT_Corpus`, backfill signer metadata from the raw frame folders before retraining:
```bash
python backfill_isl_cslrt_metadata.py
python audit_translation_dataset.py --refresh-manifest
```
- If you are importing production translation clips, require signer metadata:
```bash
python import_translation_dataset.py --profile isign_video_research --input-root path/to/iSign --require-signer --refresh-manifest
```
- Force the old image trainer:
```bash
python run_translation_pipeline.py --source-kind image --image-root Tensorflow/workspace/images/collectedimages
```
- Train the backend translation model directly:
```bash
python train_translation.py
```
- Optional environment overrides:
  - `TRANSLATION_IMAGE_ROOT`
  - `TRANSLATION_IMAGE_SIZE`
  - `TRANSLATION_MIN_IMAGES_PER_TEXT`
  - `TRANSLATION_EPOCHS`
  - `TRANSLATION_BATCH_SIZE`
  - `TRANSLATION_FINE_TUNE_EPOCHS`
- Additional sequence overrides:
  - `TRANSLATION_SEQUENCE_MODEL_TYPE`
  - `TRANSLATION_PREFERRED_SOURCE_DATASETS`
  - `TRANSLATION_ALLOWED_SOURCE_DATASETS`
- `collect_images.py` still defaults to image-only collection.
- Preferred translation model type:
  - sign sequence -> phrase/sentence label
- `iSign` and `ISLTranslate` should use `sequence_ctc` unless you intentionally collapse them to a small frozen phrase set.
- Image mode remains available, but it is not the recommended path for sentence translation.
- Outputs:
  - `translation_model.keras`
  - `static/models/translation_vocab.json`
  - `static/models/translation_registry.json`
  - `model_data/translation_data_audit.json`
  - `model_data/translation_phrase_set.json`
- Runtime behavior:
  - `/predict-sign` uses the sequence translation model when the translation registry declares a sequence model.
  - `/predict-sign` uses the supplied `image_base64` frame only when the translation registry declares an image model.
  - If translation is unavailable or low-confidence, backend classification/fallback logic still applies.
  - If `model_data/translation_phrase_set.json` exists, sequence training now restricts itself to that frozen phrase set and requires signer/session metadata for those phrases.
  - `verify_translation_dataset.py` treats missing signer/session metadata or missing signer-disjoint validation/test coverage as blocking issues. Lower clip/session counts remain warnings until new data is collected.

## Verification
- Realtime/API verification:
```bash
python verify_realtime.py
```
- Site verification:
```bash
python verify_site.py
```
- Translation dataset verification:
```bash
python verify_translation_dataset.py
```

## Release Criteria
- Offline gates:
  - Top-1 `>= 0.85`
  - Macro-F1 `>= 0.80`
  - Per-class precision floor `>= 0.75`
- If the registry evaluation in `static/models/model_registry.json` is below those gates, do not treat the model as production-ready.
