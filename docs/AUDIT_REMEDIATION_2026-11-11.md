# Second-audit remediation verification: 11 November 2026

The initial workspace was clean. HEAD exactly matched the audited commit,
`b0eee7c17cdfe89ab4c2009657a9fb8f3f27405f`. No pre-existing user changes were
overwritten. The report was treated as a source of hypotheses and checked
against local code, file bytes, DVC and executable tests.

## Executed checks

| Check | Result and scope |
| --- | --- |
| Historical lock dependencies and outputs | Byte-verified the original dependencies and all 34 stage outputs. Four Python sources accounted for exactly 11 CRLF/LF MD5 and size mismatches in a fresh checkout. |
| LF migration | DVC 3.67.1 generated the lock using `python -m dvc commit --force` after strict newline-only validation. Only those 11 records changed; original lock and migration script are archived. This was not training. |
| Two isolated Git checkouts | Audited LF sources plus the migrated lock and locally supplied, hash-verified raw data, ignored CSVs and models yielded `dvc status --json` equal to `{}`. The second checkout restored models from the verified local cache. No remote pull was used. |
| Initial focused regressions | 70 tests passed before the final three test cases were added. This included existing split, model-info and model-selection regressions. |
| New provenance tests | The final suite includes 23 cases for recoverable source bytes, missing Git, dirty-state recording, mid-run source changes, real baseline fitting and one real CNN epoch on synthetic data, stale prediction/bundle rejection, threshold/model matching, DVC contracts and LF migration. |
| Real CNN evaluation and routing | In an isolated checkout, the preserved CNN predicted all 4,787 test tickets, emitted its provenance sidecar, and passed routing validation. Both regenerated JSON reports exactly matched the preserved reports. The main workspace reports were not replaced. |
| Complete test suite | `APP_ENV=test`, `MLFLOW_TRACKING_ENABLED=false`, `.venv/Scripts/python.exe -m pytest -q`: **110 passed, 46 existing dependency warnings, 11.04 seconds**. Run outside the restricted sandbox to allow Windows loopback/event-loop initialization. |
| Static checks | Ruff and strict `mypy src/ app/ tests/` passed. |
| Output preservation | Rechecked all 34 original pipeline output SHA-256 values after changes and the isolated real-model evaluation: all unchanged, including model binaries, split IDs, metadata, thresholds, figures and metric reports. |
| Hosted evidence | Independently read GitHub run 43068533833 metadata, job summaries and artifact-job logs: all three jobs succeeded, two models were fetched, hashes passed, and 14 model integration tests passed. The run's source tree equals the audited tree. These are historical hosted checks, not a CI run of the current edits. |

Detailed local-only execution records live in `.checks/audit-lf-checkout`,
`.checks/audit-lf-verification` and `.checks/audit-real-cnn-verification.json`.
The first checkout retains the historical LF migration state; the second was
subsequently overlaid with the new source for the CNN replay, after its historical
empty-status check. The durable migration evidence is in
[`docs/history/2026-11-11-lock`](history/2026-11-11-lock/).

## Code findings and unexecuted work

Code inspection confirms checkpoint selection and threshold selection share the
persisted tune set. No new split experiment or full production-data training run
was performed. [Design options](EXPERIMENT_DESIGN.md) describe label and compute
costs separately. Existing model metadata retains its incomplete historical
source identity; the new recoverable format was exercised with synthetic models
and applies to future training runs. It was not attached to old models.

Current DVC status correctly lists `train_baseline`, `train_cnn`, `evaluate_cnn`
and `evaluate_routing_cnn` as changed or missing new outputs. The historical LF
check's empty status does not apply to these functional changes. No arbitrary
dependency hashes were updated to make those stages appear current.

The CI workflow now runs on `codex/**` pushes and includes the new regressions
and a narrow newline-only source/lock check. It does not assert full pipeline cleanliness without the raw
CSV and ignored prediction/provenance inputs. A future complete run must produce
its own lock, source snapshots and artifacts before that full clean-checkout
assertion can pass. No new hosted CI run, Docker build, deployment, remote-model
upload, push or merge was performed in this remediation. The user subsequently
authorized local commits; the changes and their regression tests were grouped
into separate commits on `codex/audit-provenance-fixes`.

## Pre-commit verification

The 23 audit regression cases were reorganized without changing their assertions
into `test_lock_migration.py`, `test_training_provenance.py`,
`test_prediction_provenance.py` and `test_dvc_provenance_contracts.py`. The full
suite was repeated after the move: **110 passed, 46 existing warnings in
10.92 seconds**. Ruff, strict mypy (49 source files) and `git diff --check`
passed. All 34 preserved pipeline output hashes still matched.
