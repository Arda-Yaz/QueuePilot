# Public-source qualification and synthetic stress tests

These diagnostics do not retrain, tune thresholds or promote models. They use a
separate package so the already frozen independent-validation evaluator sources
remain unchanged.

## Reproduce the downloaded public-source checks

```powershell
.\.venv\Scripts\python.exe -m benchmarks.public_data --download
```

This downloads the Zenodo v1 metadata and four CSV files into ignored
`reports/private/external/zenodo-7384758`. It requires network access. Only CSV
and JSON are downloaded; the publisher's pickle/model files are not used. File
MD5s must match both the pinned checksums and publisher metadata. Labels are
joined by ID, not row position. The aggregate qualification report records
taxonomy compatibility, original-corpus overlap and duplicate/conflicting texts.
No foreign class is silently renamed to a QueuePilot class.

Source and attribution: Leonardo Santiago Benitez Pereira, *Classification of IT
Support Tickets*, Zenodo, DOI 10.5281/zenodo.7384758, CC BY 4.0. Original data:
https://zenodo.org/records/7384758. License metadata was verified using the
publisher API. Raw texts remain local; this repo publishes checksums and aggregates.

## Reproduce synthetic stress data and inference

```powershell
.\.venv\Scripts\python.exe -m benchmarks.synthetic_stress generate --output reports/validation/another-explicit-run
.\.venv\Scripts\python.exe -m benchmarks.synthetic_stress evaluate --output reports/validation/another-explicit-run
```

The completed v1 run is already stored in
`reports/validation/2026-11-12/synthetic-stress-v1`; do not overwrite it. Its 80
fictional scenarios have three correlated variants each (plain, email wrapper,
single typo). The scenario source and CSV are hashed before model inference.
Both frozen models use a fixed numeric cutoff of 0.60, with no search or fitting.
This numeric cutoff is not a calibration-equivalent operating point across models.

Labels express conventional meanings defined by the scenario author. They are
not proven equivalent to the original dataset's category definitions. Scores are
therefore *synthetic specification agreement*, not independently measured
real-world accuracy. There are 80 scenario groups, not 240 independent real
tickets. Reusing variants for confidence-bound claims is inappropriate.

The generated set uses `expected_label`, not the independent intake's
`Topic_group` schema, and does not include a real-data independence attestation.
Do not relabel it as real or use it to satisfy the independent audit gate.
AI-authored fictional scenario text is offered under CC0-1.0; it does not reproduce
third-party ticket text.

See [findings and limitations](../docs/EXTERNAL_DATA_AND_STRESS_2026-11-12.md).
