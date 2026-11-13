# Maintained release status

Protocol v2 has completed locally. The source commit is `80092e8`; all 18 DVC
stages were executed from raw data in `.checks/protocol-v2-run` with a fresh cache.
The unchanged second execution skipped all stages and returned empty DVC status.
See [run verification](PROTOCOL_V2_RUN.md) and [selection protocol](SELECTION_PROTOCOL.md).

The current release scope is the public-dataset reference implementation and
recommendation API/UI. Organization-specific queue mapping, operator feedback
capture and adaptation are a productization roadmap, not implemented features
or prerequisites for this benchmark completion. See [scope and roadmap](PROJECT_SCOPE.md).

## Current local model pair

| Backend | SHA-256 | Risk threshold |
| --- | --- | ---: |
| Baseline | `ea6b1f9ca0075bd32ee39d01a249b4b8860537f576e52ba8e8afc6dd1a169843` | 0.60 |
| CNN | `6b8c053e91b8ad1a47c08acb3a9ff889af871645987214be6279ef3812599045` | 0.84 |

Baseline was frozen using checkpoint Macro-F1 (0.868978 versus 0.854772), before
risk threshold selection. There is no risk-coverage backend fallback. Current
metadata contains exact recoverable source bytes; thresholds, model selection,
prediction provenance and reports reference the new model hashes.

## Remote availability and historical evidence

At the time of the local v2 training run, the agent had not uploaded this pair.
Remote availability has not been rechecked in this analysis/documentation change;
subsequent user actions are not inferred from that historical local observation.
A remote-only checkout or CI artifact job requires the lock's model objects and
credentials. This change adds no release model objects and performs no remote upload,
push, pull request, merge or deployment.

The previous model pair was successfully downloaded and hash-verified by
[CI run 43068533833](https://github.com/Arda-Yaz/QueuePilot/actions/runs/43068533833).
That hosted evidence applies to the historical pair, not these new hashes.
The old public metrics and metadata are archived in
[protocol-v1-summary.json](history/protocol-v1-summary.json); complete old outputs
remain in `.checks/protocol-v1-preserved` locally. Old model metadata's source
identity gap is historical; new metadata was produced by actual new training.

Earlier [audit verification](AUDIT_REMEDIATION_2026-11-11.md) and
[local reproduction notes](history/2026-11-11-reproduction.md) describe the stages
before this experiment. [Design options](EXPERIMENT_DESIGN.md) preserve the cost
comparison that led to the selected protocol.

## Additional external validation work — 12 November 2026

A real human-labeled Zenodo corpus was downloaded and checksum-verified, but its seven service labels do not match this model taxonomy. An explicitly synthetic 80-scenario / 240-variant stress suite was also run; plain-scenario agreement with the authored specification was only 56.25% for each frozen baseline/candidate. These are diagnostic findings, not new real-world accuracy estimates. No model promotion occurred. See [source assessment and stress results](EXTERNAL_DATA_AND_STRESS_2026-11-12.md).

## Taxonomy investigation and annotation pilot — 12 November 2026

Publisher metadata confirms names but does not provide inclusion/exclusion rules for the eight classes. Train-only vocabulary was profiled, and 64 deduplicated external texts were reviewed without model predictions or source service labels. Under an explicitly proposed operational taxonomy, 23 received provisional AI labels; the other 41 were left unresolved or out of scope. No new human-adjudicated eight-class gold data or model promotion was produced. See [the evidence and review package](TAXONOMY_AND_ANNOTATION_2026-11-12.md).
