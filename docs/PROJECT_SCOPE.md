# Project scope and organization adaptation

QueuePilot is a reproducible reference system for confidence-based IT ticket
routing, developed and evaluated on a public eight-label dataset. Its benchmark
implementation is complete: versioned data preparation, model training,
checkpoint-based selection, independent risk threshold tuning, evaluation,
artifact integrity checks, API and browser UI.

## Current measured behavior

On the recorded 4,787-ticket test partition, the selected baseline achieved
85.75% overall accuracy. At threshold 0.60 it accepted 79.09% of tickets for
automatic-routing recommendations, with 92.95% accuracy on that accepted subset.
These are measurements on the recorded dataset and split, not guaranteed rates
for a new organization. The risk-selection target is 90%; it is distinct from
the observed 92.95% accepted test accuracy.

The classifier emits the dataset's label names. Giving those names new display
descriptions or mapping them to a company's queues does not by itself retrain
the classifier or establish semantic equivalence. The publisher supplies names
without operational annotation rules; organization-specific meanings therefore
need validation using real examples and the organization's category owner.

## Organization pilot and adaptation roadmap

The intended adoption path is a controlled, human-reviewed pilot:

1. Define the organization's queues and review representative examples. Specify
   how the dataset labels relate to those queues; do not infer the mapping from
   label spelling alone. Keep internal label identities and version the mapping.
2. Run recommendations alongside the existing workflow. Operators confirm or
   correct suggestions before consequential routing decisions in the pilot.
3. Collect versioned corrections with clear label definitions and data provenance.
   Preserve separate development and independent evaluation batches.
4. If categories match but language/input format differs, test input adaptation
   on development data. If category meanings or boundaries change, prepare newly
   labeled examples and retrain rather than only renaming outputs.
5. Re-select thresholds for the frozen model and verify the target on independent
   organization data before expanding automatic routing. Monitor workload,
   per-queue errors and review volume as well as overall accuracy.

These are adoption steps and planned integrations. The current application does
not implement an operator correction database, online learning or an automatic
organization-queue mapping/approval workflow.

| Capability | Current status |
| --- | --- |
| API/UI predictions, confidence, top-three labels and review flag | Implemented |
| Hash-bound models, thresholds, reports and source provenance | Implemented |
| Reproducible offline training and evaluation pipeline | Implemented |
| Development error analysis and bounded candidate comparison | Implemented research tools |
| Independent-data intake and risk/audit evaluator | Implemented tools; new compatible real-data audit not completed |
| Organization-specific queue descriptions/mapping configuration | Roadmap; requires validated definitions |
| Operator correction storage and feedback UI/integration | Roadmap |
| Automatic retraining or promotion from user feedback | Not implemented; offline retraining/review is required |

## How to interpret additional research

The word+character candidate improved an exploratory checkpoint trade-off but
has not replaced the selected release baseline. External corpus qualification,
synthetic stress scenarios and a provisional annotation pilot are recorded
research findings, not replacement measurements for the release test set.
The synthetic category meanings were authored assumptions; they do not establish
that release test accuracy fell from 92.95% to 56.25%.

The acquired real corpus has a different service taxonomy. Proposed operational
definitions and AI pilot labels remain unapproved. That limits broader deployment
claims; it does not erase the completed dataset benchmark or make those research
questions prerequisites for demonstrating the reference application.

Current scope is the dataset benchmark and the working recommendation system.
Organization adaptation is the next productization phase. See
[release status](RELEASE_STATUS.md) for artifact availability and
[research findings](DEVELOPMENT_ERROR_ANALYSIS_2026-11-12.md) for the recorded experiments.

The combined research/tooling changes were checked before packaging on
12 November 2026: 158 tests passed, Ruff and strict mypy (67 source files)
passed, and `git diff --check` passed. The release source, models, thresholds
and lock were not changed by this scope/documentation update.
