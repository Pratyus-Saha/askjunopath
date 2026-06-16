"""House occupation helpers using Placidus cusp spans.

House membership is half-open: house H spans [cusp_H, cusp_{H+1}),
with house 12 wrapping to cusp 1. Zodiac sign is intentionally ignored.
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


def house_of(planet_long: float, cusps: list[float]) -> int:
    """Return the 1-based house containing planet_long by cusp spans only."""

    normalized_planet = _normalize_longitude(planet_long)
    normalized_cusps = _validated_cusps(cusps)

    for index, cusp in enumerate(normalized_cusps):
        next_cusp = normalized_cusps[(index + 1) % HOUSE_COUNT]
        distance_from_cusp = (normalized_planet - cusp) % FULL_CIRCLE
        span = (next_cusp - cusp) % FULL_CIRCLE
        if distance_from_cusp < span:
            return index + 1

    raise ValueError("planet longitude did not fall within any cusp span")


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
