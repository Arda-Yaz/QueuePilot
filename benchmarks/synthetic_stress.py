"""Generate before inference; compare fixed models on a fictional policy stress set."""

import argparse
import json
import re
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import classification_report

from benchmarks.stress_scenarios import SCENARIOS
from experiments.independent_data import original_text_hashes, text_hash
from experiments.independent_validation import verify_bundle
from src.hashing import calculate_file_sha256
from src.paths import DATA_PATH, ROOT_DIR


def typo_variant(text: str) -> str:
    words = list(re.finditer(r"[A-Za-z]{6,}", text))
    match = max(words, key=lambda item: len(item.group()))
    word = match.group()
    i = len(word) // 2
    changed = word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if changed == word:
        changed = word[:i] + word[i + 1:]
    return text[:match.start()] + changed + text[match.end():]


def make_cases() -> pd.DataFrame:
    rows = []
    for label, examples in SCENARIOS.items():
        for number, text in enumerate(examples, 1):
            group = f"{label}-{number:02d}"
            for variant, document in {
                "plain": text,
                "email": f"Hello service desk,\n\n{text}\n\nPlease help with this request. Thank you.",
                "typo": typo_variant(text),
            }.items():
                rows.append({"case_id": f"{group}-{variant}", "scenario_id": group,
                             "variant": variant, "Document": document, "expected_label": label,
                             "origin": "AI-authored synthetic; not a real customer ticket"})
    result = pd.DataFrame(rows)
    if not result["Document"].map(text_hash).is_unique:
        raise ValueError("Generated stress set contains duplicate normalized text")
    return result


def generate(output: Path, bundle: Path) -> None:
    manifest = verify_bundle(bundle)
    frame = make_cases()
    if set(frame["expected_label"]) != set(manifest["labels"]):
        raise ValueError("Stress label schema mismatch")
    if set(frame["Document"].map(text_hash)) & original_text_hashes(DATA_PATH):
        raise ValueError("Synthetic case overlaps original corpus; inspect before evaluation")
    output.mkdir(parents=True, exist_ok=False)
    frame.to_csv(output / "synthetic_cases.csv", index=False)
    plan = {
        "origin": "AI-authored, fictional policy specifications; no real labels or tickets",
        "license": "CC0-1.0", "independent_real_world_evidence": False,
        "category_meanings": "Conventional authored meanings for these scenarios, NOT verified equivalence to the original training taxonomy",
        "scenario_count": frame["scenario_id"].nunique(), "rows": len(frame),
        "variants": ["plain", "email", "typo"], "variants_are_correlated": True,
        "thresholds": {"reference": 0.60, "candidate": 0.60},
        "threshold_interpretation": "Fixed shared numeric stress-test setting; not a new candidate production threshold or calibration-equivalent operating point",
        "no_threshold_search": True, "no_retraining": True, "no_automatic_promotion": True,
        "cases_sha256": calculate_file_sha256(output / "synthetic_cases.csv"),
        "frozen_bundle_sha256": calculate_file_sha256(bundle / "manifest.json"),
        "source_sha256": {name: calculate_file_sha256(ROOT_DIR / name) for name in
                          ("benchmarks/stress_scenarios.py", "benchmarks/synthetic_stress.py")},
        "label_specification": {
            "Access": "Ordinary account sign-in/authentication", "Administrative rights": "Privileged/elevated permission requests",
            "Hardware": "Physical equipment faults", "Storage": "Capacity, file backup/recovery",
            "Purchase": "Procurement, orders, licenses", "HR Support": "Payroll, leave, personnel questions",
            "Internal Project": "Planned internal IT project coordination", "Miscellaneous": "General service-desk process questions",
        },
    }
    (output / "stress_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8", newline="\n")


def evaluate(output: Path, bundle: Path) -> dict[str, Any]:
    manifest = verify_bundle(bundle)
    plan = json.loads((output / "stress_plan.json").read_text(encoding="utf-8"))
    if (calculate_file_sha256(output / "synthetic_cases.csv") != plan["cases_sha256"]
            or calculate_file_sha256(bundle / "manifest.json") != plan["frozen_bundle_sha256"]):
        raise ValueError("Stress inputs or model package changed after plan")
    for name, sha in plan["source_sha256"].items():
        if calculate_file_sha256(ROOT_DIR / name) != sha:
            raise ValueError("Stress source changed after generation")
    if (output / "stress_results.json").exists():
        raise FileExistsError("Stress results already exist; do not silently rerun/edit the benchmark")
    frame = pd.read_csv(output / "synthetic_cases.csv", keep_default_na=False)
    result: dict[str, Any] = {"interpretation": "Synthetic specification agreement only; no independence or production-accuracy claim",
              "independent_real_world_evidence": False, "plan_sha256": calculate_file_sha256(output / "stress_plan.json"),
              "models": {}}
    for name, filename in manifest["models"].items():
        model = joblib.load(bundle / filename)
        probabilities = model.predict_proba(frame["Document"])
        predictions = model.classes_[probabilities.argmax(axis=1)]
        rows = frame.copy()
        rows["predicted_label"] = predictions
        rows["confidence"] = probabilities.max(axis=1)
        rows["matches_specification"] = rows["expected_label"] == rows["predicted_label"]
        rows["accepted"] = rows["confidence"] >= plan["thresholds"][name]
        rows.to_csv(output / f"{name}_synthetic_predictions.csv", index=False)
        base = rows[rows["variant"] == "plain"]
        result["models"][name] = {
            "model_sha256": manifest["files"][filename], "plain_scenario_count": len(base),
            "plain_specification_agreement": float(base["matches_specification"].mean()),
            "all_variants_agreement": float(rows["matches_specification"].mean()),
            "accepted_count": int(rows["accepted"].sum()),
            "accepted_specification_agreement": float(rows.loc[rows["accepted"], "matches_specification"].mean()) if rows["accepted"].any() else None,
            "high_confidence_specification_mismatches": int(((rows["confidence"] >= 0.8) & ~rows["matches_specification"]).sum()),
            "agreement_by_variant": rows.groupby("variant")["matches_specification"].mean().to_dict(),
            "plain_classification": classification_report(base["expected_label"], base["predicted_label"],
                                                           labels=manifest["labels"], output_dict=True, zero_division=0),
        }
    (output / "stress_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["generate", "evaluate"])
    parser.add_argument("--bundle", type=Path, default=ROOT_DIR / ".checks/frozen-word-char-v1")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "reports/validation/2026-11-12/synthetic-stress-v1")
    args = parser.parse_args()
    if args.mode == "generate":
        generate(args.output, args.bundle)
        print("Created 80 fictional scenarios / 240 correlated variants before model inference")
    else:
        print(json.dumps(evaluate(args.output, args.bundle), indent=2))


if __name__ == "__main__":
    main()
