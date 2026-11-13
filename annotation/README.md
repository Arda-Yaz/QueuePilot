# Blind taxonomy review pilot

The original publisher metadata confirms label names, not operational class
definitions. `taxonomy_v1.json` is an explicit proposal requiring domain review;
it is not a verified dictionary for old labels.

```powershell
.\.venv\Scripts\python.exe -m annotation.review_tools
.\.venv\Scripts\python.exe -m annotation.train_profiles
```

The completed pilot already exists in ignored `reports/private/taxonomy-pilot-v1`;
do not overwrite it. `prepare` groups duplicate texts, quarantines conflicting
source labels, excludes normalized matches to the old corpus, and selects a
seed42 hash-ordered pilot without model or source-service-label selection. The
source service labels are kept in a separate lineage file. Reserved groups are
kept separate from all pilot group members.

Proposals are entered with `record_proposals`, with one ID, status, rationale and
confidence per pilot record. It rejects missing/duplicate IDs, unknown labels,
forced labels on unresolved cases and changed source sheets. AI proposals keep
`gold_approved=false` and blank human review fields. The completed 64-case review
is provisional, not a set of new human gold labels. An inspected development
pilot is rejected for independent audit even if later human-reviewed.

`train_profiles` describes vocabulary associations using train only. It does not
query model predictions and is not an authoritative label guide. It was run
after the blind pilot proposals had been recorded.

Raw ticket text remains private. Aggregate findings and provenance:
[`docs/TAXONOMY_AND_ANNOTATION_2026-11-12.md`](../docs/TAXONOMY_AND_ANNOTATION_2026-11-12.md).

For English-language review, use the rationale translation in ignored
`reports/private/taxonomy-pilot-v1-en`. The original pilot remains historical
evidence; only the authored rationale text changed. The
[revision record](../reports/annotation/2026-11-12/english_revision.json) links
both versions and their integrity checks. Labels and source ticket languages
are unchanged, and the revision is not a new adjudication or independent audit.
