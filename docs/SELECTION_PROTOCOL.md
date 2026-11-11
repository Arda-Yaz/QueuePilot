# Protocol v2: checkpoint selection before independent risk tuning

The protocol is fixed before examining the new run's results. No hyperparameters,
risk targets, threshold grids or partition seeds are changed in response to them.

1. Preserve the historical cleaned dataset and the train/calibration/test
   memberships. Reproduce the historical outer splits with seed 42 and `0.667`.
2. Stratify the historical tune partition into checkpoint and risk halves with
   seed 42 and `test_size=0.50`. Persist both ID lists. The legacy `tune_ids.csv`
   filename now denotes the risk half; `checkpoint_ids.csv` denotes checkpoint
   selection. Manifest `protocol_version: 2` distinguishes the semantics.
3. Fit baseline and CNN on train only. Baseline sigmoid calibration uses five-fold
   CV within train. CNN early stopping and checkpoint choice use checkpoint only.
4. Predict checkpoint with both fitted models. Freeze the backend with greatest
   checkpoint Macro-F1; choose baseline on an exact tie. Persist its model hash
   in `frozen_backend.json` before risk threshold analysis can run. The old
   two-percentage-point risk-coverage promotion rule is superseded for v2.
5. For the frozen backend, choose maximum risk coverage satisfying the existing
   simultaneous Clopper-Pearson lower bound and minimum accepted sample count.
   The threshold grid, target 0.90 and alpha 0.05 remain fixed. The pipeline also
   produces the other backend's threshold for descriptive comparison, but never
   uses that result to replace the frozen backend. Failure has no fallback.
6. Measure calibration quality on calibration and final classification/routing
   on test. These reports never feed back into backend selection. Publish the
   frozen choice only when its threshold references the same model hash.

The frozen backend stage has no risk/test dependency. DVC makes both threshold
stages depend on its output, and the publication stage uses only the frozen
backend's risk gate. Model metadata embeds recoverable source bytes and exact
source hashes. Training starts from committed source; Git can correctly become
dirty because preparation/training rewrites tracked generated outputs. This is
distinct from changing source during training, which causes training to fail.

Earlier results from this dataset have already been inspected. The new protocol
separates roles within this run; it does not erase historical analyst exposure
or establish distribution-independent production guarantees. The existing test
remains useful for descriptive comparison, not a pristine new confirmatory test.
Any stronger confirmatory claim requires genuinely new independent data and a
prespecified protocol. No remote publication is implied by a completed local run.

The original model pair and reports were backed up locally in
`.checks/protocol-v1-preserved`; its public metrics are archived in
[`history/protocol-v1-summary.json`](history/protocol-v1-summary.json).
