"""Held-out calibration evaluation for the TextCNN model.

Evaluates ECE and Brier score on the CALIBRATION partition â€” the independent
10% hold-out that is never used for training or threshold selection.

See ``evaluate_calibration_baseline.py`` for the full methodology note.
"""

import json

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.cnn_data import TicketDataset
from src.cnn_evaluation import predict_batches
from src.data import load_calibration_split, load_data
from src.evaluate import build_prediction_frame, calculate_calibration_metrics
from src.hashing import calculate_file_sha256
from src.paths import CNN_MODEL_PATH, METRICS_DIR, ROOT_DIR
from src.textcnn import TextCNN

CNN_DIR = ROOT_DIR / "artifacts" / "cnn"
OUTPUT_PATH = METRICS_DIR / "cnn_calibration_holdout_metrics.json"


def main() -> None:
    with open(CNN_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab = json.load(f)

    with open(CNN_DIR / "labels.json", "r", encoding="utf-8") as f:
        labels = json.load(f)

    with open(CNN_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    df = load_data()
    calib_df = load_calibration_split(df)

    label_to_id = {label: index for index, label in enumerate(labels)}
    y_calib = [label_to_id[label] for label in calib_df["Topic_group"]]

    calib_dataset = TicketDataset(
        texts=calib_df["Document"].tolist(),
        labels=y_calib,
        vocab=vocab,
        max_length=int(config["max_length"]),
    )

    calib_loader = DataLoader(calib_dataset, batch_size=64, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    model = TextCNN(
        vocab_size=len(vocab),
        embedding_dim=config["embedding_dim"],
        num_filters=config["num_filters"],
        kernel_sizes=config["kernel_sizes"],
        num_classes=config["num_classes"],
        dropout=config["dropout"],
    ).to(device)

    state_dict = torch.load(
        CNN_DIR / "textcnn.pt",
        map_location=device,
        weights_only=True,
    )
    model.load_state_dict(state_dict)
    model.eval()

    all_predictions, all_confidences = predict_batches(model, calib_loader, device)

    true_labels = [labels[index] for index in y_calib]
    predicted_labels = [labels[index] for index in all_predictions]

    results = build_prediction_frame(
        calib_df.index.to_numpy(), true_labels,
        predicted_labels, all_confidences,
    )

    calibration = calculate_calibration_metrics(
        y_true_labels=true_labels,
        y_pred_labels=np.asarray(predicted_labels),
        y_confidence=np.asarray(all_confidences),
    )

    output: dict[str, object] = {
        "partition": "calibration_holdout",
        "n_samples": int(len(results)),
        "accuracy": float(results["correct"].mean()),
        **calibration,
        "note": (
            "Calibration metrics computed on the held-out CALIBRATION partition "
            "(10% of data). This partition was never used for training or "
            "threshold selection."
        ),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({**output, "model_sha256": calculate_file_sha256(CNN_MODEL_PATH)}, f, indent=4)

    print(f"Calibration holdout accuracy: {results['correct'].mean():.4f}")
    print(f"Top label Brier score: {calibration['top_label_brier_score']:.6f}")
    print(f"ECE: {calibration['expected_calibration_error']:.6f}")
    print(f"n_samples: {len(results)}")
    print("Saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
