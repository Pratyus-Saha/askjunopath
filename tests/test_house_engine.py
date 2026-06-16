from __future__ import annotations

from collections import Counter
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.engines.house_engine import house_of, occupants  # noqa: E402


PLANETS = [
    {"name": "Sun", "longitude": 5.0},
    {"name": "Moon", "longitude": 32.0},
    {"name": "Mars", "longitude": 61.5},
    {"name": "Mercury", "longitude": 89.999},
    {"name": "Jupiter", "longitude": 120.0},
    {"name": "Venus", "longitude": 181.0},
    {"name": "Saturn", "longitude": 212.0},
    {"name": "Rahu", "longitude": 270.0},
    {"name": "Ketu", "longitude": 359.0},
]


def equal_cusps() -> list[float]:
    return [house * 30.0 for house in range(12)]


def test_house_of_assigns_normal_interior_cases_by_span() -> None:
    cusps = equal_cusps()

    assert house_of(15.0, cusps) == 1
    assert house_of(45.0, cusps) == 2
    assert house_of(315.0, cusps) == 11


def test_house_of_handles_wraparound_across_zero_aries() -> None:
    cusps = [350.0, 10.0, 40.0, 70.0, 100.0, 130.0, 160.0, 190.0, 220.0, 250.0, 280.0, 310.0]

    assert house_of(355.0, cusps) == 1
    assert house_of(5.0, cusps) == 1
    assert house_of(349.9999, cusps) == 12


def test_planet_exactly_on_cusp_belongs_to_house_starting_at_that_cusp() -> None:
    cusps = equal_cusps()

    assert house_of(90.0, cusps) == 4


def test_planets_within_one_hundredth_degree_of_cusp_obey_half_open_span() -> None:
    cusps = equal_cusps()

    assert house_of(90.0099, cusps) == 4
    assert house_of(89.9901, cusps) == 3


def test_assignment_is_not_sign_based_when_sign_and_cusp_span_disagree() -> None:
    # House 10 starts at 28 Virgo and ends at 5 Libra. A planet at 0 Libra is
    # two degrees after the 10th cusp, so it belongs to house 10 despite sign.
    cusps = [260.0, 290.0, 320.0, 350.0, 20.0, 50.0, 80.0, 110.0, 140.0, 178.0, 185.0, 220.0]

    assert house_of(180.0, cusps) == 10


def test_occupants_assigns_every_planet_exactly_once_and_returns_all_houses() -> None:
    by_house = occupants(PLANETS, equal_cusps())

    assert set(by_house) == set(range(1, 13))
    assigned = [name for names in by_house.values() for name in names]
    assert Counter(assigned) == Counter(planet["name"] for planet in PLANETS)


def test_occupants_are_consistent_with_house_of() -> None:
    cusps = equal_cusps()
    by_house = occupants(PLANETS, cusps)
    expected_house = {
        planet["name"]: house_of(planet["longitude"], cusps) for planet in PLANETS
    }

    for house, names in by_house.items():
        for name in names:
            assert expected_house[name] == house


def test_invalid_cusp_list_length_fails_clearly() -> None:
    with pytest.raises(ValueError, match="exactly 12"):
        house_of(12.0, [0.0, 30.0])
