"""Tests for the internal KP sub-lord lookup engine.

The engine is checked against the committed ``data/kp_249.csv`` (the same
table its lookup uses), with explicit attention to the half-open
``[start_arcsec, end_arcsec)`` boundary rule, the ``360 -> 0`` wrap, and the
absence of any off-by-one at row-end boundaries.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.engines.kp_engine import (  # noqa: E402
    FULL_ZODIAC_ARCSEC,
    KP_TABLE_PATH,
    get_kp_sub_lord,
)


def load_csv_rows() -> list[dict[str, object]]:
    with KP_TABLE_PATH.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {
                "row_index": int(row["row_index"]),
                "nakshatra_index": int(row["nakshatra_index"]),
                "nakshatra_name": row["nakshatra_name"],
                "nakshatra_lord": row["nakshatra_lord"],
                "sub_index": int(row["sub_index"]),
                "sub_lord": row["sub_lord"],
                "start_arcsec": int(row["start_arcsec"]),
                "end_arcsec": int(row["end_arcsec"]),
            }
            for row in reader
        ]


CSV_ROWS = load_csv_rows()


def deg(arcsec: int) -> float:
    return arcsec / 3600.0


def test_zero_aries_is_first_row_ketu_ketu():
    result = get_kp_sub_lord(0.0)
    assert result["star_lord"] == "Ketu"
    assert result["sub_lord"] == "Ketu"
    assert result["sub_index"] == 1
    assert result["sub_start_longitude"] == 0.0
    assert result["sub_end_longitude"] == pytest.approx(2800 / 3600.0)
    assert result["degree_in_sub"] == 0.0
    assert result["row_index"] == 1


def test_exact_sub_boundary_belongs_to_the_row_that_starts_there():
    # 2800 arcsec is the boundary between row 1 (Ketu/Ketu) and row 2 (Ketu/Venus).
    boundary = deg(2800)
    result = get_kp_sub_lord(boundary)
    assert result["row_index"] == 2
    assert result["sub_lord"] == "Venus"
    assert result["sub_index"] == 2
    assert result["sub_start_longitude"] == pytest.approx(2800 / 3600.0)
    assert result["degree_in_sub"] == 0.0


def test_just_before_boundary_stays_in_the_lower_row():
    result = get_kp_sub_lord(deg(2799))
    assert result["row_index"] == 1
    assert result["sub_lord"] == "Ketu"


def test_just_after_boundary_is_in_the_upper_row():
    result = get_kp_sub_lord(deg(2801))
    assert result["row_index"] == 2
    assert result["sub_lord"] == "Venus"


def test_359_99999_wraps_to_zero():
    # round(359.99999 * 3600) == 1_296_000, which wraps to 0 -> first row.
    result = get_kp_sub_lord(359.99999)
    assert result["arcsec"] == 0
    assert result["row_index"] == 1
    assert result["star_lord"] == "Ketu"
    assert result["sub_lord"] == "Ketu"


def test_360_wraps_to_zero():
    assert get_kp_sub_lord(360.0) == get_kp_sub_lord(0.0)


def test_tiny_negative_longitude_wraps_safely():
    result = get_kp_sub_lord(-0.0001)
    assert result["arcsec"] == 0
    assert result["row_index"] == 1
    assert result["sub_lord"] == "Ketu"


def test_large_and_negative_longitudes_normalise():
    # 360 + x and x must resolve identically; so must -360 + x.
    for base in (1.0, 47.5, 211.703178, 359.5):
        assert get_kp_sub_lord(base) == get_kp_sub_lord(base + 360.0)
        assert get_kp_sub_lord(base) == get_kp_sub_lord(base - 360.0)


def test_sub_lord_differs_from_star_lord_cross_checked_from_csv():
    # Manually from data/kp_249.csv row_index 2:
    #   "2,1,Ashwini,Ketu,2,Venus,2800,10800,..."
    # 1.0 deg = 3600 arcsec falls inside [2800, 10800), so the star lord is the
    # Ashwini nakshatra lord Ketu while the sub lord is Venus -- they differ.
    result = get_kp_sub_lord(1.0)
    assert result["star_lord"] == "Ketu"
    assert result["sub_lord"] == "Venus"
    assert result["star_lord"] != result["sub_lord"]
    assert result["sub_index"] == 2
    assert result["sub_start_longitude"] == pytest.approx(2800 / 3600.0)
    assert result["sub_end_longitude"] == pytest.approx(10800 / 3600.0)
    assert result["degree_in_sub"] == pytest.approx((3600 - 2800) / 3600.0)


def test_lookup_midpoint_agrees_with_its_csv_row():
    # The interior midpoint of every row must resolve to that exact row.
    for row in CSV_ROWS:
        mid_arcsec = (row["start_arcsec"] + row["end_arcsec"]) // 2
        result = get_kp_sub_lord(deg(mid_arcsec))
        assert result["row_index"] == row["row_index"]
        assert result["star_lord"] == row["nakshatra_lord"]
        assert result["sub_lord"] == row["sub_lord"]
        assert result["sub_index"] == row["sub_index"]
        assert result["nakshatra_index"] == row["nakshatra_index"]
        assert result["nakshatra_name"] == row["nakshatra_name"]
        assert result["sub_start_longitude"] == pytest.approx(
            row["start_arcsec"] / 3600.0
        )
        assert result["sub_end_longitude"] == pytest.approx(
            row["end_arcsec"] / 3600.0
        )


def test_no_off_by_one_at_row_boundaries():
    # For every row: its start_arcsec belongs to it; its last arcsec
    # (end_arcsec - 1) belongs to it; its end_arcsec belongs to the NEXT row.
    for row in CSV_ROWS:
        start_result = get_kp_sub_lord(deg(row["start_arcsec"]))
        assert start_result["row_index"] == row["row_index"]

        last_inside = get_kp_sub_lord(deg(row["end_arcsec"] - 1))
        assert last_inside["row_index"] == row["row_index"]

        if row["end_arcsec"] < FULL_ZODIAC_ARCSEC:
            after = get_kp_sub_lord(deg(row["end_arcsec"]))
            assert after["row_index"] == row["row_index"] + 1
        else:
            # The final row ends at the full zodiac; that value wraps to 0.
            assert get_kp_sub_lord(deg(row["end_arcsec"]))["arcsec"] == 0
            assert get_kp_sub_lord(deg(row["end_arcsec"]))["row_index"] == 1


def test_required_keys_present():
    result = get_kp_sub_lord(123.456)
    for key in (
        "star_lord",
        "sub_lord",
        "sub_index",
        "sub_start_longitude",
        "sub_end_longitude",
        "degree_in_sub",
    ):
        assert key in result


def test_degree_in_sub_is_offset_from_sub_start():
    result = get_kp_sub_lord(5.0)
    assert result["degree_in_sub"] == pytest.approx(
        result["longitude"] - result["sub_start_longitude"]
    )
    assert 0.0 <= result["degree_in_sub"] < (
        result["sub_end_longitude"] - result["sub_start_longitude"]
    )
