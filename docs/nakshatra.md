# Nakshatra Engine Convention

**Status: FROZEN for Day 2 (June 12, 2026). Changes require founder approval and a version note here.**

## Purpose

This document is the source of truth for the nakshatra and pada implementation.

All agents must read this before touching nakshatra, pada, navamsa, KP star-lord, sub-lord, dasha, or chart assembly logic. If this document conflicts with existing code, this document wins. If it conflicts with `schemas/chart.json`, the schema wins and this document gets corrected, per AGENTS.md Rule 2 and Rule 3.

## Canonical Input

* All longitude inputs are sidereal absolute zodiac longitude in decimal degrees.
* Zodiac starts at 0° Aries sidereal using KP/Krishnamurti ayanamsa.
* Normalize any longitude with `L % 360` before calculation. Python's `%` returns a non-negative result for negative inputs, so `-10 % 360 == 350` is the intended behavior.
* Valid normalized range is `0 <= L < 360`.
* Never feed this engine tropical longitude. Tropical input produces plausible garbage that only JHora comparison catches.

## Segment Sizes

* Full zodiac = 360° = 1,296,000 arc-seconds.
* 27 nakshatras. Each spans 13°20' = 48,000 arc-seconds.
* 4 padas per nakshatra. Each spans 3°20' = 12,000 arc-seconds.
* 108 padas total across the zodiac.

## Boundary Rule

* Lower bound inclusive. Upper bound exclusive.
* An exact boundary belongs to the next segment.
* Exactly 0°00'00" is Ashwini pada 1.
* Exactly 13°20'00" is Bharani pada 1, not Ashwini pada 4.
* Exactly 26°40'00" is Krittika pada 1, not Bharani pada 4.
* 359°59'59" is Revati pada 4.

Reference software (Jagannatha Hora) follows the same convention.

## Math Rules

* All boundary math uses integer arc-seconds internally.
* Convert input once at the engine entry:

  ```txt
  arcsec = round((L % 360) * 3600) % 1296000
  ```

  The final modulo catches longitudes that round up to exactly 1,296,000, for example `L = 359.99999`, which would otherwise fall outside the valid `0` to `1,295,999` range. Every classification (index, pada, lord, navamsa) derives from this integer. Fixtures are defined at exact integer arc-second values or explicit rounding edge cases, so the conversion is lossless for every test case.
* Floats are allowed only at the output layer.
* `degree_in_nakshatra` and `degree_in_pada` are output as decimal degrees, computed from the integer arc-second value.
* Never compare raw floats for boundary equality.
* In tests: degree outputs compare with tolerance 1e-6. Index, pada, lord, name, and navamsa sign must match exactly, no tolerance.

## Index Convention

Internal implementation may use 0-based indexes. API output is 1-based.

API output follows `schemas/chart.json` exactly:

* Ashwini = 1
* Bharani = 2
* Krittika = 3
* ...
* Revati = 27

If internal code and schema disagree, the schema wins.

## Required Planet Nakshatra Output Shape

The frozen schema defines `NakshatraBlock` with `additionalProperties: false`.

Every non-null `planets[].nakshatra` block must match this exact shape:

```json
{
  "name": "Ashwini",
  "index": 1,
  "lord": "Ketu",
  "degree_in_nakshatra": 0.0,
  "pada": 1,
  "degree_in_pada": 0.0,
  "navamsa_sign": "Aries"
}
```

Required keys, all seven, nothing else:

```txt
name
index
lord
degree_in_nakshatra
pada
degree_in_pada
navamsa_sign
```

Do not invent keys. Do not rename keys. Do not add optional fields. Do not change `schemas/chart.json` during Day 2.

## Required House Cusp Nakshatra Output Shape

The frozen schema defines:

```txt
houses[].cusp_nakshatra = string or null
```

So `houses[].cusp_nakshatra` receives only the nakshatra name string.

Correct:

```json
"cusp_nakshatra": "Pushya"
```

Incorrect:

```json
"cusp_nakshatra": { "name": "Pushya", "index": 8, "lord": "Saturn", "pada": 2 }
```

House cusp KP data lives in separate schema fields, filled on Day 4, not today:

```txt
cusp_star_lord
cusp_sub_lord
cusp_sub_sub_lord
```

Never put a `NakshatraBlock` inside `cusp_nakshatra`.

## Nakshatra Order and Lords

The lord sequence is the Vimshottari cycle (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury) repeated three times.

| API Index | Nakshatra         | Lord    |
| --------: | ----------------- | ------- |
|         1 | Ashwini           | Ketu    |
|         2 | Bharani           | Venus   |
|         3 | Krittika          | Sun     |
|         4 | Rohini            | Moon    |
|         5 | Mrigashira        | Mars    |
|         6 | Ardra             | Rahu    |
|         7 | Punarvasu         | Jupiter |
|         8 | Pushya            | Saturn  |
|         9 | Ashlesha          | Mercury |
|        10 | Magha             | Ketu    |
|        11 | Purva Phalguni    | Venus   |
|        12 | Uttara Phalguni   | Sun     |
|        13 | Hasta             | Moon    |
|        14 | Chitra            | Mars    |
|        15 | Swati             | Rahu    |
|        16 | Vishakha          | Jupiter |
|        17 | Anuradha          | Saturn  |
|        18 | Jyeshtha          | Mercury |
|        19 | Mula              | Ketu    |
|        20 | Purva Ashadha     | Venus   |
|        21 | Uttara Ashadha    | Sun     |
|        22 | Shravana          | Moon    |
|        23 | Dhanishta         | Mars    |
|        24 | Shatabhisha       | Rahu    |
|        25 | Purva Bhadrapada  | Jupiter |
|        26 | Uttara Bhadrapada | Saturn  |
|        27 | Revati            | Mercury |

This table also drives the KP 249 sub-lord generator and the Vimshottari dasha engine. It is defined here once. No other file re-declares it.

## Navamsa Sign Rule

Navamsa is calculated from normalized sidereal absolute longitude.

```txt
navamsa_sign_index = floor(L * 9 / 30) % 12
```

In integer arc-seconds: `navamsa_sign_index = (arcsec // 12000) % 12`. One pada equals one navamsa, so this is the same division that yields the pada boundaries.

Sign index mapping:

```txt
0 = Aries      4 = Leo          8 = Sagittarius
1 = Taurus     5 = Virgo        9 = Capricorn
2 = Gemini     6 = Libra       10 = Aquarius
3 = Cancer     7 = Scorpio     11 = Pisces
```

This single formula reproduces the classical movable/fixed/dual start rule. Spot checks, all three must hold:

```txt
Aries 0°00'00"  -> Aries
Taurus 0°00'00" -> Capricorn
Gemini 0°00'00" -> Libra
```

Output is the sign name string, from Aries.

## Implementation Requirements

The engine file is:

```txt
backend/app/engines/nakshatra_engine.py
```

Do not create `backend/engines/`. The `app/` segment is canonical per docs/PROJECT_CONTEXT.md.

Pure functions only. No I/O, no database, no API calls, no imports from the deprecated `backend/app/core/chart_engine.py`.

Required functions:

```txt
nakshatra_index(L)
nakshatra_name(L)
nakshatra_lord(L)
degree_in_nakshatra(L)
pada(L)
degree_in_pada(L)
navamsa_sign(L)
nakshatra_block(L)
```

`nakshatra_block(L)` returns the exact `NakshatraBlock` shape defined above.

Integration code fills house cusps with `nakshatra_name(cusp_longitude)` and assigns only the string to `houses[].cusp_nakshatra`.

## Fixture Rule

The founder-supplied fixture file is the judge:

```txt
tests/fixtures/nakshatra/boundaries_330.json
```

The engine conforms to the fixture file. The fixture file is never edited to make broken code pass (AGENTS.md Rules 7 and 8).

Coverage:

```txt
108 pada boundaries × 3 cases each:
  - 1 arc-second below the boundary
  - exactly on the boundary
  - 1 arc-second above the boundary
= 324 cases

plus:
  - 0°00'00" (0 arc-seconds)
  - 359°59'59" (1,295,999 arc-seconds)

plus four rounding regression rows:
  - 359.9999
  - 359.99999
  - 360.0
  - -0.0001

= 330 fixtures total
```

Each fixture row asserts: arc-second value, nakshatra index, name, lord, pada, and navamsa sign.

Fixture expectations are computed by the founder's generation script from the table and rules in this document, independently of the engine under test. Ten rows are additionally hand-verified against Jagannatha Hora before the engine is judged by them.

## Day 2 Hard Rule

Do not implement KP, dasha, predictions, or significators until all 330 nakshatra and pada fixtures are green. The KP 249 table, the Vimshottari dasha engine, and every prediction downstream inherit any boundary error this document fails to prevent.
