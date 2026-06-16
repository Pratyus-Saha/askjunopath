"""Structural tests for the generated KP 249 sub-lord table."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.gen_kp_table import (  # noqa: E402
    CSV_COLUMNS,
    FULL_ZODIAC_ARCSEC,
    NAKSHATRA_ARCSEC,
    OUTPUT_PATH,
    SIGN_ARCSEC,
    SUB_ARCSEC_PER_YEAR,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
    build_rows,
    csv_text,
)


INT_COLUMNS = {
    "row_index",
    "nakshatra_index",
    "sub_index",
    "start_arcsec",
    "end_arcsec",
    "length_arcsec",
}


def load_rows() -> list[dict[str, int | str]]:
    with OUTPUT_PATH.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        assert tuple(reader.fieldnames or ()) == CSV_COLUMNS
        rows: list[dict[str, int | str]] = []
        for row in reader:
            rows.append(
                {
                    key: int(value) if key in INT_COLUMNS else value
                    for key, value in row.items()
                }
            )
        return rows


def test_committed_csv_matches_deterministic_generator():
    assert OUTPUT_PATH.read_text(encoding="utf-8") == csv_text()
    assert build_rows() == load_rows()


def test_csv_has_expected_columns_and_249_rows():
    rows = load_rows()
    assert len(rows) == 249
    assert [row["row_index"] for row in rows] == list(range(1, 250))
    assert all(set(row) == set(CSV_COLUMNS) for row in rows)


def test_intervals_cover_the_full_zodiac_without_gaps_or_overlaps():
    rows = load_rows()
    assert rows[0]["start_arcsec"] == 0
    assert rows[-1]["end_arcsec"] == FULL_ZODIAC_ARCSEC
    assert sum(int(row["length_arcsec"]) for row in rows) == FULL_ZODIAC_ARCSEC

    previous_end = 0
    for row in rows:
        start_arcsec = int(row["start_arcsec"])
        end_arcsec = int(row["end_arcsec"])
        length_arcsec = int(row["length_arcsec"])

        assert start_arcsec == previous_end
        assert end_arcsec > start_arcsec
        assert length_arcsec == end_arcsec - start_arcsec
        previous_end = end_arcsec


def test_each_nakshatra_totals_exactly_48000_arcsec():
    totals_by_nakshatra: dict[int, int] = defaultdict(int)
    for row in load_rows():
        totals_by_nakshatra[int(row["nakshatra_index"])] += int(
            row["length_arcsec"]
        )

    assert len(totals_by_nakshatra) == 27
    assert set(totals_by_nakshatra) == set(range(1, 28))
    assert set(totals_by_nakshatra.values()) == {NAKSHATRA_ARCSEC}


def test_first_sub_lord_of_each_nakshatra_equals_nakshatra_lord():
    first_rows_by_nakshatra: dict[int, dict[str, int | str]] = {}
    for row in load_rows():
        first_rows_by_nakshatra.setdefault(int(row["nakshatra_index"]), row)

    assert len(first_rows_by_nakshatra) == 27
    for row in first_rows_by_nakshatra.values():
        assert row["sub_index"] == 1
        assert row["sub_lord"] == row["nakshatra_lord"]


def test_sub_lord_order_and_lengths_follow_vimshottari_cycle():
    rows_by_nakshatra: dict[int, list[dict[str, int | str]]] = defaultdict(list)
    for row in load_rows():
        rows_by_nakshatra[int(row["nakshatra_index"])].append(row)

    for rows in rows_by_nakshatra.values():
        nakshatra_lord = str(rows[0]["nakshatra_lord"])
        start_index = VIMSHOTTARI_SEQUENCE.index(nakshatra_lord)
        expected_lords = [
            VIMSHOTTARI_SEQUENCE[(start_index + offset) % len(VIMSHOTTARI_SEQUENCE)]
            for offset in range(len(VIMSHOTTARI_SEQUENCE))
        ]

        lengths_by_sub_index: dict[int, int] = defaultdict(int)
        lords_by_sub_index: dict[int, str] = {}
        for row in rows:
            sub_index = int(row["sub_index"])
            lengths_by_sub_index[sub_index] += int(row["length_arcsec"])
            lords_by_sub_index.setdefault(sub_index, str(row["sub_lord"]))
            assert lords_by_sub_index[sub_index] == row["sub_lord"]

        assert [lords_by_sub_index[index] for index in range(1, 10)] == expected_lords
        assert set(lengths_by_sub_index) == set(range(1, 10))

        for sub_index, sub_lord in enumerate(expected_lords, start=1):
            assert lengths_by_sub_index[sub_index] == (
                VIMSHOTTARI_YEARS[sub_lord] * SUB_ARCSEC_PER_YEAR
            )


def test_249_rows_are_produced_by_six_sign_boundary_splits():
    rows = load_rows()
    split_boundaries: list[int] = []

    for previous, current in zip(rows, rows[1:]):
        same_sub_lord_span = (
            previous["nakshatra_index"] == current["nakshatra_index"]
            and previous["sub_index"] == current["sub_index"]
            and previous["sub_lord"] == current["sub_lord"]
        )
        if same_sub_lord_span:
            boundary = int(previous["end_arcsec"])
            split_boundaries.append(boundary)
            assert boundary == current["start_arcsec"]
            assert boundary % SIGN_ARCSEC == 0

    assert len(split_boundaries) == 6
    assert len(rows) - len(split_boundaries) == 27 * 9
