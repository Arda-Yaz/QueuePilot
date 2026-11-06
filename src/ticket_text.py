"""Text normalization and persistent ticket identity shared by data entry points."""

import hashlib
import re


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).lower().strip())


def ticket_id(normalized_text: str, label: str) -> str:
    """Hash the original delimiter-based representation used by split manifests."""
    return hashlib.sha256((normalized_text + "|" + label).encode("utf-8")).hexdigest()
