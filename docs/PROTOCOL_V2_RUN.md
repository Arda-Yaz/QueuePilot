# Protocol v2 execution and verification

The experiment was authorized after reviewing data and training costs. Raw data,
Python 3.12.10, scikit-learn 1.9.0, PyTorch 2.13.0 CPU and DVC 3.67.1 were
available locally. No new data, credentials, paid compute or GPU was required.

## Executed experiment

Training source: `80092e8` on `codex/audit-provenance-fixes`. Execution used an
isolated Git checkout, a fresh DVC cache, four OMP/MKL threads, disabled MLflow
tracking and the predeclared [v2 protocol](SELECTION_PROTOCOL.md).

The 47,837 cleaned tickets were divided into train 33,485, checkpoint 2,389,
risk/tune 2,390, calibration 4,786 and test 4,787. Historical train, calibration
and test ID files were byte-identical. Checkpoint and risk are disjoint and their
union exactly equals historical tune. Seed, model hyperparameters, target 0.90,
alpha 0.05 and 90-candidate threshold grid were not adjusted after viewing results.

CNN stopped after epoch 9; epoch 6 supplied the best checkpoint Macro-F1,
0.8547719742. Baseline checkpoint Macro-F1 was 0.8689780210, so baseline was
frozen before risk threshold analysis. Its risk threshold is 0.60 with coverage
0.8066945607, accepted accuracy about 0.9263 and simultaneous lower bound about
0.9050. The CNN comparison threshold is 0.84. Its risk results did not influence
the frozen backend decision.

| Backend | Threshold | Test accuracy | Test coverage | Accepted test accuracy |
| --- | ---: | ---: | ---: | ---: |
| Baseline (selected) | 0.60 | 85.7531% | 79.0892% | 92.9477% |
| CNN | 0.84 | 84.0610% | 75.3708% | 92.3780% |

Calibration-holdout ECE is 0.081684 for baseline and 0.058631 for CNN.
Model hashes, exact threshold statistics and report values are authoritative in
the generated JSON records; the table rounds them for readability.

## Verification actually performed

- All 18 stages completed using `dvc repro --force --no-run-cache`.
- The next `dvc repro` skipped all 18 stages; DVC status was `{}`.
- Every locked dependency and output was checked against both MD5 and byte size.
- Both metadata source snapshots were decoded and their hashes checked against
  the executed source and the source in the main workspace. Model hashes matched
  their metadata. Metadata identifies the committed source, including dirty-state
  disclosure for regenerated tracked outputs.
- The complete new output set and model cache were copied into the main workspace;
  its DVC status was also `{}`. The former four-stage pending state is resolved.
- A separate fresh Git checkout of artifact commit `c08f5f1` restored model binaries
  with `dvc checkout` from the verified local cache. Raw input and ignored
  prediction CSVs came from the lock-verified run. With a new DVC state database,
  `dvc status --json` was `{}` and Git was clean. This was a local-cache check,
  not a remote pull.
- With the new actual models, the complete suite passed **117 tests, 46 existing
  dependency warnings in 12.16 seconds**. The pre-training run also passed 117.
- Ruff, strict mypy (51 source files) and `git diff --check` passed.
- Real API startup for baseline, CNN and auto returned matching health/model-info
  model hashes, available report panels, successful authenticated predictions,
  missing-key rejection and the browser UI. Auto loaded the frozen baseline.

Local logs: `.checks/protocol-v2-train.log`, `.checks/protocol-v2-second.log`,
`.checks/protocol-v2-verification.json`, `.checks/protocol-v2-tests.log` and
`.checks/protocol-v2-api.json`. The run workspace is `.checks/protocol-v2-run`;
the fresh verification checkout is `.checks/protocol-v2-clean-checkout`.

## Interpretation and publication

The smaller independent risk set selected a stricter baseline threshold than the
old 0.57. Coverage decreased while accepted test accuracy increased. Those test
measurements describe this run; they were not used to choose the backend or
revise the protocol. Prior analyst exposure to this dataset remains disclosed.
New confirmatory production claims need genuinely new independent data.

The old pair and reports remain backed up in `.checks/protocol-v1-preserved` and
their public summary is archived. Current local models have complete source
snapshots produced by actual training, rather than retrofitted onto old models.

No remote model upload, push, pull request, merge, deployment, new hosted CI run
or Docker build was performed. Publishing the new lock for remote artifact CI
requires separately uploading its model objects first. See
[release status](RELEASE_STATUS.md) for this explicit local/remote distinction.
