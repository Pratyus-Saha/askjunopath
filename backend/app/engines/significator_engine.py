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
from dataclasses import dataclass
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


# ===========================================================================
# Node agency v2 (D028) — node-aware significators, internal only.
#
# The base ladder above is node-blind (D025): Rahu/Ketu are plain names for
# star-lord matching and possible occupants, with no node sign-lord/conjunction/
# aspect agency. This section adds a SEPARATE node-aware computation on top of
# that baseline. It is internal only — like the base ladder it returns plain
# objects, reads the chart read-only, populates no public chart field
# (``houses[].significators``, ``planets[].significator_of_houses``,
# ``planets[].significator_levels`` stay reserved under D023), and bumps no
# schema/engine version. The chart router does not call it.
#
# Model (D028). A node (Rahu/Ketu) acts as an *agent* for the classical planets
# it represents, resolved through three deterministic channels:
#
#   * sign lord  — the dispositor of the sign the node occupies (``sign_lord``);
#   * conjunction — classical planets in the same sign (rashi) as the node;
#   * aspect — classical planets casting Parashari graha drishti onto the node's
#     sign (every planet aspects the 7th sign; Mars also 4th/8th, Jupiter 5th/9th,
#     Saturn 3rd/10th).
#
# The node's star lord is already represented by the base ladder (its A/C-level
# houses), so it is not added again. Agency is bidirectional and single-pass: the
# node gains each agent's node-blind significations, and reciprocally each agent
# gains the house the node occupies (nodes own no house). Borrowing reads only
# node-blind significations, so the pass is order-independent and free of
# node-to-node feedback; only the seven classical planets are ever agents.
#
# AstroSage comparison is external/compatibility ONLY. AstroSage is not JHora and
# the JHora final 4-level significator table is unavailable, so node-aware output
# is never claimed to have JHora parity (D028).
# ===========================================================================

SIGN_ORDER: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
SIGN_INDEX: dict[str, int] = {name: index for index, name in enumerate(SIGN_ORDER)}

# Rahu/Ketu are the shadow nodes; the other seven are the classical grahas that
# can act as significator agents for a node (a node never borrows from a node).
NODES: tuple[str, str] = ("Rahu", "Ketu")
SEVEN_CLASSICAL: tuple[str, ...] = tuple(
    name for name in CANONICAL_PLANET_ORDER if name not in NODES
)


def compute_planet_significators(
    planets: Iterable[Mapping[str, Any] | Any],
    houses: Iterable[Mapping[str, Any] | Any],
) -> dict[str, list[int]]:
    """Node-BLIND planet-centric significators: the transpose of the base ladder.

    Returns ``{planet: sorted houses}`` for the 9 classical planets. A planet
    signifies a house iff it appears at any of A/B/C/D for that house in
    :func:`compute_house_significator_ladders`. This is the documented
    planet-centric equivalence of D025 and the baseline the node-aware layer
    builds on. The input chart payload is not mutated.
    """
    ladders = compute_house_significator_ladders(planets, houses)
    houses_by_planet: dict[str, set[int]] = {
        name: set() for name in CANONICAL_PLANET_ORDER
    }
    for house_number, levels in ladders.items():
        for level in ("A", "B", "C", "D"):
            for name in levels[level]:
                houses_by_planet[name].add(house_number)
    return {name: sorted(houses_by_planet[name]) for name in CANONICAL_PLANET_ORDER}


def _casts_graha_drishti(
    source_planet: str, source_sign_idx: int, target_sign_idx: int
) -> bool:
    """Parashari sign-based graha drishti: does ``source_planet`` aspect the target sign?

    Distance is 1-indexed inclusive from the source sign to the target sign.
    Every planet aspects the 7th sign; Mars also the 4th and 8th, Jupiter the 5th
    and 9th, Saturn the 3rd and 10th. The shadow nodes cast no agency aspect
    (only the seven classical planets are ever agents), so they are never passed
    here as a source.
    """
    distance = ((target_sign_idx - source_sign_idx) % 12) + 1
    if distance == 7:
        return True
    if source_planet == "Mars" and distance in (4, 8):
        return True
    if source_planet == "Jupiter" and distance in (5, 9):
        return True
    if source_planet == "Saturn" and distance in (3, 10):
        return True
    return False


@dataclass(frozen=True)
class NodeAgency:
    """The classical planets a node represents, by channel (D028).

    ``agents`` is the canonical-ordered union of the three channels; the
    per-channel lists are kept for traceability and the comparison report.
    """

    node: str
    sign_lord: str
    conjunct: list[str]
    aspecting: list[str]
    agents: list[str]


def compute_node_agency(
    planets: Iterable[Mapping[str, Any] | Any],
) -> dict[str, NodeAgency]:
    """Resolve each present node's agent planets through the three D028 channels.

    Reads ``name``/``sign``/``sign_lord`` from each planet. Only the seven
    classical planets can be agents; a node never borrows from a node. The input
    chart payload is not mutated.
    """
    by_name: dict[str, Any] = {}
    for planet in planets:
        name = str(_field(planet, "name"))
        if name in SUPPORTED_PLANETS:
            by_name[name] = planet

    agency: dict[str, NodeAgency] = {}
    for node in NODES:
        node_obj = by_name.get(node)
        if node_obj is None:
            continue
        node_sign_idx = SIGN_INDEX[str(_field(node_obj, "sign"))]
        sign_lord = str(_field(node_obj, "sign_lord"))

        conjunct: list[str] = []
        aspecting: list[str] = []
        for other in SEVEN_CLASSICAL:
            other_obj = by_name.get(other)
            if other_obj is None:
                continue
            other_sign_idx = SIGN_INDEX[str(_field(other_obj, "sign"))]
            if other_sign_idx == node_sign_idx:
                conjunct.append(other)
            elif _casts_graha_drishti(other, other_sign_idx, node_sign_idx):
                aspecting.append(other)

        agent_set = {sign_lord, *conjunct, *aspecting}
        agency[node] = NodeAgency(
            node=node,
            sign_lord=sign_lord,
            conjunct=_canonical(conjunct),
            aspecting=_canonical(aspecting),
            agents=[name for name in SEVEN_CLASSICAL if name in agent_set],
        )
    return agency


@dataclass(frozen=True)
class NodeAwareSignificators:
    """Node-aware significators plus the node-blind baseline and agency trace.

    Internal only (like the base ladder): never written to the public chart.

    * ``planet_to_houses`` — node-aware planet -> sorted houses (9 planets).
    * ``node_blind_planet_to_houses`` — the D025 baseline, for traceability.
    * ``house_to_planets`` — the inverse of ``planet_to_houses`` (houses 1..12).
    * ``node_agency`` — per-node agent resolution.
    """

    planet_to_houses: dict[str, list[int]]
    node_blind_planet_to_houses: dict[str, list[int]]
    house_to_planets: dict[int, list[str]]
    node_agency: dict[str, NodeAgency]


def compute_node_aware_significators(
    planets: Iterable[Mapping[str, Any] | Any],
    houses: Iterable[Mapping[str, Any] | Any],
) -> NodeAwareSignificators:
    """Layer KP node agency on top of the node-blind base ladder (D028).

    A node gains the full node-blind significations of every planet it
    represents; reciprocally, each agent planet gains the house the node occupies
    (nodes own no house). Borrowing reads node-blind significations only, so the
    pass is single-step, order-independent, and free of node feedback loops. The
    seven classical planets' baseline is otherwise unchanged. The input chart
    payload is read-only and no public chart field is populated.
    """
    planets = list(planets)
    node_blind = compute_planet_significators(planets, houses)
    agency = compute_node_agency(planets)

    house_occupied: dict[str, int | None] = {}
    for planet in planets:
        name = str(_field(planet, "name"))
        if name not in SUPPORTED_PLANETS:
            continue
        try:
            value = _field(planet, "house_occupied")
        except (KeyError, AttributeError):
            value = None
        house_occupied[name] = int(value) if value is not None else None

    aware: dict[str, set[int]] = {
        name: set(node_blind[name]) for name in CANONICAL_PLANET_ORDER
    }
    for node, node_agency in agency.items():
        node_house = house_occupied.get(node)
        for agent in node_agency.agents:
            # The node borrows the agent's node-blind significations...
            aware[node].update(node_blind[agent])
            # ...and reciprocally the agent gains the house the node occupies.
            if node_house is not None:
                aware[agent].add(node_house)

    planet_to_houses = {name: sorted(aware[name]) for name in CANONICAL_PLANET_ORDER}
    house_to_planets: dict[int, list[str]] = {
        house: [] for house in range(1, HOUSE_COUNT + 1)
    }
    for name in CANONICAL_PLANET_ORDER:
        for house_number in planet_to_houses[name]:
            house_to_planets[house_number].append(name)

    return NodeAwareSignificators(
        planet_to_houses=planet_to_houses,
        node_blind_planet_to_houses=node_blind,
        house_to_planets=house_to_planets,
        node_agency=agency,
    )


def compare_significators_to_reference(
    result: NodeAwareSignificators,
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare node-aware output against an EXTERNAL reference table (e.g. AstroSage).

    The reference is a compatibility check only, never a parity judge: AstroSage
    is not JHora and the JHora final significator table is unavailable (D028).
    Differences are reported in full (``only_ours`` / ``only_reference``), never
    tuned away. Returns a JSON-friendly report.
    """
    reference_pth = {
        name: sorted(int(house) for house in reference["planet_to_houses"].get(name, []))
        for name in CANONICAL_PLANET_ORDER
    }

    planet_report: dict[str, Any] = {}
    matching: list[str] = []
    for name in CANONICAL_PLANET_ORDER:
        ours = result.planet_to_houses[name]
        theirs = reference_pth[name]
        ours_set, theirs_set = set(ours), set(theirs)
        is_match = ours_set == theirs_set
        if is_match:
            matching.append(name)
        planet_report[name] = {
            "ours": ours,
            "reference": theirs,
            "match": is_match,
            "only_ours": sorted(ours_set - theirs_set),
            "only_reference": sorted(theirs_set - ours_set),
        }

    return {
        "reference_source": str(reference.get("source", "unknown")),
        "reference_is_judge": bool(reference.get("is_judge", False)),
        "external_reference_only": bool(reference.get("external_reference_only", True)),
        "planet_to_houses": planet_report,
        "summary": {
            "planets_total": len(CANONICAL_PLANET_ORDER),
            "planets_matching": len(matching),
            "matching_planets": matching,
            "differing_planets": [
                name for name in CANONICAL_PLANET_ORDER if name not in matching
            ],
        },
    }
