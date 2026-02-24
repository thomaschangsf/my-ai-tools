"""Post-processing cleanup for converted markdown.

Fixes common artifacts from PDF-to-markdown conversion:
- Duplicate blank lines
- Broken hyphenation from line wrapping
- Unicode ligature normalization
- Trailing whitespace
"""

from __future__ import annotations

import re
import unicodedata


def cleanup(text: str) -> str:
    """Apply all post-processing steps to converted markdown."""
    text = normalize_unicode(text)
    text = fix_hyphenation(text)
    text = collapse_blank_lines(text)
    text = strip_trailing_whitespace(text)
    return text


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC form and replace common ligatures."""
    text = unicodedata.normalize("NFC", text)
    ligatures = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
    }
    for lig, replacement in ligatures.items():
        text = text.replace(lig, replacement)
    return text


def fix_hyphenation(text: str) -> str:
    """Rejoin words broken by end-of-line hyphenation.

    Matches a lowercase letter followed by a hyphen at end of line,
    then a lowercase letter at the start of the next line.
    Does NOT fix hyphens inside math blocks or code fences.
    """
    return re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)


def collapse_blank_lines(text: str) -> str:
    """Reduce runs of 3+ blank lines to exactly 2 (one empty line)."""
    return re.sub(r"\n{3,}", "\n\n", text)


def strip_trailing_whitespace(text: str) -> str:
    """Remove trailing spaces/tabs from each line."""
    return re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
