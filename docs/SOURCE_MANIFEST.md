# QueuePilot source and artifact manifest

Verified on 6 November 2026. Reference snapshot identifier is `fccd1d1430e5a601b07edd16fc832182b2432bbf`. Model training commit recorded in baseline metadata is `3f37f84e1bc4c5eaa677c2cae0645d67b6031e67`. License terms are in `LICENSE`.

## Provenance and local availability

The user supplied the two model binaries from `Desktop/Dosyalar` and the CSV from `Downloads/all_tickets_processed_improved_v3.csv`. They were copied into the runtime paths below. Baseline SHA-256 matches metadata and threshold, CNN SHA-256 matches its manifest and threshold, and raw data SHA-256 matches the data manifest. Model MD5 values also match `dvc.lock`. Model sidecars, split IDs, reports, figures and configuration came from the pinned Git snapshot. All runtime model/data assets are available locally. Model binaries and raw data are Git-ignored.

The active DVC endpoint is `https://dagshub.com/Arda-Yaz/QueuePilot.s3`. Both supplied model files were uploaded with `dvc push`. Each remote object was then read in full and its byte count and SHA-256 were verified against the local file. Baseline remote size is 53,099,876 bytes and CNN remote size is 5,235,529 bytes. Verified hashes appear in the table below. Container startup and artifact CI use this endpoint and require its DagsHub access token. Local credentials are stored in Git-ignored `.dvc/config.local`.

## Actual file hashes

These SHA-256 digests were computed from the local files. Reference code identity is anchored by snapshot `fccd1d1430e5a601b07edd16fc832182b2432bbf`. The local history groups the current files into 20 commits. Source agent settings and `skills-lock.json` were excluded.

| Runtime/configuration file | Bytes | SHA-256 |
| --- | --- | --- |
| `data/raw/all_tickets_processed_improved_v3.csv` | 14568920 | `044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4` |
| `artifacts/baseline.joblib` | 53099876 | `22d97863c792e6fd01431ae6fae42fe8547295253cc0cfc341a116eccf93e734` |
| `artifacts/baseline_metadata.json` | 975 | `179adfc1477f77c7c25d75f3744258bb5ac39dd30a6cdb23e59d554a78bfcdd8` |
| `artifacts/cnn/textcnn.pt` | 5235529 | `f2baea6b9a3a005b07436385eaeeec770773288e121e47e89aa33414a1b38111` |
| `artifacts/cnn/vocab.json` | 148126 | `746b6e3734db5864a36c84f8923548aa8734f8a87870d321abe109be6a06f43d` |
| `artifacts/cnn/labels.json` | 139 | `1f78ce5985b2b16642ea1fdf894d384f82512cbb0229a765a41bb922fed242e6` |
| `artifacts/cnn/config.json` | 265 | `6ae7cb2363aa98a328080e73259cda1952ead133f0e7e98214b7d0328a16f872` |
| `artifacts/cnn/artifact_manifest.json` | 349 | `4e10d655597f359d0a839f1afeeea6779f2b2932523ee92ce22896b70574536d` |
| `artifacts/cnn/cnn_metadata.json` | 860 | `0854ef843ad2105225ef7c8bb8b6cb284a13f03883ea46e77a32cb614822600e` |
| `reports/data/data_manifest.json` | 361 | `af6471f49989ce5f77fdfe376542c030f483f3f3d753f6c3fc6c9f4c0c72cba4` |
| `reports/data/train_ids.csv` | 2176528 | `a455c9642ce34ce1bf2230dcd87d095951961209379160214d9f57428a1ee50e` |
| `reports/data/tune_ids.csv` | 310638 | `dead36bab9399b00391ea9ad4a6058cb2144283928d480c1a51e718e6ae04f94` |
| `reports/data/calibration_ids.csv` | 311093 | `e44b7f9d87ec819daef9d7208d783fd8d3755a13403190f215da68b1ba27c877` |
| `reports/data/test_ids.csv` | 311158 | `fcff11bbc238d71eb4fb1b09f802ffe1aad55b4b7d669dde6463a7155b9f79d4` |
| `reports/metrics/baseline_selected_threshold.json` | 2233 | `84490880549b1db7208aca6ab16f65135dcd1ba47fd9db41d582e3d39555c1b5` |
| `reports/metrics/selected_threshold.json` | 2244 | `67ed10427c1c45c9f747b5cbfd9a5bae2a8e03c4077237a45dfa92114bbb8a9c` |
| `reports/metrics/model_selection.json` | 1354 | `2f396f92a77996ec8fb1d34406f8301999f3d3782158f6d825ba776f8b00f7ef` |
| `params.yaml` | 930 | `157af2f7abb947663db61d03acbcb9ab7c61478fe527720753a3ee816e6e26c2` |
| `.dvc/config` | 134 | `9609ac49b25fbce81c1773185436515bbc86b829718b45226682dd75a2bb57e2` |
| `dvc.yaml` | 7831 | `eb76ff63005b3316c259dbd16d210f9658c14f89da213a2a10e6f0566adce474` |
| `dvc.lock` | 18255 | `e511658e889dd1d562d3288d553950df3afa9866b80fabda1cce8fd78457ffa0` |

## Dependency profiles

Dependency profiles live in `requirements/`. Package constraints, pinned versions and wheel hashes retain their source values. Relative includes and generation-command comments use the new paths. Each lock describes a complete profile. Development and serving profiles pin some shared packages differently, including Prometheus and Uvicorn. The verified environment uses `requirements/dev.txt` and the source CI CPU PyTorch pin.

| Source lock | Actual SHA-256 |
| --- | --- |
| `requirements/cnn.txt` | `1b84baf9837c9f3156b8624b14c7346cd9b06511b44b441fec5c1b4a871bb7d5` |
| `requirements/cuda.txt` | `7b332e754aefb8eb15f0895ba94ae52b8a1e04ed369e69e7fef374cdf443fff1` |
| `requirements/dev.txt` | `c1b7890912a6a7cc1f0de882eb8acdca3628b40657a7294f204b5aaf7e828c3c` |
| `requirements/mlops.txt` | `167fbd1798950e82e6fb5c54ad5865dabe2930789383aeeb9d998f487ec02c48` |
| `requirements/train.txt` | `59b2980ac274c8aa3e761b95f6ec14631152da87de5fa554e29d1dd90dcf11ca` |
| `requirements/base.txt` | `4f92459ded75877f7e0b133db311f1dbab3055d6d0692cfddeeb34cd5dd10f09` |

Actual verification runtime was Python 3.12.10 on Windows with scikit-learn 1.9.0, numpy 2.5.2, pandas 2.3.3, joblib 1.5.3, torch 2.13.0+cpu, fastapi 0.141.1, uvicorn 0.52.3. Source baseline metadata records Python 3.12.14 and scikit-learn 1.9.0. Verification used CPU PyTorch.

## Verification and boundaries

- `compileall` passed for source, API, scripts and tests. `pip check`, `ruff check .` and strict `mypy src app tests` passed.
- 70 tests passed, including both real fitted backends and five additional boundary/lifecycle checks. Source tests and assertions are verbatim. `test_ml_smoke.py` was explicitly excluded because it calls `fit()` on synthetic data. Training execution count is zero.
- Source and QueuePilot produced identical predictions on 20 inputs per backend, including blank, long, whitespace and Unicode probes. Category, confidence, top-three ordering, threshold and review decision matched exactly on CPU.
- Differential checks also matched cleaned-data fingerprints, all four split-ID fingerprints, request validation/errors, health/model-info responses, token encoding boundaries, calibration metrics, threshold candidate tables, class statistics and both threshold CLI success/failure outputs. This checks compatibility on the inspected inputs.
- Actual Uvicorn entry points passed localhost checks for both backends with production API-key enforcement, predictions, health, UI and Prometheus metrics. TestClient needed execution outside the sandbox because Windows asyncio socket creation stalled inside it. The stalled diagnostic processes were stopped.
- The source locks emit Starlette/httpx and joblib/NumPy deprecation warnings. The 70-test run recorded 41 warnings. Dependency upgrades were outside this port's scope.
- Inherited metrics and figures under `reports/` describe upstream runs. This port performed compatibility verification. Comprehensive test-set performance evaluation, training, hyperparameter search, CUDA validation and Docker builds were outside the executed checks.

## Inherited snapshot gaps

The model storage migration registered existing `train_baseline` and `train_cnn` outputs with `dvc commit --force`. This updated their local dependency records and the baseline tune-metrics path. Model files retain the verified hashes above. Training execution count is zero. Other historical entries in `dvc.lock` retain older `val` stages and file paths while `dvc.yaml` and the Python entry points use `tune`. Historical lock references include source files/outputs absent from this Git snapshot. Current prediction CSVs and independent calibration report outputs are also absent from the snapshot and remain generated evaluation outputs. Their production commands are retained.

The source four-way split validator omits an error for one collective-exhaustiveness mismatch case. Its original behavior is retained. `/model-info` reads baseline metrics for either serving backend. The Docker entrypoint requests both model files through DVC at startup, including when only baseline is selected. Source configuration, error behavior and output artifacts were preserved. Model upload and authenticated remote reads are verified for the QueuePilot DagsHub endpoint. Docker startup and hosted CI execution remain unverified in this environment.
