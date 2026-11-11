# Maintained release status

Protocol v2 has completed locally. The source commit is `80092e8`; all 18 DVC
stages were executed from raw data in `.checks/protocol-v2-run` with a fresh cache.
The unchanged second execution skipped all stages and returned empty DVC status.
See [run verification](PROTOCOL_V2_RUN.md) and [selection protocol](SELECTION_PROTOCOL.md).

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

This new pair has not been uploaded to remote model storage. A remote-only
artifact checkout, CI artifact job or deployment using this new lock requires a
separately authorized upload of its model objects. Local checks do not establish
remote availability. No push, pull request, merge, deployment or upload was done.

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
