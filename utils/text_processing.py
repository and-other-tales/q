# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Utilities for working with manuscript text.
"""

from __future__ import annotations

import re
from typing import List


def split_text_into_paragraphs(text: str) -> List[str]:
    """
    Split the provided text into paragraphs using flexible heuristics.

    We primarily use blank lines as separators, but fall back to sentence-aware
    line joins when the author only inserted single newlines between paragraphs.
    """
    if not text:
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # First pass: split on blank lines (including whitespace-only lines).
    raw_paragraphs = [
        block.strip()
        for block in re.split(r"\n\s*\n", normalized)
        if block.strip()
    ]

    # If we only detected one paragraph but there are line breaks, attempt a
    # smarter split that treats sentence-ending punctuation followed by an
    # uppercase letter as a paragraph boundary.
    if len(raw_paragraphs) <= 1 and "\n" in normalized:
        candidate_paragraphs: List[str] = []
        current_lines: List[str] = []

        lines = normalized.split("\n")

        for line in lines:
            stripped = line.strip()

            # Preserve deliberate blank lines as hard breaks.
            if not stripped:
                if current_lines:
                    candidate_paragraphs.append(" ".join(current_lines).strip())
                    current_lines = []
                continue

            if not current_lines:
                current_lines.append(stripped)
                continue

            previous_line = current_lines[-1]
            last_char = previous_line[-1] if previous_line else ""
            first_char = stripped[0]

            should_break = False

            if last_char in ".!?\"””" and first_char.isupper():
                should_break = True
            elif stripped.startswith(("- ", "* ", "• ")):
                should_break = True
            elif stripped[:3].isdigit() and (last_char in ".!?" or previous_line.endswith(":")):
                should_break = True

            if should_break:
                candidate_paragraphs.append(" ".join(current_lines).strip())
                current_lines = [stripped]
            else:
                current_lines.append(stripped)

        if current_lines:
            candidate_paragraphs.append(" ".join(current_lines).strip())

        if candidate_paragraphs:
            raw_paragraphs = candidate_paragraphs

    return raw_paragraphs
