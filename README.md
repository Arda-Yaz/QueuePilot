# QueuePilot

QueuePilot classifies IT support tickets into eight categories and routes low-confidence predictions to human review. It serves a calibrated TF-IDF / logistic regression baseline and TextCNN through FastAPI and the included browser UI.

[PORT_MAP.md](docs/PORT_MAP.md) maps the code organization. [SOURCE_MANIFEST.md](docs/SOURCE_MANIFEST.md) records artifacts, checks and known limitations. License terms are in [LICENSE](LICENSE).

## Local files

This workspace contains verified copies of both fitted models and the dataset. Binary models and raw data are excluded from Git.

| Path | Purpose |
| --- | --- |
| `artifacts/baseline.joblib` | Fitted calibrated baseline |
| `artifacts/cnn/textcnn.pt` | CNN state dictionary |
| `artifacts/cnn/{vocab,labels,config,artifact_manifest}.json` | Token IDs, label order, architecture and integrity checks |
| `data/raw/all_tickets_processed_improved_v3.csv` | Dataset for data tools and evaluation |
| `reports/data/*_ids.csv`, `data_manifest.json` | Persisted train, tune, calibration and test membership |
| `reports/metrics/model_selection.json` | Persisted backend selection |
| `reports/metrics/{baseline_selected_threshold,selected_threshold}.json` | Model-bound routing thresholds |

The dataset comes from [Kaggle](https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset). Both model binaries are stored in the [QueuePilot DagsHub repository](https://dagshub.com/Arda-Yaz/QueuePilot). With DagsHub authentication configured, download them using `python -m dvc pull artifacts/baseline.joblib artifacts/cnn/textcnn.pt`. In another checkout, obtain the dataset separately and compare file hashes with the manifest.

## Windows setup and serving

Dependency profiles are grouped under `requirements/`. `base` serves the baseline, `cnn` adds CNN runtime dependencies, `train` adds training/plotting tools, `mlops` covers DVC/MLflow, `dev` covers development checks, and `cuda` retains the GPU preparation profile. Each `.in` describes inputs and its `.txt` contains pinned packages and hashes. Technical documents are grouped under `docs/`.

The prepared `.venv` is ready for use. A fresh baseline environment can be created with Python 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/base.txt
$env:MODEL_BACKEND = "auto"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the UI and `/docs` for OpenAPI. `MODEL_BACKEND` accepts `auto`, `baseline` and `cnn`. Persisted `auto` selection resolves to baseline. Source thresholds are 0.57 for baseline and 0.76 for CNN. Equality with the threshold accepts automatic routing.

For CNN serving, use the source CNN dependency profile and pinned CPU PyTorch.

```powershell
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/cnn.txt
.venv\Scripts\python.exe -m pip install --no-deps torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip check
$env:MODEL_BACKEND = "cnn"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The verified development environment uses `requirements/dev.txt` followed by the same PyTorch command. Install that profile in a fresh environment. Each source lock is a complete profile and some shared pins differ between profiles. Local verification used CPU inference, Python 3.12.10, scikit-learn 1.9.0 and PyTorch 2.13.0+cpu. Source baseline metadata records Python 3.12.14.

Set environment variables before startup. `APP_ENV=production` requires `API_KEY`. Setting `API_KEY` also enables the `X-API-Key` check on `/predict` in other environments. Submit a ticket in a second terminal with the configured key.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict `
  -Headers @{ "X-API-Key" = "your-local-key" } `
  -ContentType "application/json" `
  -Body '{"text":"I cannot access the shared network drive"}'
```

Responses contain `category`, `confidence`, `threshold`, `needs_manual_review` and `top_3`. `/health` reports backend, hash and threshold. `/model-info` serves persisted baseline metrics. Prometheus monitoring is at `/metrics/`.

## Existing tools

These tools write generated artifacts and reports. Invoke the relevant stage deliberately.

| Task | Existing command |
| --- | --- |
| Prepare data | `python -m src.prepare_data` |
| Train | `python -m src.train_baseline` / `python -m src.train_cnn` |
| Tune predictions | `python -m src.evaluate_tune_baseline` / `python -m src.evaluate_tune_cnn` |
| Held-out calibration | `python -m src.evaluate_calibration_baseline` / `python -m src.evaluate_calibration_cnn` |
| Threshold selection | `python -m src.analyze_threshold_baseline` / `python -m src.analyze_threshold_cnn` |
| Test evaluation | `python -m src.evaluate_baseline` / `python -m src.evaluate_cnn` |
| Routing evaluation | `python -m src.evaluate_routing_baseline` / `python -m src.evaluate_routing` |
| Compare and select | `python -m src.compare_models` / `python -m src.select_model` |
| Evaluation sequence | `python -m src.run_evaluation_pipeline` |
| Error analysis | `python -m src.error_summary --model baseline` or `--model cnn` |
| Figures | `python -m src.plot_results` |
| API benchmark | `python scripts/benchmark.py --help` |

MLflow uses the existing `MLFLOW_TRACKING_ENABLED`, `MLFLOW_TRACKING_URI` and `MLFLOW_EXPERIMENT_NAME` variables. Other dependency profiles are in the source lock files. Container instructions are inherited in [docs/deploy.md](docs/deploy.md). The container entrypoint performs an authenticated DVC pull at startup.

## Verification

```powershell
.venv\Scripts\python.exe -m compileall -q src app scripts tests
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy src app tests
$env:APP_ENV = "test"
$env:MLFLOW_TRACKING_ENABLED = "false"
.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_ml_smoke.py
```

The last command passed 70 tests, including both real backends. The excluded source smoke test fits a synthetic model. Training execution count for this port is zero. Source-versus-port checks matched 20 texts per backend, API responses, data/split fingerprints, routing statistics and threshold CLI output lifecycles. Actual Uvicorn serving passed health, API-key, prediction, UI and metrics checks for both backends. These are compatibility checks. Inherited `reports/` metrics and figures retain upstream provenance.
