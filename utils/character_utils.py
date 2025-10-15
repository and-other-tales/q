# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Utility helpers for working with detected characters.
"""

from __future__ import annotations

from typing import Dict, Iterable, List


def filter_confirmed_characters(
    detected_characters: Iterable[str],
    confirmed_profiles: Dict[str, object],
) -> List[str]:
    """
    Restrict detected character names to those confirmed by the user, while
    tolerating simple variations (e.g. nicknames or partial matches).
    """
    detected_list = [name for name in detected_characters if name]
    if not confirmed_profiles:
        # When no profiles are confirmed yet, preserve detected order.
        return detected_list

    confirmed_names = list(confirmed_profiles.keys())
    filtered: List[str] = []

    for candidate in detected_list:
        if candidate in confirmed_profiles:
            filtered.append(candidate)
            continue

        candidate_first = candidate.split()[0]
        match = None

        for confirmed in confirmed_names:
            if candidate in confirmed or confirmed in candidate:
                match = confirmed
                break

            if confirmed.split()[0] == candidate_first:
                match = confirmed
                break

        if match:
            filtered.append(match)

    # Preserve order but remove duplicates that may appear after normalization.
    seen = set()
    unique_filtered: List[str] = []
    for name in filtered:
        if name not in seen:
            seen.add(name)
            unique_filtered.append(name)

    return unique_filtered


def generate_character_voice_description(character_name: str) -> str:
    """
    Provide a lightweight default description for a newly detected character.
    """
    if not character_name:
        return "Clear, expressive voice with natural inflection"

    lowered = character_name.lower()

    if lowered.endswith(("a", "e", "i", "y")):
        return "Gentle, melodic voice with warm undertones"

    if len(character_name) > 8:
        return "Distinguished, measured voice with authority"

    if character_name.isupper():
        return "Strong, commanding voice with clear articulation"

    return "Clear, expressive voice with natural inflection"
