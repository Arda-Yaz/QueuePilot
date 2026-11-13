"""Freeze a local model pair, choose new risk thresholds, then audit on a separate batch.

All outputs are private local evaluation packages. This module cannot promote a
model, write serving artifacts or use an old holdout as independent new data.
"""

import argparse
import base64
import datetime
import json
import platform
import shutil
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.metrics import classification_report

from experiments.development_analysis import prediction_frame
from experiments.independent_data import load_batch, original_text_hashes
from src.hashing import calculate_file_sha256
from src.paths import BASELINE_MODEL_PATH, DATA_PATH, ROOT_DIR
from src.routing_utils import clopper_pearson_lower, select_threshold

POLICY: dict[str, Any] = {
    "target_accuracy": 0.90, "family_alpha": 0.05, "model_count": 2,
    "threshold_start": 0.10, "threshold_stop": 1.00, "threshold_step": 0.01,
    "min_accepted_samples": 50, "observed_coverage_gain": 0.01,
    "macro_f1_loss_allowed": 0.0, "admin_f1_loss_allowed": 0.02,
    "no_automatic_promotion": True,
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def runtime_environment() -> dict[str, str]:
    return {"python": platform.python_version(), "sklearn": sklearn.__version__,
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__}


def source_snapshot() -> dict[str, str]:
    paths = sorted((ROOT_DIR / "experiments").glob("*.py"))
    paths += [ROOT_DIR / "src" / name for name in ("routing_utils.py", "ticket_text.py", "hashing.py")]
    return {path.relative_to(ROOT_DIR).as_posix(): base64.b64encode(path.read_bytes()).decode("ascii")
            for path in paths}


def freeze_bundle(output: Path) -> dict[str, Any]:
    development = ROOT_DIR / "reports/development/2026-11-12"
    plan = json.loads((development / "comparison_plan.json").read_text(encoding="utf-8"))
    results = json.loads((development / "comparison_results.json").read_text(encoding="utf-8"))
    if calculate_file_sha256(development / "comparison_plan.json") != results["plan_sha256"]:
        raise RuntimeError("Development plan/results mismatch")
    for name, sha in plan["experiment_source"].items():
        if calculate_file_sha256(ROOT_DIR / name) != sha:
            raise RuntimeError(f"Development source changed: {name}")
    models = {"reference": BASELINE_MODEL_PATH,
              "candidate": ROOT_DIR / ".checks/development-analysis/word_char.joblib"}
    expected = {"reference": plan["reference_model_sha256"],
                "candidate": results["candidate_model_sha256"]}
    for name, path in models.items():
        if calculate_file_sha256(path) != expected[name]:
            raise RuntimeError(f"Frozen {name} model hash mismatch")
    if sklearn.__version__ != plan["sklearn"]:
        raise RuntimeError("Use the original comparison's sklearn version")
    labels = joblib.load(models["reference"]).classes_.tolist()
    if joblib.load(models["candidate"]).classes_.tolist() != labels:
        raise RuntimeError("Candidate/reference label schema mismatch")
    output.mkdir(parents=True, exist_ok=False)
    for name, path in models.items():
        shutil.copyfile(path, output / f"{name}.joblib")
    write_json(output / "source_snapshot.json", source_snapshot())
    for name in ("comparison_plan.json", "comparison_results.json"):
        shutil.copyfile(development / name, output / name)
    manifest = {
        "schema_version": 1, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy": POLICY, "labels": labels, "original_dataset_sha256": plan["dataset_sha256"],
        "environment": runtime_environment(),
        "files": {p.name: calculate_file_sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
        "models": {name: f"{name}.joblib" for name in models},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def verify_bundle(bundle: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or manifest["policy"] != POLICY:
        raise RuntimeError("Frozen protocol changed or unsupported bundle version")
    if manifest["models"] != {"reference": "reference.joblib", "candidate": "candidate.joblib"}:
        raise RuntimeError("Unexpected frozen model pair")
    required = {"reference.joblib", "candidate.joblib", "source_snapshot.json",
                "comparison_plan.json", "comparison_results.json"}
    if set(manifest["files"]) != required:
        raise RuntimeError("Incomplete frozen package")
    for name, sha in manifest["files"].items():
        path = bundle / name
        if path.is_symlink() or calculate_file_sha256(path) != sha:
            raise RuntimeError(f"Frozen package file changed: {name}")
    snapshot = json.loads((bundle / "source_snapshot.json").read_text(encoding="utf-8"))
    if source_snapshot() != snapshot:
        raise RuntimeError("Evaluator sources changed after freeze; do not silently change the protocol")
    if manifest["environment"] != runtime_environment():
        raise RuntimeError("Runtime environment differs from the frozen environment")
    return manifest


def evaluate(
    mode: str, bundle: Path, csv_path: Path, attestation: Path, output: Path,
    risk_path: Path | None = None,
) -> dict[str, Any]:
    if mode not in {"risk", "audit"}:
        raise ValueError("Evaluation mode must be risk or audit")
    manifest = verify_bundle(bundle)
    if calculate_file_sha256(DATA_PATH) != manifest["original_dataset_sha256"]:
        raise RuntimeError("Original dataset needed for overlap checks is missing/changed")
    forbidden = original_text_hashes(DATA_PATH)
    risk: dict[str, Any] | None = None
    if mode == "audit":
        if risk_path is None:
            raise ValueError("Audit requires the completed risk result")
        receipt = risk_path.with_suffix(".sha256")
        if receipt.read_text(encoding="utf-8").strip() != calculate_file_sha256(risk_path):
            raise RuntimeError("Risk result changed after threshold selection")
        risk = json.loads(risk_path.read_text(encoding="utf-8"))
        if (risk.get("stage") != "risk" or risk["bundle_sha256"] != calculate_file_sha256(bundle / "manifest.json")
                or not all(m["selected"] is not None for m in risk["models"].values())):
            raise RuntimeError("Audit needs eligible frozen thresholds for both models")
        forbidden.update(risk["text_sha256"])
        expected_predictions = {f"{name}_predictions.csv" for name in manifest["models"]}
        if set(risk.get("prediction_sha256", {})) != expected_predictions:
            raise RuntimeError("Incomplete risk prediction provenance")
        for name, sha in risk["prediction_sha256"].items():
            if calculate_file_sha256(risk_path.parent / name) != sha:
                raise RuntimeError("Risk predictions changed after threshold selection")
    frame, declaration = load_batch(csv_path, attestation, manifest["labels"], forbidden,
                                    set(risk["id_sha256"]) if risk is not None else None)
    output.mkdir(parents=True, exist_ok=False)
    intake = {"stage": mode, "bundle_sha256": calculate_file_sha256(bundle / "manifest.json"),
              "input_sha256": calculate_file_sha256(csv_path),
              "attestation_sha256": calculate_file_sha256(attestation), "declaration": declaration,
              "n": len(frame), "class_counts": frame["Topic_group"].value_counts().to_dict(),
              "text_sha256": frame["text_sha256"].tolist(), "id_sha256": frame["id_sha256"].tolist(),
              "models": {}, "automatic_promotion": False,
              "independence": "Owner declaration plus exact normalized overlap checks; not proof against near duplicates or hidden prior use"}
    if risk_path is not None:
        intake["risk_result_sha256"] = calculate_file_sha256(risk_path)
    write_json(output / "intake.json", intake)
    data = frame.set_index("external_id")
    records: dict[str, Any] = {}
    for name, filename in manifest["models"].items():
        model = joblib.load(bundle / filename)  # Only locally created, hash-verified trusted bundles.
        predictions = prediction_frame(model, data)
        predictions.to_csv(output / f"{name}_predictions.csv", index=False)
        if mode == "risk":
            selected, curve = select_threshold(
                predictions, threshold_start=POLICY["threshold_start"], threshold_stop=POLICY["threshold_stop"],
                threshold_step=POLICY["threshold_step"], target_accuracy=POLICY["target_accuracy"],
                alpha=POLICY["family_alpha"] / POLICY["model_count"],
                min_accepted_samples=POLICY["min_accepted_samples"],
            )
            curve.to_csv(output / f"{name}_threshold_curve.csv", index=False)
            records[name] = {"selected": selected.to_dict() if selected is not None else None}
        else:
            assert risk is not None
            threshold = float(risk["models"][name]["selected"]["threshold"])
            accepted = predictions[predictions["confidence"] >= threshold]
            correct = int(accepted["correct"].sum())
            lower = clopper_pearson_lower(correct, len(accepted), POLICY["family_alpha"] / POLICY["model_count"])
            records[name] = {
                "threshold": threshold, "accepted": len(accepted), "correct": correct,
                "coverage": len(accepted) / len(predictions),
                "accepted_accuracy": correct / len(accepted) if len(accepted) else None,
                "accepted_accuracy_lower": lower,
                "accuracy_gate_met": len(accepted) >= POLICY["min_accepted_samples"] and lower >= POLICY["target_accuracy"],
                "classification": classification_report(predictions["true_label"], predictions["predicted_label"],
                                                         labels=manifest["labels"], output_dict=True, zero_division=0),
            }
    intake["models"] = records
    intake["prediction_sha256"] = {f"{name}_predictions.csv": calculate_file_sha256(output / f"{name}_predictions.csv")
                                    for name in manifest["models"]}
    intake["decision"] = (
        "ready_for_separate_audit" if all(r["selected"] is not None for r in records.values()) else "risk_gate_not_met"
    ) if mode == "risk" else "review_required_no_automatic_promotion"
    if mode == "audit":
        intake["observed_coverage_gain"] = records["candidate"]["coverage"] - records["reference"]["coverage"]
        intake["coverage_gain_is_point_estimate"] = True
        intake["both_accuracy_gates_met"] = all(r["accuracy_gate_met"] for r in records.values())
        ref = records["reference"]["classification"]
        cand = records["candidate"]["classification"]
        admin = "Administrative rights"
        has_admin = admin in cand and int(cand[admin]["support"]) > 0
        intake["review_screen"] = {
            "all_classes_observed": set(frame["Topic_group"]) == set(manifest["labels"]),
            "macro_f1_no_loss": cand["macro avg"]["f1-score"] >= ref["macro avg"]["f1-score"] - POLICY["macro_f1_loss_allowed"],
            "admin_f1_within_margin": has_admin and cand[admin]["f1-score"] >= ref[admin]["f1-score"] - POLICY["admin_f1_loss_allowed"],
            "observed_coverage_gain_met": intake["observed_coverage_gain"] >= POLICY["observed_coverage_gain"],
        }
        intake["prespecified_review_screen_met"] = intake["both_accuracy_gates_met"] and all(intake["review_screen"].values())
    result_path = output / f"{mode}_result.json"
    write_json(result_path, intake)
    result_path.with_suffix(".sha256").write_text(calculate_file_sha256(result_path) + "\n", encoding="utf-8", newline="\n")
    return intake


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "risk", "audit"])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--attestation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--risk-result", type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        freeze_bundle(args.bundle)
        print("Frozen local model pair and protocol. No new-data evaluation performed.")
        return
    if args.csv is None or args.attestation is None or args.output is None:
        parser.error("risk/audit require --csv, --attestation and --output")
    result = evaluate(args.mode, args.bundle, args.csv, args.attestation, args.output, args.risk_result)
    print(json.dumps({"stage": args.mode, "n": result["n"], "decision": result["decision"]}))


if __name__ == "__main__":
    main()
