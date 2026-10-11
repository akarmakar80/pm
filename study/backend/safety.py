"""Blocked-terms check for searches and titles. Educator review remains the main safeguard."""

import re
from pathlib import Path

TERMS = [
    line.strip().lower()
    for line in (Path(__file__).resolve().parent / "seed" / "blocked_terms.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]
PATTERN = re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in TERMS) + r")(?!\w)", re.IGNORECASE)


def is_blocked(text: str) -> bool:
    return bool(PATTERN.search(text))
