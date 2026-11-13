# Validation workflow for new independent data

Scope note: this document covers additional development and organization adaptation research. It does not change the completed benchmark result on the existing dataset or introduce a new requirement for completing the reference application. See [project scope and roadmap](PROJECT_SCOPE.md).

As of 12 November 2026, new compatible independent labeled data is not yet
available. This document and the tools prepare validation; they do not show
that the new model succeeds on independent data. Synthetic test results are
not used as real-data results.

## What is frozen

The reference and word+character candidate from the development comparison
are copied into a local package with hash verification and without retraining.
The package manifest binds the model files, class schema, development plan and
result, evaluator source snapshot, and Python/sklearn/numpy/pandas/scipy
versions. Execution stops if a file, protocol or evaluator source changes.
The current production model and threshold are unchanged; this workflow cannot
promote a model automatically.

Risk selection retains the 0.90 target, threshold range 0.10-0.99 and minimum
accepted count of 50. Because two fixed models are compared, total alpha 0.05
is divided between them: alpha 0.025 per model, with Bonferroni correction for
90 thresholds. The 180 model/threshold candidates are thus treated as one
family. This is a more conservative future validation protocol than the earlier
development screen for a single model.

## Two separate groups of new data

1. **New risk data:** selects thresholds for the two fixed models. If the lower
   bound for accepted accuracy does not meet the target, an old threshold or
   another model cannot be substituted to present a successful result. The
   workflow does not proceed to audit unless both models have an eligible
   threshold. This group is not for model search.
2. **New audit data:** contains different records that were not used to select
   thresholds. Thresholds from the risk stage are applied unchanged. Overall
   accuracy/Macro-F1, class results, coverage and accepted accuracy are reported.
   The one-sided Clopper-Pearson bound for accepted accuracy is calculated with
   alpha 0.025 for each of the two fixed policies. No threshold search occurs here.

The new groups must be separated before evaluation begins. Adding records
sequentially after seeing results to seek a favorable outcome, or stopping
sampling based on success, is outside this protocol.

In addition to passing both accuracy gates, the audit review screen checks for
an observed coverage increase of at least 1 percentage point, no Macro-F1 loss,
and at most a 2 percentage point loss in Administrative rights F1. The full
screen cannot pass if any class is unobserved. Coverage differences and class
F1s are point estimates; this screen does not establish a statistically proven
improvement. Every outcome requires human review and is not written to
production files.

## Data format and label provenance

CSV template: [`experiments/templates/new_tickets.csv`](../experiments/templates/new_tickets.csv).
Required columns are `external_id`, `Document`, `Topic_group`; optional
`labeler_id` and `label_notes` provide a review trail. Use UTF-8. Class names:

- Access
- Administrative rights
- HR Support
- Hardware
- Internal Project
- Miscellaneous
- Purchase
- Storage

Class names alone are not a labeling guide. For apparently ambiguous groups
such as Administrative rights, the domain owner must verify category definitions
and examples. New labels must not be copied from model predictions, and
ambiguous examples need expert review. This work did not invent an authoritative
label taxonomy or change evaluation labels.

Source attestation template:
[`data_attestation.json`](../experiments/templates/data_attestation.json).
Empty fields and `false` values in the template are intentional: the blank
template cannot pass evaluation. The data owner must describe the source,
sampling method, labeling process and collection period, and explicitly attest
that the data has not been used before and that labels were produced
independently of model predictions. An attestation is not proof of verification;
the tool cannot establish its historical accuracy automatically.

Initial intake rejects blank/missing fields, unknown labels, duplicate IDs,
repeated normalized text and text overlap with the old raw dataset. The text
hash excludes the label: relabeling an old record does not make it new. Audit
also rejects risk-record texts and IDs. Checks catch case/whitespace differences;
they cannot guarantee independence against paraphrases, ticket versions, email
threads or undisclosed prior use. Collection and human review must address
those issues.

Prefer random or consecutive records representing the target distribution.
Selecting only a problematic class does not produce a representative sample
for claims about coverage across all tickets. Missing classes and all class
counts remain visible in the result.

## Sample size

`min_accepted_samples=50` is not a statistical power plan or a promise that 50
new records can establish the target. Correction for two models/90 thresholds,
expected error rate, acceptance rate and class distribution affect the required
sample size. Once the data source and cost are known, risk/audit sizes should
be planned separately before looking at outcomes. Taking another partition
from the existing dataset or generating synthetic records does not satisfy
the need for genuinely new independent data.

## Running the workflow

From the repository root in the existing development environment:

```powershell
# Once only: freeze the existing two models and evaluator sources.
.\.venv\Scripts\python.exe -m experiments.independent_validation freeze --bundle .checks/frozen-word-char-v1

# When genuinely new risk data becomes available:
.\.venv\Scripts\python.exe -m experiments.independent_validation risk --bundle .checks/frozen-word-char-v1 --csv reports/private/new-risk.csv --attestation reports/private/new-risk-source.json --output .checks/new-risk-run

# When different, genuinely new audit data becomes available:
.\.venv\Scripts\python.exe -m experiments.independent_validation audit --bundle .checks/frozen-word-char-v1 --csv reports/private/new-audit.csv --attestation reports/private/new-audit-source.json --risk-result .checks/new-risk-run/risk_result.json --output .checks/new-audit-run
```

The tool does not overwrite existing package/output directories. Before a real
risk result is supplied to audit, its receipt hash and risk prediction files
are verified; modified thresholds or files are rejected. Hashes detect accidental
changes; they do not replace a signed or external trust authority. Use only
trusted local joblib packages that you created.

Outputs should remain under `.checks` or `reports/private`; ticket texts and
row-level results must not be added to Git. Until new independent data is
available, only freezing and synthetic automated tests are run.

## Work actually performed in the original preparation run

- The `.checks/frozen-word-char-v1` package was created; do not rerun the freeze
  command above for that directory. Existing model files and the source snapshot
  were verified again.
- Candidate hash: `d3c997c2d12d7ea793cf7db6f4dd6bd200a5da428a877fa4e657439f9aae4378`;
  reference hash: `ea6b1f9ca0075bd32ee39d01a249b4b8860537f576e52ba8e8afc6dd1a169843`.
- The shareable manifest and readiness state are under
  [`reports/development/2026-11-12`](../reports/development/2026-11-12/).
  `independent_validation_readiness.json` records **0** real evaluations.
  The manifest is not a success report on new data.
- Nineteen synthetic tests were added for data intake, model/source integrity,
  risk/audit separation and threshold immutability. Full suite: **144 passed**,
  94 dependency warnings, 12.64 seconds. Warnings come from existing joblib/NumPy
  and TestClient dependencies; more model-loading tests increase their count.
- Ruff and strict mypy passed (58 source files). New tests were added to CI;
  no hosted CI run was started.
- Risk and audit commands were not run with real data because no new compatible
  real data was available. Synthetic fixtures stayed in test temporary directories.

## Subsequent data search and stress testing

A real, human-labeled corpus was downloaded from the internet. Its seven service
labels do not match the existing eight classes, so it was not used directly as
audit input. Separately, 240 correlated variants from 80 fictional scenarios
were generated and run through both models. Details, including unfavorable
results, are in the [external data and stress test report](EXTERNAL_DATA_AND_STRESS_2026-11-12.md).
An independent audit using compatible real eight-class data remains incomplete.
