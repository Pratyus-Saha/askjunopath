"""House occupation helpers using JHora bhava midpoint spans.

Public house occupation (``planets[].house_occupied`` and
``houses[].occupants``) follows JHora's "House Start / Cusp / End /
Planets in it" table (D024). A house is the bhava span around its cusp:

    start_H = midpoint(prev_cusp, cusp_H)
    end_H   = midpoint(cusp_H, next_cusp)
    House H = [start_H, end_H)          (lower inclusive, upper exclusive)

The cusp sits INSIDE the house, not at its start boundary, so a planet
that lies before the cusp but after the bhava start still belongs to that
house (this is why Rahu lands in house 1 for User 1 Kolkata even though it
sits before the 1st cusp). Consecutive houses share a boundary exactly
(end_H == start_{H+1} == midpoint(cusp_H, cusp_{H+1})), so the twelve spans
tile the circle with no gap or overlap and every planet maps to exactly one
house. All math is modular across 360deg / 0deg Aries; zodiac sign is
intentionally ignored.

This supersedes the prior cusp-to-next-cusp membership rule for public
occupation. Cusp longitude is still used by the KP engine for cusp
star/sub-lord lookup; that lookup is unchanged and not computed here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


FULL_CIRCLE = 360.0
HOUSE_COUNT = 12


def _normalize_longitude(longitude: float) -> float:
    return float(longitude) % FULL_CIRCLE


def _validated_cusps(cusps: list[float]) -> list[float]:
    if len(cusps) != HOUSE_COUNT:
        raise ValueError("cusps must contain exactly 12 longitudes")

    normalized = [_normalize_longitude(cusp) for cusp in cusps]
    for index, cusp in enumerate(normalized):
        next_cusp = normalized[(index + 1) % HOUSE_COUNT]
        if (next_cusp - cusp) % FULL_CIRCLE == 0:
            house = index + 1
            raise ValueError(f"cusp span for house {house} must be non-zero")
    return normalized


def _bhava_boundaries(cusps: list[float]) -> list[float]:
    """Return the 12 bhava boundaries (midpoints between adjacent cusps).

    ``boundaries[i]`` is the midpoint between ``cusp_{i+1}`` and the next
    cusp; it is simultaneously the END of house ``i + 1`` and the START of
    house ``i + 2``. Computing each boundary once guarantees adjacent houses
    share the identical float, so the spans tile the circle exactly.
    """

    boundaries: list[float] = []
    for index in range(HOUSE_COUNT):
        cusp = cusps[index]
        next_cusp = cusps[(index + 1) % HOUSE_COUNT]
        midpoint = (cusp + ((next_cusp - cusp) % FULL_CIRCLE) / 2) % FULL_CIRCLE
        boundaries.append(midpoint)
    return boundaries


def house_of(planet_long: float, cusps: list[float]) -> int:
    """Return the 1-based house containing planet_long by bhava spans."""

    normalized_planet = _normalize_longitude(planet_long)
    normalized_cusps = _validated_cusps(cusps)
    boundaries = _bhava_boundaries(normalized_cusps)

    for index in range(HOUSE_COUNT):
        start = boundaries[(index - 1) % HOUSE_COUNT]
        end = boundaries[index]
        offset = (normalized_planet - start) % FULL_CIRCLE
        span = (end - start) % FULL_CIRCLE
        if offset < span:
            return index + 1

    raise ValueError("planet longitude did not fall within any bhava span")


def _planet_field(planet: Mapping[str, Any] | Any, field: str) -> Any:
    if isinstance(planet, Mapping):
        return planet[field]
    return getattr(planet, field)


def occupants(planets: Iterable[Mapping[str, Any] | Any], cusps: list[float]) -> dict[int, list[str]]:
    """Return every house key with the planet names occupying that house."""

    normalized_cusps = _validated_cusps(cusps)
    by_house: dict[int, list[str]] = {house: [] for house in range(1, HOUSE_COUNT + 1)}

    for planet in planets:
        name = str(_planet_field(planet, "name"))
        longitude = float(_planet_field(planet, "longitude"))
        house = house_of(longitude, normalized_cusps)
        by_house[house].append(name)

    return by_house
