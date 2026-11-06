"""Deterministic data-preparation stage.

Owns:
- Cleaned dataset (blank/conflict removal, deduplication)
- Stable SHA-256 row IDs
- Stratified train/tune/calibration/test split IDs
- Data quality report (JSON)
- Conflicting-label report (CSV)
"""

import json

import pandas as pd
from sklearn.model_selection import train_test_split

from src.hashing import calculate_file_sha256
from src.paths import DATA_PATH, REPORT_DATA_DIR
from src.ticket_text import normalize_text
from src.ticket_text import ticket_id as _sha256_row_id

EXPECTED_LABELS = frozenset(
    {"Access", "Administrative rights", "Hardware", "HR Support",
     "Internal Project", "Miscellaneous", "Purchase", "Storage"}
)


def split_partitions(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply the source's exact three stratified split operations in order."""
    train, remaining = train_test_split(
        raw, test_size=0.30, stratify=raw["Topic_group"], random_state=42
    )
    tune, calibration_and_test = train_test_split(
        remaining, test_size=0.667, stratify=remaining["Topic_group"], random_state=42
    )
    calibration, test = train_test_split(
        calibration_and_test,
        test_size=0.50,
        stratify=calibration_and_test["Topic_group"],
        random_state=42,
    )
    return train, tune, calibration, test


def main() -> None:
    REPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(DATA_PATH)[["Document", "Topic_group"]].copy()
    total_raw = len(raw)

    # Drop nulls
    raw = raw.dropna(subset=["Document", "Topic_group"]).copy()
    null_dropped = total_raw - len(raw)

    raw["Document"] = raw["Document"].astype(str)
    raw["Topic_group"] = raw["Topic_group"].astype(str)
    raw["document_normalized"] = raw["Document"].apply(normalize_text)

    # Reject blank normalized text
    blank_mask = raw["document_normalized"].str.strip() == ""
    blank_dropped = blank_mask.sum()
    raw = raw[~blank_mask].copy()

    # Stable SHA-256 row IDs
    raw["ticket_id"] = raw.apply(
        lambda r: _sha256_row_id(r["document_normalized"], r["Topic_group"]), axis=1
    )

    # Assert uniqueness of IDs
    dup_ids = raw["ticket_id"].duplicated(keep=False)
    if dup_ids.any():
        # Duplicates will be resolved after conflict detection / dedup; flag here
        pass

    # Detect conflicting labels (same text, different labels)
    conflicts = raw.groupby("document_normalized")["Topic_group"].nunique()
    conflicting_docs = conflicts[conflicts > 1].index
    n_conflicting = int(conflicting_docs.shape[0])
    if n_conflicting > 0:
        raw[raw["document_normalized"].isin(conflicting_docs)].to_csv(
            REPORT_DATA_DIR / "conflicting_duplicate_labels.csv", index=False
        )
        raw = raw[~raw["document_normalized"].isin(conflicting_docs)].copy()

    # Exact deduplication (keep first)
    before_dedup = len(raw)
    raw = raw.drop_duplicates(subset=["document_normalized"], keep="first").copy()
    exact_duplicates_dropped = before_dedup - len(raw)

    raw = raw.set_index("ticket_id")

    # Re-check IDs are unique after dedup
    assert raw.index.is_unique, "ticket_id collisions remain after deduplication"

    # Label validation
    unexpected = set(raw["Topic_group"].unique()) - EXPECTED_LABELS
    if unexpected:
        print(f"WARNING: unexpected labels found: {unexpected}")

    # Four-way split: 70% train / 10% tune / 10% calibration / 10% test
    train_df, tune_df, calib_df, test_df = split_partitions(raw)

    # Assert disjointness
    sets = [set(train_df.index), set(tune_df.index), set(calib_df.index), set(test_df.index)]
    for i, a in enumerate(sets):
        for j, b in enumerate(sets):
            if i < j:
                overlap = a & b
                assert not overlap, f"Split {i} and {j} overlap: {len(overlap)} IDs"

    dataset_sha256 = calculate_file_sha256(DATA_PATH)

    # Persist split IDs
    for name, df in [("train", train_df), ("tune", tune_df),
                     ("calibration", calib_df), ("test", test_df)]:
        pd.DataFrame({"id": df.index}).to_csv(
            REPORT_DATA_DIR / f"{name}_ids.csv", index=False
        )

    # Persist manifest
    manifest = {
        "dataset_sha256": dataset_sha256,
        "random_seed": 42,
        "split_ratios": {"train": 0.70, "tune": 0.10, "calibration": 0.10, "test": 0.10},
        "train_rows": len(train_df),
        "tune_rows": len(tune_df),
        "calibration_rows": len(calib_df),
        "test_rows": len(test_df),
        "total_rows": len(raw),
    }
    with open(REPORT_DATA_DIR / "data_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    # Machine-readable quality report
    quality = {
        "dataset_sha256": dataset_sha256,
        "raw_rows": total_raw,
        "null_dropped": null_dropped,
        "blank_rows_dropped": int(blank_dropped),
        "conflicting_label_groups": n_conflicting,
        "exact_duplicates_dropped": exact_duplicates_dropped,
        "rows_after_cleaning": len(raw),
        "label_schema": sorted(EXPECTED_LABELS),
        "unexpected_labels": sorted(unexpected),
        "split_counts": {
            "train": len(train_df),
            "tune": len(tune_df),
            "calibration": len(calib_df),
            "test": len(test_df),
        },
    }
    with open(REPORT_DATA_DIR / "data_quality_report.json", "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=4)

    print(f"Raw rows:            {total_raw}")
    print(f"Null dropped:        {null_dropped}")
    print(f"Blank dropped:       {blank_dropped}")
    print(f"Conflicting groups:  {n_conflicting}")
    print(f"Exact dupes dropped: {exact_duplicates_dropped}")
    print(f"Clean rows:          {len(raw)}")
    print(f"Train: {len(train_df)}, Tune: {len(tune_df)}, "
          f"Calibration: {len(calib_df)}, Test: {len(test_df)}")


if __name__ == "__main__":
    main()
