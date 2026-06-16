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


# With equal 30-deg cusps the bhava boundaries fall at 15, 45, ... 345, so
# house H spans [30H - 45, 30H - 15) and its cusp 30(H-1) sits at the centre.
# House 1 = [345, 15) wraps 0 Aries; house 4 = [75, 105) with cusp 90.


def test_house_of_assigns_normal_interior_cases_by_bhava_span() -> None:
    cusps = equal_cusps()

    # Each cusp sits inside (at the centre of) its own house.
    assert house_of(0.0, cusps) == 1
    assert house_of(30.0, cusps) == 2
    assert house_of(120.0, cusps) == 5
    assert house_of(300.0, cusps) == 11


def test_house_of_handles_wraparound_across_zero_aries() -> None:
    # cusp_12 = 340, cusp_1 = 0, cusp_2 = 20 -> house 1 = [350, 10): it
    # straddles 0 Aries and must contain longitudes on both sides of it.
    cusps = [0.0, 20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 340.0]

    assert house_of(355.0, cusps) == 1
    assert house_of(5.0, cusps) == 1
    assert house_of(349.9999, cusps) == 12
    assert house_of(10.0, cusps) == 2


def test_cusp_is_inside_the_house_not_its_start_boundary() -> None:
    # The JHora insight (and the User 1 Kolkata Rahu case): a planet BEFORE
    # the cusp but after the bhava start still belongs to that house, because
    # the cusp is the interior reference point, not the start boundary.
    cusps = equal_cusps()

    assert house_of(80.0, cusps) == 4  # before cusp_4 (90), after start (75)
    assert house_of(90.0, cusps) == 4  # the cusp itself is interior
    assert house_of(100.0, cusps) == 4  # after the cusp, before end (105)


def test_bhava_span_start_boundary_is_inclusive() -> None:
    cusps = equal_cusps()

    # 75 is the start of house 4 (midpoint of cusp_3 and cusp_4): inclusive.
    assert house_of(75.0, cusps) == 4


def test_bhava_span_end_boundary_is_exclusive() -> None:
    cusps = equal_cusps()

    # 105 is the end of house 4 == start of house 5: exclusive -> house 5.
    assert house_of(105.0, cusps) == 5
    assert house_of(104.9999, cusps) == 4


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
