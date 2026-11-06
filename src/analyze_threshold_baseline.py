"""Threshold selection CLI for the Baseline backend."""

from src.paths import METRICS_DIR, ROOT_DIR
from src.threshold_analysis import run_threshold_analysis

INPUT_PATH = METRICS_DIR / "baseline_tune_predictions.csv"
OUTPUT_PATH = METRICS_DIR / "baseline_threshold_analysis.csv"
THRESHOLD_PATH = METRICS_DIR / "baseline_selected_threshold.json"
MODEL_PATH = ROOT_DIR / "artifacts" / "baseline.joblib"



def main() -> None:
    run_threshold_analysis(
        INPUT_PATH, OUTPUT_PATH, THRESHOLD_PATH, MODEL_PATH,
        ROOT_DIR / "params.yaml", "Baseline",
    )


if __name__ == "__main__":
    main()
