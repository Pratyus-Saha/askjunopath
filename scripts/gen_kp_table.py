"""Generate the deterministic KP 249 sub-lord table.

The base KP table has 27 nakshatras x 9 Vimshottari sub-lords = 243
intervals. KP reference tables commonly restart rows at sign boundaries, so
any sub-lord interval that crosses a 30-degree sign boundary is split into two
CSV rows with the same sub_index and sub_lord. Six intervals cross sign
boundaries, producing 249 rows without changing the underlying sub-lord spans.
"""

from __future__ import annotations

import argparse
import csv
import sys
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.engines.nakshatra_engine import (  # noqa: E402
    FULL_ZODIAC_ARCSEC,
    NAKSHATRA_ARCSEC,
    NAKSHATRAS,
)

OUTPUT_PATH = REPO_ROOT / "data" / "kp_249.csv"
SIGN_ARCSEC = FULL_ZODIAC_ARCSEC // 12
VIMSHOTTARI_TOTAL_YEARS = 120
SUB_ARCSEC_PER_YEAR = NAKSHATRA_ARCSEC // VIMSHOTTARI_TOTAL_YEARS

VIMSHOTTARI_SEQUENCE = tuple(lord for _, lord in NAKSHATRAS[:9])
VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

CSV_COLUMNS = (
    "row_index",
    "nakshatra_index",
    "nakshatra_name",
    "nakshatra_lord",
    "sub_index",
    "sub_lord",
    "start_arcsec",
    "end_arcsec",
    "length_arcsec",
    "start_deg",
    "end_deg",
)


def format_degree(arcsec: int) -> str:
    return f"{arcsec / 3600.0:.6f}"


def sub_lords_for(nakshatra_lord: str) -> list[str]:
    start_index = VIMSHOTTARI_SEQUENCE.index(nakshatra_lord)
    return [
        VIMSHOTTARI_SEQUENCE[(start_index + offset) % len(VIMSHOTTARI_SEQUENCE)]
        for offset in range(len(VIMSHOTTARI_SEQUENCE))
    ]


def sign_boundaries_inside(start_arcsec: int, end_arcsec: int) -> list[int]:
    return [
        boundary
        for boundary in range(SIGN_ARCSEC, FULL_ZODIAC_ARCSEC, SIGN_ARCSEC)
        if start_arcsec < boundary < end_arcsec
    ]


def build_rows() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []

    for nakshatra_zero_based, (nakshatra_name, nakshatra_lord) in enumerate(
        NAKSHATRAS
    ):
        nakshatra_start = nakshatra_zero_based * NAKSHATRA_ARCSEC
        sub_start = nakshatra_start

        for sub_index, sub_lord in enumerate(
            sub_lords_for(nakshatra_lord), start=1
        ):
            sub_length = VIMSHOTTARI_YEARS[sub_lord] * SUB_ARCSEC_PER_YEAR
            sub_end = sub_start + sub_length
            split_points = [
                sub_start,
                *sign_boundaries_inside(sub_start, sub_end),
                sub_end,
            ]

            for start_arcsec, end_arcsec in zip(split_points, split_points[1:]):
                rows.append(
                    {
                        "nakshatra_index": nakshatra_zero_based + 1,
                        "nakshatra_name": nakshatra_name,
                        "nakshatra_lord": nakshatra_lord,
                        "sub_index": sub_index,
                        "sub_lord": sub_lord,
                        "start_arcsec": start_arcsec,
                        "end_arcsec": end_arcsec,
                        "length_arcsec": end_arcsec - start_arcsec,
                        "start_deg": format_degree(start_arcsec),
                        "end_deg": format_degree(end_arcsec),
                    }
                )

            sub_start = sub_end

        expected_nakshatra_end = nakshatra_start + NAKSHATRA_ARCSEC
        if sub_start != expected_nakshatra_end:
            raise ValueError(
                f"{nakshatra_name} ends at {sub_start}, "
                f"expected {expected_nakshatra_end}"
            )

    for row_index, row in enumerate(rows, start=1):
        row["row_index"] = row_index

    validate_rows(rows)
    return rows


def validate_rows(rows: list[dict[str, int | str]]) -> None:
    if len(rows) != 249:
        raise ValueError(f"expected 249 rows, got {len(rows)}")
    if rows[0]["start_arcsec"] != 0:
        raise ValueError("first KP row must start at 0 arcsec")
    if rows[-1]["end_arcsec"] != FULL_ZODIAC_ARCSEC:
        raise ValueError("last KP row must end at the full zodiac")

    previous_end = 0
    totals_by_nakshatra: dict[int, int] = {}

    for row in rows:
        start_arcsec = int(row["start_arcsec"])
        end_arcsec = int(row["end_arcsec"])
        length_arcsec = int(row["length_arcsec"])
        nakshatra_index = int(row["nakshatra_index"])

        if start_arcsec != previous_end:
            raise ValueError(
                f"gap or overlap before row {row['row_index']}: "
                f"expected {previous_end}, got {start_arcsec}"
            )
        if end_arcsec <= start_arcsec:
            raise ValueError(f"row {row['row_index']} has non-positive length")
        if length_arcsec != end_arcsec - start_arcsec:
            raise ValueError(f"row {row['row_index']} length is inconsistent")

        totals_by_nakshatra[nakshatra_index] = (
            totals_by_nakshatra.get(nakshatra_index, 0) + length_arcsec
        )
        previous_end = end_arcsec

    if previous_end != FULL_ZODIAC_ARCSEC:
        raise ValueError("KP rows do not cover the full zodiac")
    if len(totals_by_nakshatra) != 27:
        raise ValueError("KP rows must cover exactly 27 nakshatras")

    for nakshatra_index, total in sorted(totals_by_nakshatra.items()):
        if total != NAKSHATRA_ARCSEC:
            raise ValueError(
                f"nakshatra {nakshatra_index} totals {total}, "
                f"expected {NAKSHATRA_ARCSEC}"
            )


def csv_text(rows: list[dict[str, int | str]] | None = None) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows if rows is not None else build_rows())
    return output.getvalue()


def write_csv(path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(csv_text(), encoding="utf-8", newline="\n")


def check_csv(path: Path = OUTPUT_PATH) -> bool:
    return path.read_text(encoding="utf-8") == csv_text()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the output path already matches generated content",
    )
    args = parser.parse_args()

    if args.check:
        if check_csv(args.output):
            return 0
        print(f"{args.output} does not match generated KP table", file=sys.stderr)
        return 1

    write_csv(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
