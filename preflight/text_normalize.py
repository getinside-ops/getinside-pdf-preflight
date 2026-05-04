"""Text normalization and fuzzy matching helpers.

Designed for OCR-tolerant matching of French legal mentions. The pipeline:
1. NFKD-decompose, drop combining marks (accents).
2. Lowercase.
3. Normalize typographic variants (curly quotes, hyphens, NBSPs).
4. Collapse whitespace.

All matching is done over the normalized form. `fuzzy_contains` uses
rapidfuzz `partial_ratio` so that a needle phrase can be located inside
a larger haystack (e.g. extracted page text).
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

# Typographic substitutions applied before NFKD so we don't accidentally
# split characters that should map to a single ASCII form.
_PUNCT_MAP = str.maketrans(
    {
        "’": "'",  # right single quotation mark
        "‘": "'",  # left single quotation mark
        "“": '"',  # left double quotation mark
        "”": '"',  # right double quotation mark
        "–": "-",  # en dash
        "—": "-",  # em dash
        "−": "-",  # minus sign
        " ": " ",  # non-breaking space
        " ": " ",  # narrow no-break space
        "​": "",   # zero-width space
    }
)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Return an OCR-tolerant, accent-folded, lowercase version of ``text``."""
    if not text:
        return ""
    text = text.translate(_PUNCT_MAP)
    text = unicodedata.normalize("NFKD", text)
    # Drop combining marks (accents).
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def fuzzy_contains(haystack: str, needle: str, threshold: int = 85) -> bool:
    """Return True if ``needle`` is approximately present in ``haystack``.

    Both inputs are normalized first. Uses rapidfuzz partial_ratio so that
    short needles match anywhere in a long haystack.
    """
    if not needle:
        return True
    h = normalize(haystack)
    n = normalize(needle)
    if not h or not n:
        return False
    if n in h:
        return True
    score = fuzz.partial_ratio(n, h)
    return score >= threshold


def fuzzy_score(haystack: str, needle: str) -> float:
    """Return the partial_ratio score (0-100) of ``needle`` against ``haystack``."""
    h = normalize(haystack)
    n = normalize(needle)
    if not h or not n:
        return 0.0
    return float(fuzz.partial_ratio(n, h))


__all__ = ["normalize", "fuzzy_contains", "fuzzy_score"]
