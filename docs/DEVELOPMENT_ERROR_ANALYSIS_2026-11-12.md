# QueuePilot development error analysis - 12 November 2026

Scope note: this document covers additional development and organization adaptation research. It does not change the completed benchmark result on the existing dataset or introduce a new requirement for completing the reference application. See [project scope and roadmap](PROJECT_SCOPE.md).

This work diagnoses errors on train and checkpoint data and runs one comparison
specified in advance, without changing the production model. No new performance
evaluation was run on the risk, calibration or test partitions. The numbers
compared here belong to **the same 2,389 checkpoint records** and should be kept
separate from the earlier test results.

## Reference and data boundary

- Starting Git revision: `b615135`; working branch: `codex/development-error-analysis`.
- Reference: protocol v2 baseline model, SHA-256
  `ea6b1f9ca0075bd32ee39d01a249b4b8860537f576e52ba8e8afc6dd1a169843`.
- Train: 33,485 records; checkpoint: 2,389. ID lists and raw-data hashes were
  verified. Train/checkpoint overlap and duplicate IDs are rejected.
- The raw data is read with the existing cleaner to resolve IDs. Analysis and
  fitting use only train/checkpoint rows. Risk/test IDs, predictions and
  performance reports are not inputs to candidate selection.
- Full texts, row-level predictions and the review sheet are kept only in the
  Git-ignored `reports/private/development-analysis` directory. Shareable reports
  contain aggregates and provenance hashes.

## Error analysis findings

Train accuracy is 0.9241 and Macro-F1 is 0.9363; checkpoint accuracy is 0.8564
and Macro-F1 is 0.8690. The train measurement uses data already seen by the
model, so it is not evidence of generalization. The gap alone also does not
establish overfitting as the cause of the errors.

There are 343 incorrect checkpoint predictions, including 20 with confidence
of at least 0.80. The true class appears among the top three predictions in
about 93.88% of errors. The correct alternative is therefore usually still
present, but a successful top-three suggestion does not mean automatic routing
is correct.

The most common confusion pairs are:

| True class | Prediction | Count |
| --- | --- | ---: |
| HR Support | Hardware | 46 |
| Hardware | Miscellaneous | 37 |
| Hardware | HR Support | 33 |
| Miscellaneous | Hardware | 30 |
| HR Support | Miscellaneous | 25 |
| Access | Hardware | 15 |
| Administrative rights | Hardware | 15 |

Focusing only on Administrative rights would therefore leave most errors
unaddressed. This class has 88 checkpoint examples; 15 of its 17 errors are
predicted as Hardware. Precision is 0.8452, recall is 0.8068 and F1 is 0.8256.

At the existing 0.60 threshold, the following slices have different meanings:

| Checkpoint slice | Accepted | Correct | Accuracy |
| --- | ---: | ---: | ---: |
| True label is Administrative rights | 71 | 61 | 85.92% |
| Routed as Administrative rights | 67 | 61 | 91.04% |
| Routed as Hardware | 562 | 500 | 88.97% |

The true class is unknown in production. The first row concerns missed members
of a class; the second and third concern tickets sent to the wrong destination
queue. An overall accuracy target does not provide a separate assurance for
each queue. The Hardware slice also matters because of its contribution to
all accepted errors.

### Example review and unverified explanations

Local example review found short descriptions of monitor, battery and audio
problems under the Administrative rights label. Correctly predicted examples
of the same class include Outlook/profile and Windows update descriptions.
This suggests possible ambiguity between the everyday meaning of the class
name and the dataset taxonomy. Without a labeling guide or domain expert
confirmation, these examples were not declared mislabeled and no labels were
changed.

As a check, the nearest train record was examined for each of the 88
Administrative rights checkpoint records in the first calibration fold's word
TF-IDF space. No nearest neighbor had both a different label and cosine
similarity >=0.85. This narrow check did not confirm conflicting labels on
near-identical texts; it does not establish taxonomy correctness or the
cleanliness of the entire dataset.

A vocabulary coverage check combined the word vocabularies from the train
folds. The mean unknown-token ratio was 0.35% for checkpoint errors and 0.40%
for correct predictions. A simple out-of-vocabulary explanation for errors
overall was not supported. Administrative rights errors had a higher short-token
ratio (23.35%, versus 16.88% for correct predictions), but an observation based
on only 17 errors is not a causal explanation.

## Comparison with one change

Hypothesis: adding character fragments to word unigram/bigram features may
provide complementary representations for short technical expressions and
word forms. This is a testable development hypothesis, not an established
diagnosis.

The only changed feature branch uses `char_wb`, 3-5 characters, `min_df=2`, at
most 50,000 features, sublinear TF and weight 1. Word-branch settings and logistic
regression parameters are unchanged. Calibration still uses five-fold sigmoid
calibration within train; vectorizers are fitted inside each fold's pipeline.
Checkpoint is excluded from fitting. No hyperparameter search or second
candidate was run.

The plan was recorded before fitting. The predefined development screen requires
no Macro-F1 loss, at least a 1 percentage point increase in checkpoint coverage
under the same target/confidence-bound formula, and no more than a 2 percentage
point loss in Administrative rights F1. This screen prioritizes candidates;
it is not a production acceptance criterion or a new guarantee.

### Checkpoint result

| Measurement | Reference | Word + character |
| --- | ---: | ---: |
| Overall accuracy | 85.64% | 85.89% |
| Macro-F1 | 0.8690 | 0.8712 |
| Administrative rights F1 | 0.8256 | 0.8421 |
| Development selection threshold | 0.59 | 0.56 |
| Development coverage | 80.79% | 83.55% |
| Accuracy on accepted tickets | 92.23% | 92.48% |
| Accepted / correct | 1,930 / 1,780 | 1,996 / 1,846 |
| Exploratory lower bound | 90.05% | 90.37% |
| Incorrect predictions with confidence >=0.80 | 20 | 21 |

Coverage was calculated with the same 0.90 target, alpha 0.05, 90 threshold
candidates and at least 50 accepted samples. Because both the threshold and
candidate were evaluated using checkpoint, the lower bounds in this table
are **not independent risk validation**. The candidate's 0.56 threshold was
not recorded as a production threshold; the reference production threshold
remains 0.60.

The increase is about 2.76 percentage points, or 66 additional acceptances.
In the paired comparison on the same records, the candidate corrected 61
errors and made 55 previously correct predictions incorrect: a net gain of
only 6 correct predictions. No large or statistically established improvement
in overall classification is claimed.

At a fixed 0.60 threshold, the result differs: coverage falls from 79.74% to
77.94%, while accepted accuracy rises from 92.49% to 93.93%. The same numeric
threshold does not represent the same operating point for two differently
calibrated models. Both fixed-threshold and fixed-selection-rule results are
therefore reported.

| Class | Checkpoint count | Reference F1 | Candidate F1 | Difference (percentage points) |
| --- | ---: | ---: | ---: | ---: |
| Access | 356 | 0.8949 | 0.8927 | -0.22 |
| Administrative rights | 88 | 0.8256 | 0.8421 | +1.65 |
| HR Support | 545 | 0.8569 | 0.8493 | -0.75 |
| Hardware | 680 | 0.8362 | 0.8424 | +0.62 |
| Internal Project | 106 | 0.9135 | 0.8986 | -1.49 |
| Miscellaneous | 352 | 0.8116 | 0.8275 | +1.59 |
| Purchase | 123 | 0.8963 | 0.8926 | -0.37 |
| Storage | 139 | 0.9170 | 0.9247 | +0.78 |

The candidate passed the predefined development screen. Nevertheless, not all
classes improved and high-confidence errors did not decrease. Model size grew
from about 53.10 MB to 68.22 MB. Candidate training and checkpoint evaluation
took about 115.5 seconds. The reference was not retrained, so these timings
are not a training-speed comparison.

![Checkpoint coverage-accuracy curves and class F1 differences](../reports/development/2026-11-12/development_comparison.png)

The plotted points mark thresholds selected by the same development rule.
They are neither independent risk validation nor new production thresholds.

## Decision and further validation

The character-feature candidate merits evaluation on new independent risk
data. The serving model, thresholds and automatic backend selection remain
unchanged. The Internal Project loss and high-confidence errors in particular
should be carried into further review.

Existing risk/test results have already been inspected. Searching for another
model on those partitions or presenting a favorable result there as new
independent validation would be inappropriate. After freezing the candidate
and protocol, new independent risk data can provide stronger further validation.
Until new data arrives, this work remains a development finding.

A labeling guide or domain expert review of examples could help resolve the
label/taxonomy concern. Evaluation labels should not be changed before that
review. Any future development cycle should separately record the data version
to which corrections were applied.

## Files and checks performed

Shareable numeric evidence:
[`reports/development/2026-11-12`](../reports/development/2026-11-12/).
It includes the plan, source hashes, train/checkpoint ID hashes, reference and
candidate model hashes, both threshold curves, class reports and resource costs.
Commands: [`experiments/README.md`](../experiments/README.md).

Local candidate weights are at `.checks/development-analysis/word_char.joblib`;
full-text review files and paired predictions are under
`reports/private/development-analysis`. The candidate was not recorded as a
production artifact or a DVC release output.

The following results describe the original development run:

- Eight tests passed for the new data boundary, slice interpretation, parameter
  equality and screening rules.
- Full suite: **125 passed**, 46 existing dependency warnings, 11.48 seconds.
- Ruff and strict mypy passed (55 source files).
- DVC status was `{}`. MD5s and byte sizes for the 42 production outputs in the
  lock, and the lock's bytes in Git, were unchanged. There was no diff in `src`,
  production artifacts or existing data/metric/figure directories.
- The new test file and `experiments` type checking were added to the relevant
  CI steps. No new hosted CI run was executed for this work.
- No new risk/test metric run or production model promotion was performed.

The next preparation step for independent data is complete:
[data intake, model freezing and two-stage validation](INDEPENDENT_VALIDATION.md).
New independent data is not yet available; this preparation is not a new
performance measurement.
