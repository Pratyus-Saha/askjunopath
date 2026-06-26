"""Static disclaimer for the synthesis layer (Phase 2).

A single source of truth for the user-facing honesty disclaimer. It is a fixed
string — Swiss Ephemeris for the positions, KP principles for the reading, and a
plain statement that astrology's predictive accuracy is unproven and this is not
professional advice.
"""

from __future__ import annotations

_DISCLAIMER = (
    "AskJunoPath computes chart positions using Swiss Ephemeris "
    "and explains them using KP astrology principles. Astrology's "
    "predictive accuracy is unproven. This is not professional advice."
)


def get_disclaimer() -> str:
    """Return the fixed synthesis-layer disclaimer string."""
    return _DISCLAIMER
