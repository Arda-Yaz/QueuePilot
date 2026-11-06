# QueuePilot source map

Reference snapshot identifier is `fccd1d1430e5a601b07edd16fc832182b2432bbf`. The initial implementation was organized into 20 commits. Every original application, CLI, test and reporting module has a counterpart at its original path. `src` and `app` continue to be the import packages.

| Original responsibility | QueuePilot counterpart | Change |
| --- | --- | --- |
| `src.data.normalize_text`, preparation normalization | `src.ticket_text.normalize_text`, re-exported from `src.data` | Shared whitespace/lowercase implementation |
| `src.prepare_data._sha256_row_id`, loader row hashing | `src.ticket_text.ticket_id`, aliased by `src.prepare_data` | Same UTF-8 delimiter representation and full SHA-256 |
| Preparation partition construction | `src.prepare_data.split_partitions`, called by `main` | Three stratified calls retain order, seed and exact 0.30 / 0.667 / 0.50 parameters |
| `src.data.validate_persisted_splits` | Same function | Shared size-check loop retains check order and errors |
| Inference prediction types and `format_prediction` | `src.prediction`, re-exported from `src.inference` | Backend-independent presentation separated from model loading |
| CNN manifest checks | `src.inference.verify_cnn_artifacts` | Checks happen before sidecars and weights load |
| Predictor classes, factory, threshold loader and `calculate_sha256` | Original `src.inference` exports | Original entry points and hash binding |
| `src.cnn_data.encode_text`, `TicketDataset` | Same exports | Explicit encoding, truncation, padding and tensor construction |
| `src.textcnn.TextCNN.forward` | Same class and method | Named convolution, pooling and dropout stages with identical state-dict keys |
| `src.routing_utils` | Same exports | Explicit counts and bounds with original operation order |
| Two `analyze_threshold_*` CLIs | Original wrappers calling `src.threshold_analysis.run_threshold_analysis` | Shared workflow retains paths, console output, CSV/JSON fields and stale-threshold removal |
| Baseline estimator setup | `src.train_baseline.build_baseline_pipeline`, called by original training function | Construction separated from fitting and 5-fold sigmoid calibration |
| Tune and calibration CNN batch loops | `src.cnn_evaluation.predict_batches` | Shared ordered softmax/max loop |
| Five evaluation prediction tables | `src.evaluate.build_prediction_frame` | Shared column order and correctness calculation |
| API request/response classes | `app.schemas`, re-exported by `app.main` | Validation and OpenAPI structures separated from routes |
| Request monitoring | `app.main.monitor_requests` | Removed redundant catch-and-reraise, retained finally-based observations |
| Model winner selection | `src.select_model.select_candidate`, called by `main` | Eligibility, coverage ranking, macro-F1 tie-break and failure text extracted |
| Other training, evaluation, tracking, figures, error analysis, benchmark, UI, Docker and DVC files | Original paths | Source capabilities carried into QueuePilot |
| Root-level dependency files | `requirements/{base,cnn,cuda,dev,mlops,train}.{in,txt}` | Matching input/lock names with updated installer, Docker and CI paths, UTF-8 input files |
| Root-level technical documents | `docs/PORT_MAP.md`, `docs/SOURCE_MANIFEST.md` | Technical records grouped under `docs/` |

The project/package display name and browser/API title are QueuePilot. Public schema fields, environment keys, CLI arguments and output formats retain their source definitions. Existing tests and fixtures were carried over verbatim. `tests/test_port_contracts.py` adds threshold equality/tie and threshold-file lifecycle checks.

Source agent skills and `skills-lock.json` were excluded from the application import. Local reference, runtime and verification directories are excluded from Git and Docker build contexts.

The source DVC lock predates its tune-stage rename. Historical stage records and model hashes are retained for provenance. The source four-way collective-exhaustiveness validation has a missing error branch, and `/model-info` reads baseline reports even when CNN serves predictions. These source behaviors were retained during the port.
