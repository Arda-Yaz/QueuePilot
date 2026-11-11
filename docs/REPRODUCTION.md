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
also checks the selection's model hash and threshold. Existing historical reports
must be regenerated before the UI performance panel becomes available.

The CNN promotion margin in `routing.min_coverage_improvement` applies when both
models are eligible. Calibration-holdout comparisons use the same partition for
both backends. Tune-based CNN checkpoint selection and threshold selection retain
the existing experimental design; a new split design requires a separate experiment.

Remote pulls require DagsHub credentials; local reproduction from raw data does
not. Publishing models or deployment is a separate operation. Commit the new
lock, sidecars and reports together only after a successful complete run and
upload the corresponding model binaries before deploying that revision.

## Local verification on 11 November 2026

All 15 stages completed from raw input in `.checks/repro-clean` with empty
generated-output directories and a new DVC cache. The existing Python 3.12
environment was used for training. The initial fresh-install attempt failed to
resolve aiobotocore 3.9.0 in the restricted execution environment. That version
exists on official PyPI; the subsequent fresh installation below succeeded.
Full training was not repeated in the newly installed environment.

CNN early stopping occurred at epoch 12; the best tune Macro-F1 was 0.853467.
Thresholds are baseline 0.57 and CNN 0.77. Tune coverages are 83.8251% and
83.9088%; the configured two percentage point promotion margin retains baseline.
Test accuracy / routing coverage / accepted accuracy are 85.7531% / 82.5569% /
92.1559% for baseline and 84.1863% / 84.2490% / 91.0241% for CNN.

All four split ID lists and their order match the original artifacts. The
unchanged second DVC run skipped every stage; `dvc status --json` returned `{}`
in both the isolated workspace and the main workspace after copying outputs and
cache. A dry run after changing target accuracy scheduled both threshold stages
and selection. Real baseline, CNN and auto predictors returned matching model-info
reports and successful predictions. Original artifacts and lock are retained in
`.checks/before-reproduction`. The generated lock and artifacts are local;
remote model storage has not been updated.

Generated artifacts, reports and lock files use byte-preserving Git attributes so
checkout line-ending conversion cannot invalidate CNN sidecar hashes.

Ruff and strict mypy passed. The complete test suite subsequently passed outside
this session's restricted sandbox: **87 tests, 46 warnings in 8.47 seconds**.
The API-only suite passed 16 tests in 0.82 seconds. Direct model-info tests cover
both backends and missing, malformed and stale reports.

The earlier Windows TestClient timeout was reproduced with a bounded 22-second
probe and a thread dump. It blocks before application lifespan startup, in
`socket._fallback_socketpair -> accept`, called while asyncio creates its Windows
Proactor event loop. Running the same interpreter, dependencies and tests outside
the sandbox removes the stall. No application or event-loop workaround was
needed. Run Windows API tests from a normal local terminal (or an execution
context permitting loopback sockets); increasing HTTP/test timeouts does not
address this event-loop initialization restriction. Diagnostic evidence is in
`.checks/api-timeout-diagnostic.log`; the full-suite result is in
`.checks/full-tests-outside-sandbox.log`.

Hosted CI and Docker verification were not run here. Training metadata records
the repository HEAD; these local code changes were not committed before training.


## Fresh dependency installation verified on 11 November 2026

A new Python 3.12.10 venv was created at `.checks/fresh-install/.venv`, with
`include-system-site-packages = false`; its initial package list contained only
pip. Installations used official PyPI and the official PyTorch CPU index, with
network access permitted. No dependency versions or hashes were changed and no
packages were copied from the original environment. Verified cached wheels were
reused where available, which does not share installed packages between venvs.

On another Windows machine with Python 3.12, start from the repository root and
an unused `.venv` path:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/dev.txt --index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install --no-deps torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip check
$env:APP_ENV = "test"
$env:MLFLOW_TRACKING_ENABLED = "false"
.\.venv\Scripts\python.exe -m pytest -q
```

The fresh environment passed:

- `pip check`: no broken requirements.
- All 87 tests in 7.88 seconds (46 existing warnings).
- Actual Uvicorn startup and HTTP checks for baseline and CNN: health, API-key
  rejection, authenticated prediction, browser UI and Prometheus metrics.
- Real baseline, CNN and auto TestClient checks: matching model-info/health model
  hashes and successful predictions.
- DVC status: `{}` against the existing generated artifacts.

Imported FastAPI, scikit-learn, Torch and DVC paths were checked to be inside the
new venv. Verification logs are `.checks/fresh-verification.log`,
`.checks/fresh-install-dev.log` and `.checks/fresh-install-torch.log`.
This validates the Windows/Python 3.12 CPU development profile. Model binaries,
raw data and remote credentials remain separate inputs as documented above;
Linux, Docker and GPU installation were not part of this fresh-install check.
