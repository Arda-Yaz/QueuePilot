# Checkpoint and threshold selection: decision required

No split, model artifact or performance report was changed for this design
discussion. The preserved dataset contains 47,837 cleaned tickets: 33,485 train,
4,779 tune, 4,786 calibration and 4,787 test.

## Verified issue and scope

`train_cnn.evaluate_on_tune` selects the checkpoint and controls early stopping
using tune Macro-F1. `evaluate_tune_cnn` predicts that same persisted partition;
`analyze_threshold_cnn` selects a threshold from it. Model promotion then compares
both backends' tune coverage. The threshold grid's Bonferroni correction covers
the grid for a fixed predictor. It does not, by itself, cover adaptive checkpoint
and backend selection on the same observations. An independent test partition
exists; this finding is not evidence that training used test labels.

Current 90% accuracy targets should be described as empirical threshold-selection
criteria with held-out measurements, rather than unconditional production
guarantees. The existing calibration holdout measures score quality; it does not
fix reuse of tune data for the selection process.

## Options and costs

| Option | Data cost | Training and evaluation cost | What it supports |
| --- | --- | --- | --- |
| Keep the current design and narrow the claim | No new labels or repartition | No retraining; documentation only | Exploratory comparison with the existing held-out test and an explicit adaptive-selection limitation |
| Divide the 4,779 tune tickets into checkpoint and risk subsets | Approximately 2,390 checkpoint and 2,389 risk tickets; no extra labels; fewer observations for each purpose | At least one full CNN training run using only checkpoint data for early stopping, prediction and threshold runs for both backends, and a complete report/lock regeneration; baseline can retain its fitted weights if train is unchanged, but its threshold must be recomputed | An independent risk subset for a predictor frozen before inspecting risk data; stricter uncertainty and potentially lower feasible coverage |
| Collect a new, untouched risk-selection sample | Additional representative, deduplicated, labeled tickets; annotation and class-review effort depends on error rate and class balance | Existing weights may be frozen, avoiding training; run inference and risk/threshold selection on new labels, version the new data, regenerate the relevant reports/lock | Independent threshold selection conditional on a frozen model and prespecified grid; a separate later sample is still needed for a new unbiased final assessment |
| Nested selection or cross-fitting | No extra labels required in principle; more complex data partitioning and bookkeeping | Typically K full CNN fits for K folds, plus a final fit if deployment uses one model; inference and threshold work for every fold | Uses data more efficiently for selection estimates; an out-of-fold threshold is not automatically a guarantee for a different final refitted model |

For the tune subdivision, choose the backend using checkpoint/model-selection
data, then freeze it before risk selection. Alternatively prespecify a joint
correction over both frozen backends and all threshold candidates. Choosing the
backend again using risk coverage without accounting for that choice would
reintroduce selection effects. Hyperparameter search must also stay outside the
independent risk partition.

The existing calibration and test partitions have already been inspected. They
should not be relabeled as pristine new risk/test data after seeing results.
Repartitioning existing tune data improves the mechanical separation for a new,
prespecified run, but cannot undo historical analyst exposure. A stronger new
confirmatory claim favors genuinely new data and a frozen protocol.

With roughly half the current tune data, the accepted-sample counts also shrink.
Confidence bounds widen, rare-class measurements become less stable and some
thresholds may no longer meet the target. The minimum accepted sample count
alone does not guarantee statistical power. Plan the new sample size before
collecting data using the actual candidate count, target, alpha, expected error
rate, accepted coverage and required class support; then simulate power under
those assumptions. The current split's measured results cannot establish the
future feasible coverage.

The historical CPU CNN run stopped at epoch 12. That is context for budgeting,
not a timing promise: changed checkpoint data can change the stopping epoch.
A tune subdivision costs about one full training experiment; K-fold selection
costs about K such fits, subject to early stopping and hardware. No reliable
wall-clock or labeling price can be inferred from the repository alone.

For a portfolio demonstration, keeping the existing artifacts and narrowing the
claim has no data or training cost. Before making a formal selective-risk claim,
prefer a frozen backend plus independent risk data and prespecified multiplicity
control. Choosing a design and its data budget precedes any replacement artifacts.
