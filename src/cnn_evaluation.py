"""Ordered CNN batch predictions shared by tune and calibration evaluation."""

import torch
from torch.utils.data import DataLoader

from src.textcnn import TextCNN


def predict_batches(
    model: TextCNN,
    loader: DataLoader[tuple[torch.Tensor, torch.Tensor]],
    device: torch.device,
) -> tuple[list[int], list[float]]:
    predictions: list[int] = []
    confidences: list[float] = []
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            logits = model(inputs)
            probabilities = torch.softmax(logits, dim=1)
            confidence, predicted = probabilities.max(dim=1)
            predictions.extend(predicted.cpu().tolist())
            confidences.extend(confidence.cpu().tolist())
    return predictions, confidences
