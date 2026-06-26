"""Strict payload builder for the Gemini synthesis layer (Phase 2).

The synthesis layer turns the engines' *unified prediction contract* into a
human explanation, but it must never hand Gemini a free-text surface it could
parrot or embellish. This module is the gate: it reduces a unified engine output
dict to a strict, name-and-number-only JSON payload.

The payload contains **only** computed values that map directly back to the
engine output — planet names with their natal longitudes, house numbers with
their cusp longitudes, the cusp sub-lords, the confidence tier and the
``signal_strength`` integer, the dasha period lord names, the transit-window
dates with their trigger planet names, and the event-type labels. The engine's
own templated ``summary``/``caveat``/``framing`` prose is **deliberately
dropped** — there is no interpretive text in the payload, so Gemini has no
sentence to copy and no fabrication surface to lean on.

Natal longitudes live in exactly one place in the unified contract: alongside
the planet/house identity inside the transit-window triggers (and the forward
``next_contact``). We harvest them there rather than inventing them, so every
``planets``/``houses`` entry is a value the engine actually computed.
"""

from __future__ import annotations

from typing import Any

# The nine KP grahas, canonical casing. Used to normalise the lower-cased
# ``natal_<name>`` contact-point identifiers back to real planet names.
ALL_PLANETS: tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)
_PLANET_BY_LOWER = {name.lower(): name for name in ALL_PLANETS}

# Top-level keys the built payload always carries.
PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "domain",
        "planets",
        "houses",
        "cusp_sublords",
        "confidence",
        "signal_strength",
        "dasha_period",
        "transit_windows",
        "event_types",
    }
)


def _planet_from_point(point: str) -> str | None:
    """``"natal_jupiter"`` -> ``"Jupiter"`` (canonical), else ``None``."""
    if not isinstance(point, str) or not point.startswith("natal_"):
        return None
    return _PLANET_BY_LOWER.get(point[len("natal_"):].lower())


def _house_from_point(point: str) -> int | None:
    """``"cusp_10"`` -> ``10``, else ``None``."""
    if not isinstance(point, str) or not point.startswith("cusp_"):
        return None
    try:
        return int(point[len("cusp_"):])
    except ValueError:
        return None


def _harvest_longitudes(
    engine_output: dict, planets: dict[str, float], houses: dict[str, float]
) -> None:
    """Fill ``planets``/``houses`` with natal longitudes found in the contract.

    Longitudes appear only inside transit-window triggers and the forward
    ``next_contact``; we read them straight from there. First write wins, so the
    result is deterministic regardless of how many windows touch a point.
    """
    for window in engine_output.get("transit_windows") or []:
        for trigger in window.get("triggers") or []:
            longitude = trigger.get("natal_point_longitude")
            if longitude is None:
                continue
            point = trigger.get("natal_point", "")
            planet = _planet_from_point(point)
            if planet is not None:
                planets.setdefault(planet, float(longitude))
                continue
            house = _house_from_point(point)
            if house is not None:
                houses.setdefault(str(house), float(longitude))

    next_contact = (engine_output.get("transit_summary") or {}).get("next_contact") or {}
    longitude = next_contact.get("natal_longitude")
    if longitude is not None:
        point = next_contact.get("natal_point", "")
        planet = _planet_from_point(point)
        if planet is not None:
            planets.setdefault(planet, float(longitude))
        else:
            house = _house_from_point(point)
            if house is not None:
                houses.setdefault(str(house), float(longitude))


def build_payload(engine_output: dict) -> dict:
    """Reduce a unified engine output dict to the strict Gemini payload.

    Args:
        engine_output: a unified prediction contract dict as returned by the
            career / finance / relationship engines.

    Returns:
        A JSON-serialisable dict containing only names, numbers, dates and the
        templated event-type labels — never any interpretive prose. Every field
        maps directly to a value computed by the engine.
    """
    planets: dict[str, float] = {}
    houses: dict[str, float] = {}
    _harvest_longitudes(engine_output, planets, houses)

    cusp_block = engine_output.get("cusp_sublords") or {}
    primary_houses = {
        str(house): lord
        for house, lord in (cusp_block.get("primary_houses") or {}).items()
    }
    sublord_significations = {
        lord: [int(h) for h in (signified or [])]
        for lord, signified in (cusp_block.get("sublord_significations") or {}).items()
    }

    dasha = engine_output.get("dasha_timing") or {}
    dasha_period = {
        "md_lord": dasha.get("md_lord"),
        "ad_lord": dasha.get("ad_lord"),
        "pd_lord": dasha.get("pd_lord"),
    }

    transit_windows: list[dict[str, Any]] = []
    for window in engine_output.get("transit_windows") or []:
        trigger_planets = sorted(
            {
                trigger["planet"]
                for trigger in (window.get("triggers") or [])
                if trigger.get("planet")
            }
        )
        transit_windows.append(
            {
                "start_date": window.get("start_date"),
                "end_date": window.get("end_date"),
                "trigger_planets": trigger_planets,
            }
        )

    signal_strength = engine_output.get("signal_strength", 0)
    try:
        signal_strength = int(signal_strength)
    except (TypeError, ValueError):
        signal_strength = 0

    return {
        "domain": engine_output.get("domain"),
        "planets": planets,
        "houses": houses,
        "cusp_sublords": {
            "primary_houses": primary_houses,
            "sublord_significations": sublord_significations,
        },
        "confidence": engine_output.get("confidence"),
        "signal_strength": signal_strength,
        "dasha_period": dasha_period,
        "transit_windows": transit_windows,
        "event_types": list(engine_output.get("event_types") or []),
    }


def known_planet_names(payload: dict) -> set[str]:
    """Every canonical planet name that appears anywhere in the payload.

    The union of: the ``planets`` longitude map, the primary-house cusp sub-lord
    names, the sub-lord signification keys, the dasha period lords, and the
    transit-window trigger planets. This is the reference universe a synthesised
    paragraph may legitimately cite.
    """
    names: set[str] = set()
    names.update(name for name in (payload.get("planets") or {}) if name in ALL_PLANETS)

    cusp = payload.get("cusp_sublords") or {}
    names.update(
        lord for lord in (cusp.get("primary_houses") or {}).values() if lord in ALL_PLANETS
    )
    names.update(
        lord for lord in (cusp.get("sublord_significations") or {}) if lord in ALL_PLANETS
    )

    dasha = payload.get("dasha_period") or {}
    names.update(lord for lord in dasha.values() if lord in ALL_PLANETS)

    for window in payload.get("transit_windows") or []:
        names.update(
            planet for planet in (window.get("trigger_planets") or []) if planet in ALL_PLANETS
        )
    return names


def known_house_numbers(payload: dict) -> set[int]:
    """Every house number (1..12 by construction) referenced in the payload."""
    houses: set[int] = set()

    def _add(value: Any) -> None:
        try:
            houses.add(int(value))
        except (TypeError, ValueError):
            pass

    for key in payload.get("houses") or {}:
        _add(key)

    cusp = payload.get("cusp_sublords") or {}
    for key in cusp.get("primary_houses") or {}:
        _add(key)
    for signified in (cusp.get("sublord_significations") or {}).values():
        for house in signified or []:
            _add(house)
    return houses
