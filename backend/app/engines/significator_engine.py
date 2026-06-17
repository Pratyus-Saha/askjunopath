"""Internal base KP A/B/C/D house significator ladder engine.

This computes the *base structural* significator ladder for every house from
already-computed chart data. It is **internal only**: it returns a plain
mapping and never touches the public chart payload. The reserved public
significator fields (``houses[].significators``,
``planets[].significator_of_houses``, ``planets[].significator_levels``) stay
unpopulated under D023 — this engine does not fill them and the chart router
does not call it.

Base A/B/C/D ladder (D025), house-centric:

* ``A`` — planets whose KP star lord is one of the *direct occupants* of the
  house.
* ``B`` — the *direct occupants* of the house.
* ``C`` — planets whose KP star lord is the *house owner* (``cusp_sign_lord``).
* ``D`` — the *house owner* (``cusp_sign_lord``).

The planet-centric reading is the transpose of the same relation: a planet
signifies the houses occupied by its star lord (A), occupied by itself (B),
owned by its star lord (C), and owned by itself (D).

Scope (D025), deliberately narrow for deterministic fixture validation:

* Only the 9 classical planets participate: Sun, Moon, Mars, Mercury, Jupiter,
  Venus, Saturn, Rahu, Ketu. Outer planets, the Lagna, and house cusps are
  ignored everywhere.
* Rahu and Ketu are treated as **normal planet names** for star-lord matching
  and as possible occupants. This v1 ladder does NOT implement node agency
  through sign lord, conjunction, aspect, or representation; that must be
  restored before serious prediction/timing launch.
* No sub-lord filtering, no conjunction/aspect agency, no prediction logic, and
  no API exposure.

Inputs:

* ``planets`` — the chart's planet objects. Each must carry ``name`` and a KP
  block exposing ``star_lord`` (``planet["kp"]["star_lord"]``). The star lord
  is the nakshatra (star) lord at the planet's longitude, owned by the KP
  engine.
* ``houses`` — the chart's house objects. Each must carry ``house`` (1..12),
  ``cusp_sign_lord`` (the house owner), and ``occupants`` (the direct
  occupants, filled by ``house_engine`` via JHora bhava spans, D024).

Both ``Mapping`` (dict) and attribute-style objects are accepted. The input
chart payload is read only, never mutated.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# Canonical planet order — used for every emitted list so output is stable and
# deterministic regardless of input ordering (AGENTS.md §4).
CANONICAL_PLANET_ORDER: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
)
SUPPORTED_PLANETS: frozenset[str] = frozenset(CANONICAL_PLANET_ORDER)

HOUSE_COUNT = 12


def _field(obj: Mapping[str, Any] | Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _star_lord(planet: Mapping[str, Any] | Any) -> str:
    """Return a planet's KP star lord from its ``kp`` block.

    Falls back to the nakshatra block's ``lord`` (the same star lord) so the
    engine still works on chart objects that carry only a nakshatra block.
    """
    kp = None
    try:
        kp = _field(planet, "kp")
    except (KeyError, AttributeError):
        kp = None
    if kp is not None:
        return str(_field(kp, "star_lord"))

    nakshatra = _field(planet, "nakshatra")
    if nakshatra is None:
        raise ValueError(
            f"planet {_field(planet, 'name')!r} has no kp.star_lord or "
            "nakshatra.lord to read its star lord from"
        )
    return str(_field(nakshatra, "lord"))


def _canonical(names: Iterable[str]) -> list[str]:
    """Filter to supported planets, dedupe, and order canonically."""
    present = set(names)
    return [name for name in CANONICAL_PLANET_ORDER if name in present]


def compute_house_significator_ladders(
    planets: Iterable[Mapping[str, Any] | Any],
    houses: Iterable[Mapping[str, Any] | Any],
) -> dict[int, dict[str, list[str]]]:
    """Compute the base A/B/C/D ladder for every house.

    Returns a mapping ``{house_number: {"A": [...], "B": [...], "C": [...],
    "D": [...]}}``. Every list is filtered to the 9 classical planets,
    deduplicated, and ordered canonically. The input chart payload is not
    mutated and no public chart field is populated.

    Raises:
        ValueError: if a house owner (``cusp_sign_lord``) is not one of the 9
            supported classical planets — this is a loud, deterministic failure
            rather than a silently skipped house.
    """
    # planet name -> its KP star lord, classical planets only.
    star_lord_by_planet: dict[str, str] = {}
    for planet in planets:
        name = str(_field(planet, "name"))
        if name not in SUPPORTED_PLANETS:
            # Ignore outer planets, Lagna, cusps (D025 scope).
            continue
        star_lord_by_planet[name] = _star_lord(planet)

    ladders: dict[int, dict[str, list[str]]] = {}
    for house in houses:
        house_number = int(_field(house, "house"))

        owner = _field(house, "cusp_sign_lord")
        if owner not in SUPPORTED_PLANETS:
            raise ValueError(
                f"house {house_number} owner (cusp_sign_lord) {owner!r} is not "
                "one of the 9 supported classical planets"
            )

        # Direct occupants, classical planets only (B).
        occupant_names = [
            name
            for name in (str(n) for n in _field(house, "occupants"))
            if name in SUPPORTED_PLANETS
        ]
        occupant_set = set(occupant_names)

        # A: planets whose star lord occupies this house.
        a_planets = [
            name
            for name, star_lord in star_lord_by_planet.items()
            if star_lord in occupant_set
        ]
        # C: planets whose star lord owns this house.
        c_planets = [
            name
            for name, star_lord in star_lord_by_planet.items()
            if star_lord == owner
        ]

        ladders[house_number] = {
            "A": _canonical(a_planets),
            "B": _canonical(occupant_names),
            "C": _canonical(c_planets),
            "D": [owner],
        }

    return ladders
