# Development-only experiments

These tools open only the persisted train/checkpoint ID files. The raw dataset
is read through the canonical cleaner to resolve those IDs, then only the two
development partitions are retained for diagnosis/fitting. No risk, calibration
or test ID, prediction or performance report is used for candidate selection.
They do not call the production `load_splits` consumer or overwrite release files.

From the repository root with the existing Python 3.12 development environment:

```powershell
$env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '4'
$env:MKL_NUM_THREADS = '4'
.\.venv\Scripts\python.exe -m experiments.development_analysis
.\.venv\Scripts\python.exe -m experiments.compare_word_char
```

The first command diagnoses the hash-verified reference model. Aggregate results
are written to `.checks/development-analysis`; full ticket text, IDs, prediction
rows and the review worksheet stay in ignored `reports/private/development-analysis`.
Train performance is in-sample and must not be presented as generalization.

The second command writes its immutable plan before fitting one candidate.
The word TF-IDF branch, classifier parameters, train IDs and five-fold sigmoid
calibration match the reference. Character TF-IDF is the single added feature
branch. Vectorizers stay inside each calibration-fold pipeline, avoiding fitting
features on checkpoint or on the calibration fold's validation observations.

There is no hyperparameter sweep or automatic production promotion. The
predeclared development screen requires nondecreasing Macro-F1, at least one
percentage point improvement in exploratory checkpoint CP-gated coverage, and
Administrative rights F1 loss no greater than two percentage points. That screen
is a development triage rule, not a new statistical guarantee. Checkpoint has
already been inspected and is used to pick thresholds and compare models here.

The candidate weights stay under `.checks`, not under serving artifacts. Plan,
source hashes, candidate model hash, curves and paired predictions make the
comparison reviewable. A pre-existing plan causes the runner to fail rather than
silently overwrite the experiment; use `--output` with a fresh directory only for
an explicitly justified rerun, not to search for favorable results.

`src/error_summary.py` has historical risk/test defaults. Do not use that entry
point for this development workflow. The production source tree remains unchanged
so the existing source snapshots and DVC release contract stay valid.

For the completed comparison and limits, see
[`docs/DEVELOPMENT_ERROR_ANALYSIS_2026-11-12.md`](../docs/DEVELOPMENT_ERROR_ANALYSIS_2026-11-12.md).

## Next step: genuinely new independent data

The candidate can be frozen without retraining with
`python -m experiments.independent_validation freeze --bundle .checks/frozen-word-char-v1`.
Data intake templates and the two-batch risk/audit procedure are documented in
[`docs/INDEPENDENT_VALIDATION.md`](../docs/INDEPENDENT_VALIDATION.md). New independent
data is not currently available; passing synthetic automation tests does not
validate the candidate on real new tickets.
