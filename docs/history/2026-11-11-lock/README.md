# Historical lock and LF migration

`original.dvc.lock` is the exact byte record at audited commit
`b0eee7c17cdfe89ab4c2009657a9fb8f3f27405f`. It contains the CRLF source hashes
from the historical training/evaluation workspace. `lf.dvc.lock` is DVC's
newline-only migration of that record. Both use byte-preserving Git attributes.

`migration.json` records the two lock SHA-256 values, the four source conversions,
the 34 unchanged output SHA-256 values, DVC version, command and two clean-checkout
status results. `migration-script.py.txt` preserves the one-off script used for
the check (including the retry handling for an existing isolated checkout).
It is an execution record, not a tool for blessing future source changes.

The isolated checkouts used Git's audited LF sources. Ignored raw data,
predictions and model files were supplied from locally available inputs and
matched against the original lock before migration. The second checkout used
`dvc checkout` from the verified local cache. No training or remote pull occurred.
Only 11 dependency MD5/size pairs changed. Every other lock value, including all
outputs, remained identical. Equal ASTs supplement the exact CRLF/LF byte check;
they are not a claim that the entire training experiment was replayed.

Subsequent functional changes in the current workspace have not been recorded
as if this old run had used them. In particular, the main lock does not claim
that source-snapshot metadata or prediction provenance has been produced for the
preserved models. See [release status](../../RELEASE_STATUS.md).
