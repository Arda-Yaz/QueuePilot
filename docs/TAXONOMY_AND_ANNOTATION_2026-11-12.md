# Taxonomy research and blind annotation pilot - 12 November 2026

Scope note: this document covers additional development and organization adaptation research. It does not change the completed benchmark result on the existing dataset or introduce a new requirement for completing the reference application. See [project scope and roadmap](PROJECT_SCOPE.md).

## What the source did and did not verify

The [original Kaggle page](https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset)
and [publisher metadata API](https://www.kaggle.com/api/v1/datasets/view/adisongoh/it-service-ticket-classification-dataset)
were checked. The API response was preserved locally and hashed. Version 1,
two fields (`Document`, `Topic_group`), 47,837 rows and eight class names can
be verified. Metadata identifies the license as CC0: Public Domain.

The inspected publisher metadata does not describe class inclusion/exclusion
rules, annotator instructions or the labeling process. No authoritative guide
completing those meanings was found in the local notebook or source records
either. The **original class meanings are therefore not considered verified**.
This is not a universal claim that no guide exists elsewhere.

Numeric record:
[`taxonomy_source_evidence.json`](../reports/annotation/2026-11-12/taxonomy_source_evidence.json).

## Patterns in train data

Word patterns were extracted from train texts/labels only, without model
predictions. The analysis used class mean TF-IDF and distinctiveness relative
to the overall mean, retaining phrases seen in at least 10 class documents.
These are **empirical associations with existing labels**, not class definitions.

| Original label | Prominent train phrases | Unresolved boundary |
| --- | --- | --- |
| Access | confluence, card, license, password, user | Account access, licensing and application permissions may share a group |
| Administrative rights | upgrade, outlook, windows, windows upgrade, issues | Administrator privileges or endpoint software/OS support? |
| HR Support | starter, form, new starter, error, leave | How are personnel processes separated from account creation? |
| Hardware | monitor, laptop, meeting, room, cable | Physical faults versus room/connectivity services |
| Internal Project | code, project, codes, setup, pipeline | Project code/setup services versus planned project coordination |
| Miscellaneous | change, add, approval, owner, approve | Groups/lists/approval workflows versus general service questions |
| Purchase | po, purchase, purchase po, purchased, item | Procurement versus license activation/access |
| Storage | wants, mailbox, folder, accept decline, decline | Storage capacity versus folder/mailbox access permissions |

This evidence narrows the interpretation of the earlier synthetic stress test.
That test defined Administrative rights as conventional elevated privileges
and Storage as capacity/recovery. Training labels may reflect a different
operational taxonomy. Stress scores were retained, but they do not measure
real model accuracy against the old taxonomy or establish model error on their own.

Labels were not renamed by treating patterns as source authority. For example,
Administrative rights was not simply renamed Software, nor were all sharing
requests automatically assigned to Storage.

## Explicit proposed review guide

[`annotation/taxonomy_v1.json`](../annotation/taxonomy_v1.json) defines inclusion
and exclusion rules per class. Its status is
`proposal_requires_domain_adjudication`, with
`equivalent_to_original_training_taxonomy=false`. It is neither a verified
dictionary for the old dataset nor a new labeling scheme for the active model.

The main proposed distinctions are:

- Ordinary authentication and user resource permissions: Access.
- Explicit admin/root/sudo/elevated privilege requests: Administrative rights.
- Explicit physical device faults: Hardware; not every printing error is hardware.
- Capacity, backup/recovery and file persistence: Storage; access permission alone does not imply Storage.
- Commercial purchases/orders/quotes: Purchase; installation or activation alone is not procurement.
- Personnel/leave/pay business processes: HR Support; creating an intern's account is not HR solely because the text says intern.
- Explicit planned project coordination: Internal Project; the word project alone is insufficient.
- General service-desk process information: Miscellaneous; unknown requests are not automatically assigned here.

This strict proposal does not cover all general software, network, messaging
and security services. Instead of forcing them into the old eight classes,
they are recorded as `OUT_OF_SCOPE` or `TAXONOMY_REVIEW`. Missing context is
`INSUFFICIENT_CONTEXT`; separate requests without a dominant intent are
`MULTI_INTENT`.

## Blind pilot on 64 real records

Source: Pereira's [Zenodo corpus](https://zenodo.org/records/7384758), CC BY 4.0.
Source text/label CSV checksums were verified. Normalized texts were deduplicated
as groups, and one group with conflicting source labels was quarantined.
There is no normalized exact-text overlap with the old raw data.

This left 1,470 eligible distinct text groups. A fixed seed42 hash ordering
selected 64 groups, without model scores, source service categories or selection
of easy examples. Another 1,406 groups were placed in a separate
`reserved_unreviewed_pool.csv` list. This list is an unreviewed pool, not an
audit set; its suitability for future use requires separate verification.

The file viewed during annotation contained only text, local pilot ID and text
hash, with no source service label or model prediction. Source lineage was
kept separately. A rationale based on the full text and a provisional AI decision
were recorded for each of the 64 texts.

| Provisional pilot decision | Records |
| --- | ---: |
| Labelable under the proposed guide | 23 |
| Insufficient context | 20 |
| Outside the proposed eight-class scope | 13 |
| Taxonomy boundary decision needed | 7 |
| Multiple intents | 1 |

The provisional distribution of the 23 labelable records is Access 20,
Administrative rights 2 and Storage 1. This does not establish the real target
distribution of the external corpus or coverage of all eight classes. It
particularly exposes gaps in the proposed software/network/messaging scope
and missing information in short titles.

**Human-approved records: 0. Gold records: 0.** The AI confidence field is a
review note, not a calibrated probability. These proposals do not replace
independent expert annotation. The inspected pilot is development data; later
human approval does not turn it into new independent audit data. The tool
rejects that use.

## Files ready for human review

Full texts and original review files are in the Git-ignored directory
`reports/private/taxonomy-pilot-v1`:

- `review_blind.csv`: blank review sheet without source categories or predictions.
- `provisional_annotations.csv`: AI proposals, rationales and blank human-decision fields.
- `ai_proposals.json`: complete rationale records keyed by row ID.
- `hidden_source_lineage.csv`: source labels to open only during adjudication.
- `pilot_group_members.csv`: all source IDs associated with each text.
- `reserved_unreviewed_pool.csv`: unreviewed groups disjoint from the pilot.
- `quarantined_conflicts.csv`: source-label conflicts.

An English revision of the authored rationales is available in
`reports/private/taxonomy-pilot-v1-en`. Use this revision for English-language
review. The original pilot is retained as historical evidence. Translation
changes only the rationale wording; source ticket texts, IDs, labels, statuses,
confidence values and human review fields are preserved. The public
[English revision record](../reports/annotation/2026-11-12/english_revision.json)
links the original and translated hashes and records the integrity checks.
The original summary and verification records continue to describe the original
pilot; [the English revision summary](../reports/annotation/2026-11-12/english_annotation_summary.json)
describes the translated copy.

Residual identifiers may remain in texts despite the source's anonymization
statement, so full texts were not published. Shared reports contain only counts,
statuses, general word patterns and hashes. Attribution: Leonardo Santiago
Benitez Pereira, *Classification of IT Support Tickets*, Zenodo, 2022,
DOI 10.5281/zenodo.7384758, CC BY 4.0.

## Specific boundaries requiring a decision

1. Preserving the old labels exactly requires the old source's rules or an
   explanation from an authorized domain owner. Train vocabulary cannot establish
   a definitive dictionary.
2. Adopting a guide based on business meanings creates a new taxonomy version;
   old labeled train data does not become correctly labeled automatically.
   New annotation and retraining on suitable data are required.
3. If software/network/messaging/security support is in scope, explicit classes
   or justified boundaries must be defined; Miscellaneous must not be silently
   expanded.
4. Shared mailbox creation, email address/list maintenance and file-lock examples
   need guide boundary decisions. They must not be exported as gold data while
   those ambiguities remain unresolved.
5. For genuine independent risk/audit validation, freeze the taxonomy and sampling
   protocol first. Experts should then label suitable groups outside the pilot
   without viewing predictions, with checks for language, duplicates and
   representativeness.

No change assigning new meanings to production labels or promoting a model
was made. This step produced source research that exposes what could not be
verified, an explicit proposed guide and a completed provisional review of
real texts.

## Checks performed in the original pilot run

- Eight tests passed for blind sampling, ID integrity, rejection of forced
  labeling, detection of changed review sheets and preventing the pilot from
  becoming audit data.
- Full suite: **158 passed**, 94 dependency warnings, 18.02 seconds.
- Ruff, strict mypy (67 source files) and `git diff --check` passed.
- Pilot text/proposal/taxonomy hashes were verified. The 1,406 reserved text
  groups do not overlap any duplicate member of the pilot; the count of new
  human-approved gold records is zero.
- DVC status was `{}`. The 42 production output records, production sources,
  model/threshold files and lock were unchanged. The frozen candidate package
  also passed integrity checks.
- No new model training/promotion, hosted CI run or commit/push occurred in that run.

Numeric record: [`verification.json`](../reports/annotation/2026-11-12/verification.json).
