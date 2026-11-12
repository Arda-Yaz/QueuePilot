"""Prepare a deterministic model-blind pilot, record proposals, and gate exports."""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from benchmarks.public_data import load_pinned_corpus
from experiments.independent_data import original_text_hashes, text_hash
from src.hashing import calculate_file_sha256
from src.paths import DATA_PATH, ROOT_DIR

TAXONOMY = ROOT_DIR / "annotation/taxonomy_v1.json"


def prepare(source: Path, output: Path, n: int = 64) -> dict[str, Any]:
    frame = load_pinned_corpus(source)
    frame["text_sha256"] = frame["text"].map(text_hash)
    conflicts = set(frame.groupby("text_sha256")["category_truth"].nunique().loc[lambda s: s > 1].index)
    known = original_text_hashes(DATA_PATH)
    clean = frame[~frame["text_sha256"].isin(conflicts | known)].copy()
    unique = clean.sort_values("id").drop_duplicates("text_sha256")
    if n < 1 or n >= len(unique):
        raise ValueError("Pilot size must leave a separate unreviewed pool")
    # Hash ordering, not the model, source category or favorable-case selection.
    unique["order"] = unique["text_sha256"].map(lambda s: text_hash("pilot-v1-seed42-" + s))
    unique = unique.sort_values("order")
    pilot = unique.head(n).copy()
    pilot["annotation_id"] = [f"P{i:03d}" for i in range(1, n + 1)]
    output.mkdir(parents=True, exist_ok=False)
    blind = pilot[["annotation_id", "text", "text_sha256"]].rename(columns={"text": "Document"})
    for column in ("proposed_label", "status", "confidence", "rationale", "annotator_id", "human_reviewer_id", "human_decision"):
        blind[column] = ""
    blind.to_csv(output / "review_blind.csv", index=False)
    pilot[["annotation_id", "id", "source_split", "category_truth", "text_sha256"]].to_csv(output / "hidden_source_lineage.csv", index=False)
    clean[clean["text_sha256"].isin(pilot["text_sha256"])][["id", "text_sha256", "source_split"]].to_csv(output / "pilot_group_members.csv", index=False)
    unique.iloc[n:][["id", "text_sha256"]].to_csv(output / "reserved_unreviewed_pool.csv", index=False)
    frame[frame["text_sha256"].isin(conflicts)][["id", "text_sha256", "category_truth"]].to_csv(output / "quarantined_conflicts.csv", index=False)
    manifest = {"pilot_rows": n, "eligible_unique_groups": len(unique), "reserved_unreviewed_groups": len(unique) - n,
                "conflicting_text_groups_quarantined": len(conflicts), "original_overlap_rows_excluded": int(frame["text_sha256"].isin(known).sum()),
                "taxonomy_sha256": calculate_file_sha256(TAXONOMY), "taxonomy_approved": False,
                "blind_sheet_sha256": calculate_file_sha256(output / "review_blind.csv"),
                "sampling": "normalized text group, seed42 hash order, no model or service-label selection",
                "source": "https://zenodo.org/records/7384758", "license": "CC-BY-4.0",
                "status": "development_pilot_not_independent_audit", "automatic_gold_export": False}
    (output / "pilot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def record_proposals(output: Path, proposals: list[dict[str, str]]) -> dict[str, Any]:
    manifest = json.loads((output / "pilot_manifest.json").read_text(encoding="utf-8"))
    if calculate_file_sha256(TAXONOMY) != manifest["taxonomy_sha256"]:
        raise ValueError("Taxonomy changed after pilot selection")
    if calculate_file_sha256(output / "review_blind.csv") != manifest["blind_sheet_sha256"]:
        raise ValueError("Blind source sheet changed")
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    frame = pd.read_csv(output / "review_blind.csv", keep_default_na=False)
    items = pd.DataFrame(proposals)
    required = {"annotation_id", "status", "proposed_label", "confidence", "rationale"}
    if not required <= set(items.columns):
        raise ValueError("Incomplete proposal fields")
    if not items["annotation_id"].is_unique or set(items["annotation_id"]) != set(frame["annotation_id"]):
        raise ValueError("Proposals must cover each pilot ID exactly once")
    for item in proposals:
        status, label = item["status"], item["proposed_label"]
        if status == "LABELABLE":
            if label not in taxonomy["classes"]:
                raise ValueError("Unknown proposed label")
        elif status not in taxonomy["unresolved_statuses"] or label:
            raise ValueError("Unresolved cases cannot be forced into a label")
        if not item.get("rationale", "").strip() or item["confidence"] not in {"high", "medium", "low"}:
            raise ValueError("Each proposal needs a rationale and confidence")
    result = frame[["annotation_id", "Document", "text_sha256"]].merge(items, on="annotation_id", validate="one_to_one")
    result["annotator_id"] = "codex-ai-provisional"
    result["human_reviewer_id"] = ""
    result["human_decision"] = ""
    result["gold_approved"] = False
    path = output / "provisional_annotations.csv"
    if path.exists():
        raise FileExistsError("Provisional annotations already exist; preserve the review history")
    result.to_csv(path, index=False)
    return {"pilot_rows": len(result), "status_counts": result["status"].value_counts().to_dict(),
            "proposed_label_counts": result.loc[result["status"] == "LABELABLE", "proposed_label"].value_counts().to_dict(),
            "human_adjudicated_rows": 0, "gold_rows": 0, "eligible_for_independent_audit": False,
            "annotations_sha256": calculate_file_sha256(path), "taxonomy_sha256": manifest["taxonomy_sha256"]}


def require_audit_eligibility(pilot_manifest: dict[str, Any]) -> None:
    """This pilot has been inspected for development; approval cannot make it independent."""
    if pilot_manifest.get("status") != "independent_new_data":
        raise ValueError("Development pilot cannot be exported as independent audit data")
    if (pilot_manifest.get("taxonomy_approved") is not True
            or pilot_manifest.get("annotation_origin") != "human_adjudicated"
            or int(pilot_manifest.get("gold_rows", 0)) <= 0
            or pilot_manifest.get("gold_rows") != pilot_manifest.get("total_rows")):
        raise ValueError("Independent export requires an approved taxonomy and complete human adjudication")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT_DIR / "reports/private/external/zenodo-7384758")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "reports/private/taxonomy-pilot-v1")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
