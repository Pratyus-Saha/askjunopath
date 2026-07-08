import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.schemas.models import BirthDataRequest, ChartGenerateResponse, ChartData
from app.core.auth import get_current_user
from app.utils.geocode import GeocodingService
from app.core.fingerprint import generate_chart_fingerprint
from app.core.db import get_chart_by_fingerprint, save_chart
from app.core.config import settings
from app.engines.dasha_engine import compute_dasha_from_chart
from app.engines.ephemeris_engine import (
    EphemerisError,
    InvalidCoordinatesError,
    InvalidDatetimeError,
    InvalidTimezoneError,
    LatUnsupportedError,
    compute_ephemeris,
)
from app.engines.kp_engine import get_kp_sub_lord
from app.engines.nakshatra_engine import nakshatra_block, nakshatra_name
from app.engines.house_engine import occupants as house_occupants

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chart", tags=["chart"])


def _public_kp_block(longitude: float) -> dict[str, str]:
    lookup = get_kp_sub_lord(longitude)
    return {
        "star_lord": lookup["star_lord"],
        "sub_lord": lookup["sub_lord"],
    }


def _cached_chart_is_current(chart_json: object) -> bool:
    if not isinstance(chart_json, dict):
        return False
    try:
        ChartData.model_validate(chart_json)
    except Exception:
        return False
    return chart_json.get("schema_version") == "1.2"


def _build_chart_payload(
    ephemeris: dict,
    place_label: str,
    request_data: BirthDataRequest,
    geo_lat: float,
    geo_lon: float,
    timezone_str: str,
) -> dict:
    """Assemble the stored/returned chart payload from trusted engine output.

    The canonical payload is validated through chart.json v1.2 (ChartData).
    Its optional metadata block carries response trust signals used by
    save_chart() and the scaffold chart page while remaining narrow and
    extra-forbidden.
    """
    birth = {
        **ephemeris["birth"],
        "place_label": place_label,
        # Birth-input toggle ships Day 4 (T4.4); false per docs/chart-schema.md.
        "approximate_time": False,
    }
    # Nakshatra fill follows docs/nakshatra.md. KP fill follows D022: expose
    # only star_lord/sub_lord, even though the internal lookup returns more.
    # House occupation follows docs/houses.md JHora bhava spans (D024);
    # significators stay reserved and unpopulated per D023.
    cusps = [house["cusp_longitude"] for house in ephemeris["houses"]]
    occupants_by_house = house_occupants(ephemeris["planets"], cusps)
    house_by_planet = {
        planet_name: house
        for house, planet_names in occupants_by_house.items()
        for planet_name in planet_names
    }
    planets = [
        {
            **planet,
            "house_occupied": house_by_planet[planet["name"]],
            "nakshatra": nakshatra_block(planet["longitude"]),
            "kp": _public_kp_block(planet["longitude"]),
        }
        for planet in ephemeris["planets"]
    ]
    houses = [
        {
            **house,
            "cusp_nakshatra": nakshatra_name(house["cusp_longitude"]),
            "kp": _public_kp_block(house["cusp_longitude"]),
            "occupants": occupants_by_house[house["house"]],
        }
        for house in ephemeris["houses"]
    ]
    metadata = {
        "birth_date": request_data.birth_date,
        "birth_time": request_data.birth_time,
        "birth_city": request_data.birth_city,
        "latitude": geo_lat,
        "longitude": geo_lon,
        "timezone": timezone_str,
        "ayanamsa": ephemeris["settings"]["ayanamsa_value_deg"],
        "engine_version": settings.chart_engine_version,
    }
    chart_model = ChartData(
        schema_version="1.2",
        metadata=metadata,
        birth=birth,
        settings=ephemeris["settings"],
        ascendant=ephemeris["ascendant"],
        planets=planets,
        houses=houses,
    )
    return chart_model.model_dump(mode="json")


@router.post("/generate", response_model=ChartGenerateResponse)
async def generate_chart(
    request_data: BirthDataRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Generate an astrological chart with fingerprint caching.

    Chart math comes exclusively from the trusted engines under
    app.engines: ephemeris_engine (JHora-validated: sidereal KP-Newcomb,
    TRUE_NODE, FLG_TRUEPOS, Placidus cusps) plus nakshatra_engine
    (boundaries_330-validated) for planets[].nakshatra and
    houses[].cusp_nakshatra. The deprecated app.core.chart_engine is no
    longer called on any path.
    """
    geocoder = GeocodingService()

    # 1. Geocode birth city using Nominatim
    try:
        geo_result = await geocoder.geocode(request_data.birth_city)
    except Exception:
        # Full detail stays server-side; clients get no internal error text
        # (audit finding #14). The echoed city name is the caller's own input.
        logger.exception(
            "Geocoding failed for birth city %r", request_data.birth_city
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not geocode birth city '{request_data.birth_city}'.",
        )

    lat = geo_result["latitude"]
    lon = geo_result["longitude"]
    timezone_str = geo_result["timezone"]

    # 2. Compute the chart's SHA-256 fingerprint
    fingerprint = generate_chart_fingerprint(
        birth_date=request_data.birth_date,
        birth_time=request_data.birth_time,
        latitude=lat,
        longitude=lon,
        timezone=timezone_str,
        ayanamsa="krishnamurti",
        house_system="placidus",
        node_type="true_node",
        engine_version=settings.chart_engine_version
    )

    # 3. Lookup cache in Supabase user_charts table
    cached_record = get_chart_by_fingerprint(user_id, fingerprint)
    if cached_record and _cached_chart_is_current(cached_record.get("chart_json")):
        return ChartGenerateResponse(
            cache_status="HIT",
            chart_id=str(cached_record.get("id")),
            chart_fingerprint=fingerprint,
            chart=cached_record.get("chart_json", {})
        )

    # 4. MISS: single trusted computation. The engine performs the one
    # local->UTC conversion internally (zoneinfo, at the engine boundary);
    # the route hands it the naive local time plus the IANA zone and never
    # converts the timezone itself.
    datetime_local = f"{request_data.birth_date}T{request_data.birth_time}:00"
    try:
        ephemeris = compute_ephemeris(
            datetime_local=datetime_local,
            timezone=timezone_str,
            lat=lat,
            lon=lon,
        )
    except LatUnsupportedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.code, "message": e.message},
        )
    except (InvalidTimezoneError, InvalidCoordinatesError, InvalidDatetimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": e.code, "message": e.message},
        )
    except EphemerisError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message},
        )

    try:
        chart_data = _build_chart_payload(
            ephemeris=ephemeris,
            place_label=geo_result.get("display_name", request_data.birth_city),
            request_data=request_data,
            geo_lat=lat,
            geo_lon=lon,
            timezone_str=timezone_str,
        )

        # 5. Save output to Supabase cache
        saved_record = save_chart(
            user_id=user_id,
            chart_fingerprint=fingerprint,
            birth_data={
                "birth_date": request_data.birth_date,
                "birth_time": request_data.birth_time,
                "birth_city": request_data.birth_city,
                "birth_country": geo_result.get("country", "Unknown"),
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone_str
            },
            chart_data=chart_data
        )

        return ChartGenerateResponse(
            cache_status="MISS",
            chart_id=str(saved_record["id"]),
            chart_fingerprint=fingerprint,
            chart=chart_data
        )

    except HTTPException:
        raise
    except Exception:
        # Full traceback stays server-side; clients get a generic message
        # (audit finding #14).
        logger.exception("Chart generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chart generation calculation failed.",
        )


class DashaRequest(BaseModel):
    chart: dict[str, Any]


def _serialize_timeline(timeline):
    """Convert a DashaTimeline dataclass to a JSON-safe dict."""
    raw = asdict(timeline)
    def _convert(obj):
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_convert(item) for item in obj]
        from datetime import datetime as _dt
        if isinstance(obj, _dt):
            return obj.isoformat()
        return obj
    return _convert(raw)


@router.post("/dasha")
async def compute_dasha_endpoint(
    body: DashaRequest,
    user_id: str = Depends(get_current_user),
):
    try:
        ChartData.model_validate(body.chart)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "INVALID_CHART"},
        )

    timeline = compute_dasha_from_chart(body.chart)
    return _serialize_timeline(timeline)
