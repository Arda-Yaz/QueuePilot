# External data search and synthetic stress test - 12 November 2026

Scope note: this document covers additional development and organization adaptation research. It does not change the completed benchmark result on the existing dataset or introduce a new requirement for completing the reference application. See [project scope and roadmap](PROJECT_SCOPE.md).

At the user's request, real data was sought online and a separate synthetic
stress set was created and evaluated. Results were not used for new training
or model promotion. Failing scenarios were not changed after inspecting results.

## Real data found and downloaded

Source: Leonardo Santiago Benitez Pereira, **Classification of IT Support
Tickets**, [Zenodo v1](https://zenodo.org/records/7384758),
DOI `10.5281/zenodo.7384758`. The publisher states that 2,229 tickets from a real
IT company were classified by three IT professionals in 2020, with anonymization
and manual verification. The corpus is multilingual, including English, German,
Portuguese and Spanish. The [publisher metadata API](https://zenodo.org/api/records/7384758)
identifies the license as `cc-by-4.0`. Attribution: Pereira, Leonardo Santiago
Benitez, *Classification of IT Support Tickets*, Zenodo, 2022, CC BY 4.0.

The `X_train`, `X_test`, `y_train` and `y_test` CSV files were downloaded. MD5s
for all four were verified against both publisher metadata and pinned checksums.
Model, tokenizer and encoder pickle files were not downloaded or loaded.
Metadata for the [newer v2 record](https://zenodo.org/records/7648117) was also
checked: its four CSV checksums match v1. These are not two distinct new datasets.

Text and label files were joined one-to-one by ID. Labels were read from the
actual CSV files rather than differing category lists in secondary repository
descriptions. The corpus uses the following service groups instead of
QueuePilot's eight classes:

| Publisher class | Rows |
| --- | ---: |
| Support general | 762 |
| Fileservice | 684 |
| Software | 222 |
| O365 | 219 |
| Active Directory | 133 |
| Computer-Services | 106 |
| EOL | 103 |

Our checks found:

- 2,229 rows, 1,471 unique normalized texts and 758 duplicate rows.
- One normalized-text group with multiple source labels.
- 33 normalized texts shared by the source train/test files.
- Zero normalized exact-text overlaps with QueuePilot's old raw corpus.
- Zero source classes directly matching the label schema.

Zero overlap does not establish that all near duplicates were found or that
an independent sample from the same target distribution was obtained. The
source's train/test names also do not refer to our existing data partitions.

**Decision:** a real external source was obtained, but it is not directly
compatible with the existing eight-class audit. Mappings such as
`Fileservice -> Storage` or `O365 -> Access` were not invented; a service group
can cover multiple problem types. Eight-class accuracy was not calculated on
this corpus. Using it would require justified taxonomy alignment or independent
relabeling, splitting by duplicate groups, and defining language/distribution
coverage.

Raw CSV files remain only under `reports/private/external/zenodo-7384758`.
Shareable evidence:
[public_source_qualification.json](../reports/validation/2026-11-12/public_source_qualification.json).

## Other sources checked

- [Mendeley IT Incidents](https://data.mendeley.com/datasets/7pfzrjpct7/1)
  links to the Endava/Microsoft support classification repository. The
  [original repository](https://github.com/gabrielpreda/Support-Tickets-Classification)
  describes numerically encoded operational classes and processed texts.
  Direct compatibility with the eight classes could not be verified. The linked
  Azure CSV URL returned a DNS error; because the content was not downloaded,
  no claim was made that it contains the same texts.
- The [Tobi-Bueck corpus card](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets)
  lists a different queue schema and CC BY-NC 4.0 license, and also describes
  synthetic data generation. Independent human-labeled provenance was not
  verified for this data, so it was not selected as a real independent audit
  source. This observation is not a definitive claim that the whole corpus
  is synthetic.

The search is not proof that no suitable source exists anywhere. Checked sources
and decisions are recorded in
[source_search_registry.json](../reports/validation/2026-11-12/source_search_registry.json).

## Generated synthetic stress set

Separately from the real corpus, 80 original fictional scenarios were written:
10 per class. Each scenario has three variants: plain text, an email wrapper
and a single typo. There are 240 rows in **80 correlated scenario groups**,
not 240 independent real observations. Texts were AI-authored and were not
presented as real user tickets. Scenario texts are offered under CC0-1.0.

Scenario labels use explicitly stated conventional meanings: Access for sign-in,
Administrative rights for elevated privileges, Hardware for physical faults,
Storage for capacity/recovery, Purchase for procurement, HR for personnel/leave/pay,
Internal Project for planned projects, and Miscellaneous for general service-desk
questions. Equivalence to the original training taxonomy has not been established.
The measurement is therefore called **synthetic specification agreement**.

The plan and CSV were recorded with hashes before model inference. A normalized
exact-text overlap check against the old raw corpus found no overlap. The same
numeric threshold of 0.60 was applied to both fixed models; no threshold search
or training was performed. The candidate's 0.60 threshold was not recorded as
a new production threshold. The same number may not correspond to the same
calibration/coverage point in both models.

| Stress measurement | Reference | Word + character candidate |
| --- | ---: | ---: |
| Specification agreement on 80 plain scenarios | 45/80 - 56.25% | 45/80 - 56.25% |
| Agreement on email variants | 41.25% | 46.25% |
| Agreement on typo variants | 57.50% | 56.25% |
| Agreement across all correlated variants | 51.67% | 52.92% |
| Variants accepted at 0.60 | 142/240 | 153/240 |
| Specification agreement on accepted variants | 61.27% | 59.48% |
| Disagreements with confidence >=0.80 | 18 | 25 |

Neither model found the expected class in any of the 10 plain Administrative
rights scenarios written to mean elevated privileges. This highlights the need
to clarify label meanings; it does not establish zero performance on the
original real data. The drop in agreement after adding an email wrapper is
also a concrete stress finding about robustness to input format.

Unfavorable results were retained and easy examples were not added to inflate
the score. The candidate's checkpoint coverage gain did not reproduce as general
superiority under this new scenario specification. No new Clopper-Pearson
guarantees or real production accuracy claims were derived from synthetic results.

Data, plan, predictions and aggregate results:
[`synthetic-stress-v1`](../reports/validation/2026-11-12/synthetic-stress-v1/).
Commands: [`benchmarks/README.md`](../benchmarks/README.md).

## Completed work and remaining limit

Real-data search, download and source verification, as well as synthetic data
generation and stress evaluation, are complete. Independent risk/audit validation
with suitable new real labels for QueuePilot's eight classes is **not complete**.
Synthetic data was not represented as real to bridge that gap. No model was
promoted. The existing production package and earlier measurements are retained;
the stress findings do not support a claim that it transfers directly to new
data and taxonomies.

## Checks performed in the original run

- Six new tests passed, covering source checksum corruption, text/label ID order,
  taxonomy incompatibility, source train/test text duplication, synthetic group
  structure and data changes after plan creation.
- Full suite: **150 passed**, 94 dependency warnings, 12.72 seconds.
- Ruff and strict mypy passed (63 source files); `git diff --check` passed.
- Production DVC status was `{}`. MD5s and byte sizes for the 42 locked output
  records and the lock's bytes in Git were unchanged. Production sources, models
  and thresholds remained the same.
- The frozen model package, synthetic CSV and scenario sources passed hash
  checks. No new hosted CI run, commit/push or model promotion occurred in that run.

Numeric verification record:
[`verification.json`](../reports/validation/2026-11-12/verification.json).
