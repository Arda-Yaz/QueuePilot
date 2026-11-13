"""One prespecified word+character ablation; checkpoint results are exploratory."""

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
import yaml
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline

from experiments.development_analysis import load_development_data, prediction_frame, summarize
from src.hashing import calculate_file_sha256
from src.paths import BASELINE_MODEL_PATH, DATA_PATH, REPORT_DATA_DIR, ROOT_DIR
from src.routing_utils import select_threshold
from src.train_baseline import build_baseline_pipeline


def build_candidate(params: dict[str, Any]) -> Pipeline:
    reference = build_baseline_pipeline(params)
    return Pipeline([
        ("features", FeatureUnion([
            ("word", clone(reference.named_steps["tfidf"])),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                    min_df=2, max_features=50000, sublinear_tf=True)),
        ])),
        ("classifier", clone(reference.named_steps["classifier"])),
    ])


def development_coverage(predictions: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    selected, curve = select_threshold(predictions, target_accuracy=0.90, alpha=0.05,
                                      min_accepted_samples=50)
    return ({"eligible": selected is not None,
             "selected": selected.to_dict() if selected is not None else None,
             "interpretation": "Exploratory checkpoint fit/selection; NOT independent risk confirmation"}, curve)


def meets_screen(reference: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """A development recommendation only; never changes model selection artifacts."""
    if not reference["coverage"]["eligible"] or not candidate["coverage"]["eligible"]:
        return False
    return bool(
        candidate["analysis"]["classification"]["macro avg"]["f1-score"]
        >= reference["analysis"]["classification"]["macro avg"]["f1-score"]
        and candidate["coverage"]["selected"]["coverage"]
        >= reference["coverage"]["selected"]["coverage"] + 0.01
        and candidate["analysis"]["classification"]["Administrative rights"]["f1-score"]
        >= reference["analysis"]["classification"]["Administrative rights"]["f1-score"] - 0.02
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT_DIR / ".checks/development-analysis")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "comparison_plan.json").exists():
        raise RuntimeError("Plan already exists; use a new output directory for another experiment")
    params = yaml.safe_load((ROOT_DIR / "params.yaml").read_text(encoding="utf-8"))["baseline"]
    train, checkpoint = load_development_data()
    reference = joblib.load(BASELINE_MODEL_PATH)
    metadata = json.loads((ROOT_DIR / "artifacts/baseline_metadata.json").read_text(encoding="utf-8"))
    if calculate_file_sha256(BASELINE_MODEL_PATH) != metadata["model_sha256"]:
        raise RuntimeError("Reference model/metadata mismatch")
    if metadata["scikit_learn_version"] != sklearn.__version__:
        raise RuntimeError("Use the reference model's sklearn environment for this comparison")
    if any(metadata["hyperparameters"][key] != value for key, value in params.items()):
        raise RuntimeError("Reference hyperparameters differ from comparison parameters")
    plan = {
        "hypothesis": "Character 3-5 grams may complement word unigrams/bigrams on short technical fragments and spelling/morphology; not an established cause",
        "candidates": ["frozen_reference", "word_plus_char_wb_3_5"],
        "unchanged": {"baseline_params": params, "calibration": "sigmoid 5-fold CV on train; n_jobs=1"},
        "added_features": {"analyzer": "char_wb", "ngram_range": [3, 5], "min_df": 2,
                           "max_features": 50000, "sublinear_tf": True, "feature_weight": 1.0},
        "screen": "checkpoint Macro-F1 no loss; exploratory CP-gated coverage +1pp; Administrative rights F1 loss <=2pp",
        "no_promotion": "No risk/calibration/test partition inspected; passing screen still needs new independent risk confirmation",
        "dataset_sha256": calculate_file_sha256(DATA_PATH),
        "reference_model_sha256": calculate_file_sha256(BASELINE_MODEL_PATH),
        "split_sha256": {name: calculate_file_sha256(REPORT_DATA_DIR / f"{name}_ids.csv")
                         for name in ("train", "checkpoint")},
        "python": platform.python_version(), "sklearn": sklearn.__version__,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip(),
        "experiment_source": {p.relative_to(ROOT_DIR).as_posix(): calculate_file_sha256(p)
                              for p in sorted((ROOT_DIR / "experiments").glob("*.py"))},
    }
    (args.output / "comparison_plan.json").write_text(json.dumps(plan, indent=2) + "\n",
                                                       encoding="utf-8", newline="\n")
    records: dict[str, Any] = {}
    predictions = {}
    for name, model in (("reference", reference), ("word_char", None)):
        started = time.perf_counter()
        if model is None:
            model = CalibratedClassifierCV(estimator=build_candidate(params), method="sigmoid", cv=5, n_jobs=1)
            print("Fitting single word+character candidate; checkpoint is never used for fitting", flush=True)
            model.fit(train["Document"], train["Topic_group"])
            joblib.dump(model, args.output / "word_char.joblib")
        pred = prediction_frame(model, checkpoint)
        predictions[name] = pred
        coverage, curve = development_coverage(pred)
        curve.to_csv(args.output / f"{name}_development_curve.csv", index=False)
        records[name] = {"analysis": summarize(pred, model.classes_.tolist()), "coverage": coverage,
                         "elapsed_seconds": time.perf_counter() - started}
        print(f"{name}: checkpoint Macro-F1={records[name]['analysis']['classification']['macro avg']['f1-score']:.6f}", flush=True)
    ref, cand = predictions["reference"], predictions["word_char"]
    assert ref["ticket_id"].equals(cand["ticket_id"])
    paired = {"corrected": int((~ref["correct"] & cand["correct"]).sum()),
              "regressed": int((ref["correct"] & ~cand["correct"]).sum())}
    cases = ref[["ticket_id", "true_label", "predicted_label", "confidence", "correct"]].merge(
        cand[["ticket_id", "predicted_label", "confidence", "correct"]], on="ticket_id",
        suffixes=("_reference", "_candidate"), validate="one_to_one")
    private = ROOT_DIR / "reports/private/development-analysis"
    private.mkdir(parents=True, exist_ok=True)
    cases.to_csv(private / "paired_checkpoint_predictions.csv", index=False)
    result = {"plan_sha256": calculate_file_sha256(args.output / "comparison_plan.json"),
              "candidate_model_sha256": calculate_file_sha256(args.output / "word_char.joblib"),
              "models": records, "paired": paired,
              "meets_prespecified_development_screen": meets_screen(records["reference"], records["word_char"]),
              "production_model_changed": False}
    (args.output / "comparison_results.json").write_text(json.dumps(result, indent=2) + "\n",
                                                          encoding="utf-8", newline="\n")
    print(json.dumps({"paired": paired, "meets_screen": result["meets_prespecified_development_screen"]}))


if __name__ == "__main__":
    main()
