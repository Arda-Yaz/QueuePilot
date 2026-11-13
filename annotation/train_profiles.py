"""Descriptive train-label vocabulary; this is not an authoritative label guide."""

import json
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from experiments.development_analysis import load_development_data
from src.paths import ROOT_DIR


def main() -> None:
    train, _ = load_development_data()
    vectorizer = TfidfVectorizer(min_df=5, max_df=0.9, ngram_range=(1, 2),
                                 max_features=30000, stop_words="english")
    matrix = vectorizer.fit_transform(train["Document"])
    terms = vectorizer.get_feature_names_out()
    global_mean = np.asarray(matrix.mean(axis=0)).ravel()
    profiles: dict[str, Any] = {}
    for label in sorted(train["Topic_group"].unique()):
        mask = train["Topic_group"].to_numpy() == label
        subset = matrix[mask]
        mean = np.asarray(subset.mean(axis=0)).ravel()
        support = np.asarray((subset > 0).sum(axis=0)).ravel()
        score = mean * np.maximum(0, np.log((mean + 1e-6) / (global_mean + 1e-6)))
        score[support < 10] = 0
        order = np.argsort(score)[::-1][:15]
        profiles[label] = {"train_rows": int(mask.sum()), "phrases": [
            {"term": str(terms[i]), "documents": int(support[i]), "score": float(score[i])} for i in order
        ]}
    output = ROOT_DIR / "reports/private/taxonomy-pilot-v1/train_label_profiles.json"
    output.write_text(json.dumps({"interpretation": "Empirical associations in train labels, not verified class definitions",
                                  "profiles": profiles}, indent=2) + "\n", encoding="utf-8", newline="\n")
    for label, profile in profiles.items():
        print(label, [entry["term"] for entry in profile["phrases"][:10]])


if __name__ == "__main__":
    main()
