from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PlanetName = Literal[
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]
SignName = Literal[
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
]
DomainName = Literal["career", "finance", "relationship"]
ConfidenceTier = Literal["HIGH", "MEDIUM", "SPECULATIVE", "WEAK_SIGNAL"]
RagAlignmentStatus = Literal["aligned", "partial", "contradicted", "no_data"]

PLANET_ORDER: tuple[str, ...] = (
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
HOUSE_ORDER: tuple[int, ...] = tuple(range(1, 13))

Longitude = Annotated[float, Field(ge=0.0, lt=360.0)]
SignDegree = Annotated[float, Field(ge=0.0, lt=30.0)]
BirthLatitude = Annotated[float, Field(ge=-66.0, le=66.0)]
BirthLongitude = Annotated[float, Field(ge=-180.0, le=180.0)]
HouseNumber = Annotated[int, Field(ge=1, le=12)]
Pada = Annotated[int, Field(ge=1, le=4)]
NakshatraIndex = Annotated[int, Field(ge=1, le=27)]
Percent = Annotated[int, Field(ge=0, le=100)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BirthDataRequest(StrictModel):
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM format (24-hour)")
    birth_city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="City of birth",
    )

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError("birth_date must be in YYYY-MM-DD format")
        try:
            year, month, day = (int(part) for part in value.split("-"))
            date(year, month, day)
        except Exception as exc:
            raise ValueError("birth_date is not a valid calendar date") from exc
        return value

    @field_validator("birth_time")
    @classmethod
    def validate_birth_time(cls, value: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", value):
            raise ValueError("birth_time must be in HH:MM format")
        try:
            hour, minute = (int(part) for part in value.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except Exception as exc:
            raise ValueError("birth_time contains invalid hour or minute values") from exc
        return value


class ChartGenerateResponse(StrictModel):
    cache_status: str
    chart_id: str
    chart_fingerprint: str
    chart: dict


class BirthBlock(StrictModel):
    datetime_local: str = Field(..., min_length=1)
    datetime_utc: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1)
    lat: BirthLatitude
    lon: BirthLongitude
    place_label: str = Field(..., min_length=1)
    approximate_time: bool
    julian_day_ut: float = Field(..., gt=0.0)

    @field_validator("datetime_utc")
    @classmethod
    def utc_timestamp_must_use_z(cls, value: str) -> str:
        if not value.endswith("Z"):
            raise ValueError("datetime_utc must use a Z suffix")
        return value


class SettingsBlock(StrictModel):
    ayanamsa: Literal["KP_NEWCOMB"]
    ayanamsa_value_deg: float = Field(..., ge=20.0, le=30.0)
    node_type: Literal["TRUE"]
    house_system: Literal["PLACIDUS"]
    zodiac: Literal["SIDEREAL"]


class AscendantBlock(StrictModel):
    longitude: Longitude
    sign: SignName
    sign_degree: SignDegree


class ChartMetadata(StrictModel):
    birth_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    birth_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    birth_city: str = Field(..., min_length=2, max_length=100)
    latitude: BirthLatitude
    longitude: BirthLongitude
    timezone: str = Field(..., min_length=1)
    ayanamsa: float = Field(..., ge=20.0, le=30.0)
    engine_version: str = Field(..., min_length=1)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: str) -> str:
        return BirthDataRequest.validate_birth_date(value)

    @field_validator("birth_time")
    @classmethod
    def validate_birth_time(cls, value: str) -> str:
        return BirthDataRequest.validate_birth_time(value)


class NakshatraBlock(StrictModel):
    name: str = Field(..., min_length=1)
    index: NakshatraIndex
    lord: PlanetName
    degree_in_nakshatra: float = Field(..., ge=0.0, lt=13.333334)
    pada: Pada
    degree_in_pada: float = Field(..., ge=0.0, lt=3.333334)
    navamsa_sign: SignName


class KpBlock(StrictModel):
    star_lord: PlanetName
    sub_lord: PlanetName
    sub_sub_lord: PlanetName


class PlanetBlock(StrictModel):
    name: PlanetName
    longitude: Longitude
    sign: SignName
    sign_lord: PlanetName
    sign_degree: SignDegree
    house_occupied: HouseNumber | None = None
    retrograde: bool
    combust: bool
    speed_deg_per_day: float
    nakshatra: NakshatraBlock | None = None
    kp: KpBlock | None = None
    significator_of_houses: list[HouseNumber] = Field(default_factory=list)
    significator_levels: dict[str, Literal["A", "B", "C", "D"]] = Field(
        default_factory=dict
    )

    @field_validator("significator_of_houses")
    @classmethod
    def house_list_must_be_sorted_unique(cls, value: list[int]) -> list[int]:
        if value != sorted(set(value)):
            raise ValueError("significator_of_houses must be sorted and unique")
        return value

    @model_validator(mode="after")
    def significator_level_keys_must_match_houses(self) -> "PlanetBlock":
        houses = set(self.significator_of_houses)
        for key in self.significator_levels:
            if not key.isdigit():
                raise ValueError("significator_levels keys must be house numbers")
            house = int(key)
            if house < 1 or house > 12:
                raise ValueError("significator_levels keys must be 1..12")
            if house not in houses:
                raise ValueError(
                    "significator_levels keys must be a subset of significator_of_houses"
                )
        return self


class SignificatorLadder(StrictModel):
    A_in_star_of_occupants: list[PlanetName] = Field(default_factory=list)
    B_occupants: list[PlanetName] = Field(default_factory=list)
    C_in_star_of_owner: list[PlanetName] = Field(default_factory=list)
    D_owner: list[PlanetName] = Field(default_factory=list)


class HouseBlock(StrictModel):
    house: HouseNumber
    cusp_longitude: Longitude
    cusp_sign: SignName
    cusp_sign_lord: PlanetName
    cusp_nakshatra: str | None = None
    cusp_star_lord: PlanetName | None = None
    cusp_sub_lord: PlanetName | None = None
    cusp_sub_sub_lord: PlanetName | None = None
    occupants: list[PlanetName] = Field(default_factory=list)
    significators: SignificatorLadder | None = None


class BirthBalance(StrictModel):
    lord: PlanetName
    years_remaining: float = Field(..., ge=0.0, le=20.0)


class DashaPeriod(StrictModel):
    lord: PlanetName
    start: date
    end: date

    @model_validator(mode="after")
    def start_must_precede_end(self) -> "DashaPeriod":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class CurrentDasha(StrictModel):
    mahadasha: DashaPeriod
    antardasha: DashaPeriod
    pratyantardasha: DashaPeriod


class MdAdPeriod(StrictModel):
    md: PlanetName
    ad: PlanetName
    start: date
    end: date

    @model_validator(mode="after")
    def start_must_precede_end(self) -> "MdAdPeriod":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class PdPeriod(StrictModel):
    md: PlanetName
    ad: PlanetName
    pd: PlanetName
    start: date
    end: date

    @model_validator(mode="after")
    def start_must_precede_end(self) -> "PdPeriod":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class DashaBlock(StrictModel):
    system: Literal["VIMSHOTTARI"]
    birth_balance: BirthBalance
    current: CurrentDasha
    upcoming_md_ad: list[MdAdPeriod] = Field(default_factory=list, max_length=5)
    upcoming_pd: list[PdPeriod] = Field(default_factory=list, max_length=30)


class StrengthComponents(StrictModel):
    dignity: int
    house_placement: int
    dig_bala: int
    retrograde: int
    combustion: int
    aspects_net: int
    base: int


class StrengthBlock(StrictModel):
    planet: PlanetName
    v1_score: Percent
    components: StrengthComponents
    tier: Literal["STRONG", "MODERATE", "WEAK"]
    notes: list[str] = Field(default_factory=list)
    derived: bool = False


class D9Flags(StrictModel):
    vargottama: list[PlanetName] = Field(default_factory=list)
    debilitated_in_d9: list[PlanetName] = Field(default_factory=list)


class D10Flags(StrictModel):
    tenth_lord_well_placed: bool
    tenth_lord_in_dusthana: bool


class D9Block(StrictModel):
    placements: dict[PlanetName, SignName]
    flags: D9Flags

    @field_validator("placements")
    @classmethod
    def placements_must_cover_all_planets(
        cls, value: dict[str, str]
    ) -> dict[str, str]:
        if set(value) != set(PLANET_ORDER):
            raise ValueError("placements must include all 9 planets")
        return value


class D10Block(StrictModel):
    placements: dict[PlanetName, SignName]
    flags: D10Flags

    @field_validator("placements")
    @classmethod
    def placements_must_cover_all_planets(
        cls, value: dict[str, str]
    ) -> dict[str, str]:
        if set(value) != set(PLANET_ORDER):
            raise ValueError("placements must include all 9 planets")
        return value


class DivisionalBlock(StrictModel):
    d9: D9Block | None = None
    d10: D10Block | None = None


class TransitWindow(StrictModel):
    domain: DomainName
    start: date
    end: date
    triggers: list[str] = Field(..., min_length=1)
    window_score: Probability

    @model_validator(mode="after")
    def validate_window(self) -> "TransitWindow":
        span_days = (self.end - self.start).days
        if span_days <= 0:
            raise ValueError("start must be before end")
        if span_days < 7 or span_days > 30:
            raise ValueError("transit windows must span 7 to 30 days")
        return self


class TransitsBlock(StrictModel):
    computed_at: str | None = None
    windows: list[TransitWindow] = Field(default_factory=list)

    @model_validator(mode="after")
    def max_three_windows_per_domain(self) -> "TransitsBlock":
        counts = {domain: 0 for domain in ("career", "finance", "relationship")}
        for window in self.windows:
            counts[window.domain] += 1
            if counts[window.domain] > 3:
                raise ValueError("maximum 3 transit windows per domain")
        return self


class FeatureTransitWindow(StrictModel):
    start: date
    end: date
    triggers: list[str] = Field(..., min_length=1)
    window_score: Probability

    @model_validator(mode="after")
    def start_must_precede_end(self) -> "FeatureTransitWindow":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class RagAlignment(StrictModel):
    status: RagAlignmentStatus
    chunk_ids: list[str] = Field(default_factory=list)


class PredictionFeature(StrictModel):
    domain: DomainName
    primary_cusp_sub_lord: PlanetName
    cusp_sub_lord_signifies: list[HouseNumber] = Field(default_factory=list)
    event_promise: bool
    active_dasha_lords: list[PlanetName] = Field(default_factory=list)
    dasha_support: dict[PlanetName, list[HouseNumber]] = Field(default_factory=dict)
    supporting_significators: list[PlanetName] = Field(default_factory=list)
    blocking_significators: list[PlanetName] = Field(default_factory=list)
    blocking_houses_hit: list[HouseNumber] = Field(default_factory=list)
    relevant_strengths: dict[PlanetName, Percent] = Field(default_factory=dict)
    transit_windows: list[FeatureTransitWindow] = Field(default_factory=list)
    rag_alignment: RagAlignment
    raw_score: Percent
    confidence_tier: ConfidenceTier
    probability_pct: Percent


class PredictionFeaturesBlock(StrictModel):
    career: PredictionFeature | None = None
    finance: PredictionFeature | None = None
    relationship: PredictionFeature | None = None

    @model_validator(mode="after")
    def domains_must_match_slots(self) -> "PredictionFeaturesBlock":
        for expected_domain in ("career", "finance", "relationship"):
            feature = getattr(self, expected_domain)
            if feature is not None and feature.domain != expected_domain:
                raise ValueError("prediction feature domain must match its slot")
        return self


class ChartData(StrictModel):
    schema_version: Literal["1.1"]
    metadata: ChartMetadata | None = None
    birth: BirthBlock
    settings: SettingsBlock
    ascendant: AscendantBlock
    planets: list[PlanetBlock] = Field(..., min_length=9, max_length=9)
    houses: list[HouseBlock] = Field(..., min_length=12, max_length=12)
    dashas: DashaBlock | None = None
    strengths: list[StrengthBlock] = Field(default_factory=list)
    divisional: DivisionalBlock = Field(default_factory=DivisionalBlock)
    transits: TransitsBlock = Field(default_factory=TransitsBlock)
    prediction_features: PredictionFeaturesBlock = Field(
        default_factory=PredictionFeaturesBlock
    )

    @field_validator("planets")
    @classmethod
    def planets_must_be_fixed_order(
        cls, value: list[PlanetBlock]
    ) -> list[PlanetBlock]:
        if tuple(planet.name for planet in value) != PLANET_ORDER:
            raise ValueError("planets must be in fixed Sun..Ketu order")
        return value

    @field_validator("houses")
    @classmethod
    def houses_must_be_ordered(cls, value: list[HouseBlock]) -> list[HouseBlock]:
        if tuple(house.house for house in value) != HOUSE_ORDER:
            raise ValueError("houses must be ordered 1..12")
        return value

    @field_validator("strengths")
    @classmethod
    def strengths_must_be_empty_or_fixed_order(
        cls, value: list[StrengthBlock]
    ) -> list[StrengthBlock]:
        if not value:
            return value
        if len(value) != len(PLANET_ORDER):
            raise ValueError("strengths must include all 9 planets when populated")
        if tuple(strength.planet for strength in value) != PLANET_ORDER:
            raise ValueError("strengths must be in fixed Sun..Ketu order")
        return value
