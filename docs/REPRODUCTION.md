# Reproducing the pipeline

Use Python 3.12 and one complete dependency profile. The CI reference installs
`requirements/dev.txt` with `pip install --require-hashes`, then installs
`torch==2.13.0+cpu --no-deps` from the PyTorch CPU index. Run `pip check`.
The train profile alone does not provide the whole DVC toolchain. GPU runs require
a separately validated Torch/CUDA environment; identical seeds do not guarantee
identical CPU/GPU results.

The raw input is not downloaded by DVC. Supply
`data/raw/all_tickets_processed_improved_v3.csv` and verify SHA-256
`044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4`.
Do not resave or reorder the input. The historical split uses `0.667`, not `2/3`.
Expected sizes: train 33485, tune 4779, calibration 4786, test 4787.

Perform training in a separate checkout with no serving process using its outputs.
DVC removes a stage's outputs before rebuilding them. A failed threshold stage
removes its threshold; do not substitute an older threshold or lower the risk
target to make the run pass.

For a local run, set `APP_ENV=test`, `MLFLOW_TRACKING_ENABLED=false` and
`MPLBACKEND=Agg`. On Windows, set `DVC_SITE_CACHE_DIR` to a writable local cache
directory if the shared ProgramData cache is inaccessible. Activate the intended
environment so DVC's `python -m ...` commands use its interpreter.

Run `dvc repro --force --no-run-cache`, then `dvc repro` again without changes.
The second invocation should skip all stages. Inspect `dvc status` and lock changes.
Routing parameter edits must invalidate threshold/model-selection stages; edits to
shared source modules must invalidate their consumers. DVC tracks the dependency
profile, but cannot detect an unrecorded change to installed packages or hardware.

Keep models, CNN sidecars, thresholds, model selection, metric reports and the
generated lock together. `/model-info` requires all three reports for the loaded
backend to carry its model hash. Missing, malformed, historical unbound or stale
reports result in `available=false`. ECE/Brier use the independent calibration
holdout, while classification and routing use test data. Automatic backend loading
also checks the selection's model hash and threshold. The checked-in reports already have matching model hashes. This requirement
applies to missing or stale reports, rather than to every historical report.

The CNN promotion margin in `routing.min_coverage_improvement` applies when both
models are eligible. Calibration-holdout comparisons use the same partition for
both backends. Tune-based CNN checkpoint selection and threshold selection retain
the existing experimental design; a new split design requires a separate experiment.

Remote pulls require DagsHub credentials; local reproduction from raw data does
not. Publishing models or deployment is a separate operation. Commit the new
lock, sidecars and reports together only after a successful complete run and
upload the corresponding model binaries before deploying that revision.

## Source identity and current artifacts

New baseline and CNN training records include `git_commit`, `git_dirty`,
`source_tree_sha256` and `source_provenance`. The latter embeds the exact bytes
(base64) and SHA-256 of every Python file under `src`, dependency profile, and
`params.yaml`, `pyproject.toml` and `.gitattributes`. DVC separately records the
stage command, dependency contract and parameters in its lock. A dirty run is
recoverable from this snapshot without an uncommitted diff. Missing Git metadata
is recorded as null, rather than inventing a clean commit. Training fails before
publishing metadata if this source snapshot or HEAD changes during the run.
Data identity remains recorded separately as `dataset_sha256`; persisted split
IDs and environment versions are also required for reproduction. The source
snapshot is evidence of inputs, not a promise of bit-identical GPU execution.

The training stages explicitly depend on the snapshot's files. A regression
check requires dependency coverage when new source files are added. CNN params
are read at training start, after the snapshot, rather than at module import.

These fields apply to future runs. Existing model metadata is preserved as the
original training record: its `7ea2b768...` HEAD does not uniquely identify the
uncommitted source used for that run. Do not retroactively replace it with the
current commit or attach a newly captured source snapshot to an old model.

## CNN prediction provenance

`evaluate_cnn` produces `cnn_test_predictions.csv` and the accompanying
`cnn_test_predictions.provenance.json`. The record binds the CSV bytes to the
model, vocabulary, labels and config bytes. It is emitted only if the bundle
remains unchanged during inference. `evaluate_routing` checks that binding and
requires the threshold to reference the same model, before writing any report.
Missing, malformed or stale provenance is a hard error. Regenerate predictions
with the actual intended model; never manufacture a sidecar for an old CSV.
DVC tracks the model bundle and prediction provenance directly in the routing
stage. Existing ignored CSVs have no sidecar and are intentionally rejected.

## LF lock migration and verification

The historical run used CRLF bytes for four Python dependencies although Git
stores LF. The [migration record](history/2026-11-11-lock/migration.json) and both
original and LF locks retain that distinction. All original dependencies and
outputs were byte-checked, the four source pairs were checked for exact CRLF/LF
conversion and equal Python ASTs, and DVC 3.67.1 generated the LF lock with
`python -m dvc commit --force` in an isolated checkout. Only the 11 proven newline
records changed; outputs were inherited unchanged. This was a metadata migration,
not a new training execution. Do not use `dvc commit --force` to bless arbitrary
source changes or to hide a pending rerun.

Two separate LF Git checkouts of `b0eee7c17cdfe89ab4c2009657a9fb8f3f27405f`,
with the migrated lock, passed `dvc status --json` as `{}`. Missing raw data,
ignored prediction CSVs and cached models were supplied from local files only
after matching the original lock. The second checkout restored models using
`dvc checkout` from the verified local cache. This check did not pull from remote
storage and did not repeat training.

The current code also contains functional provenance changes. Its training and
CNN evaluation stages therefore correctly remain pending against the migrated
historical lock. The current workspace must not be presented as a newly completed
15-stage run. Preserve this state until a new experiment is authorized, then
regenerate the complete run and lock together in an isolated checkout.

For a future fully reproduced release, provide the raw CSV, run `dvc pull` for
cached models and regenerate the ignored `cache: false` prediction CSVs with their
matching provenance. Then require an empty `dvc status --json` in a fresh checkout
with an empty DVC state database. Artifact-only CI lacks raw data and ignored
predictions, so a full empty-status assertion there would not test this contract.

See [maintained release status](RELEASE_STATUS.md),
[archived local verification](history/2026-11-11-reproduction.md), and
[experiment design options](EXPERIMENT_DESIGN.md).
