"""Fixture-driven tests for docs/nakshatra.md boundary conventions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.engines.nakshatra_engine import (  # noqa: E402
    degree_in_nakshatra,
    degree_in_pada,
    nakshatra_block,
    nakshatra_index,
    nakshatra_lord,
    nakshatra_name,
    navamsa_sign,
    pada,
)

FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "nakshatra" / "boundaries_330.json"
)
FIXTURE_ROWS = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

EXPECTED_BLOCK_KEYS = {
    "name",
    "index",
    "lord",
    "degree_in_nakshatra",
    "pada",
    "degree_in_pada",
    "navamsa_sign",
}


def fixture_id(row: dict) -> str:
    return f"{row['normalized_arcsec']}:{row['input_longitude']}"


def assert_matches_fixture(longitude: float, row: dict) -> None:
    block = nakshatra_block(longitude)
    assert block["name"] == row["expected_name"]
    assert block["index"] == row["expected_index"]
    assert block["lord"] == row["expected_lord"]
    assert block["pada"] == row["expected_pada"]
    assert block["navamsa_sign"] == row["expected_navamsa_sign"]
    assert block["degree_in_nakshatra"] == pytest.approx(
        row["expected_degree_in_nakshatra"], abs=1e-6
    )
    assert block["degree_in_pada"] == pytest.approx(
        row["expected_degree_in_pada"], abs=1e-6
    )


def test_fixture_file_has_330_rows():
    assert len(FIXTURE_ROWS) == 330


@pytest.mark.parametrize("row", FIXTURE_ROWS, ids=fixture_id)
def test_all_fixture_rows_match_nakshatra_block(row):
    assert_matches_fixture(row["input_longitude"], row)


@pytest.mark.parametrize("row", FIXTURE_ROWS, ids=fixture_id)
def test_individual_helpers_match_fixture_rows(row):
    longitude = row["input_longitude"]
    assert nakshatra_name(longitude) == row["expected_name"]
    assert nakshatra_index(longitude) == row["expected_index"]
    assert nakshatra_lord(longitude) == row["expected_lord"]
    assert pada(longitude) == row["expected_pada"]
    assert navamsa_sign(longitude) == row["expected_navamsa_sign"]
    assert degree_in_nakshatra(longitude) == pytest.approx(
        row["expected_degree_in_nakshatra"], abs=1e-6
    )
    assert degree_in_pada(longitude) == pytest.approx(
        row["expected_degree_in_pada"], abs=1e-6
    )


@pytest.mark.parametrize("longitude", [359.9999, 359.99999, 360.0, -0.0001])
def test_rounding_regressions_classify_as_ashwini_pada_1(longitude):
    rows = [row for row in FIXTURE_ROWS if row["input_longitude"] == longitude]
    assert rows, f"fixture row missing for {longitude}"

    block = nakshatra_block(longitude)
    assert block["name"] == "Ashwini"
    assert block["index"] == 1
    assert block["lord"] == "Ketu"
    assert block["pada"] == 1
    assert block["navamsa_sign"] == "Aries"


def test_last_arcsecond_before_zero_classifies_as_revati_pada_4():
    longitude = 1_295_999 / 3600.0
    rows = [row for row in FIXTURE_ROWS if row["normalized_arcsec"] == 1_295_999]
    assert rows

    block = nakshatra_block(longitude)
    assert block["name"] == "Revati"
    assert block["index"] == 27
    assert block["lord"] == "Mercury"
    assert block["pada"] == 4
    assert block["navamsa_sign"] == "Pisces"


def test_nakshatra_block_returns_exactly_the_schema_keys():
    assert set(nakshatra_block(0.0).keys()) == EXPECTED_BLOCK_KEYS


def test_navamsa_spot_checks_from_docs():
    assert navamsa_sign(0.0) == "Aries"
    assert navamsa_sign(30.0) == "Capricorn"
    assert navamsa_sign(60.0) == "Libra"
