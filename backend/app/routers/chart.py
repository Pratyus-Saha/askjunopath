from fastapi import APIRouter, Header, HTTPException, status
from app.schemas.models import BirthDataRequest, ChartGenerateResponse, ChartData
from app.utils.geocode import GeocodingService
from app.core.fingerprint import generate_chart_fingerprint
from app.core.db import get_chart_by_fingerprint, save_chart
from app.core.config import settings
from app.engines.ephemeris_engine import (
    EphemerisError,
    InvalidCoordinatesError,
    InvalidDatetimeError,
    InvalidTimezoneError,
    LatUnsupportedError,
    compute_ephemeris,
)
from app.engines.nakshatra_engine import nakshatra_block, nakshatra_name

router = APIRouter(prefix="/chart", tags=["chart"])


def _build_chart_payload(
    ephemeris: dict,
    place_label: str,
    request_data: BirthDataRequest,
    geo_lat: float,
    geo_lon: float,
    timezone_str: str,
) -> dict:
    """Assemble the stored/returned chart payload from trusted engine output.

    The canonical part is validated through the frozen chart.json v1.0
    contract (ChartData). One extra non-schema key, `metadata`, is kept
    alongside it: save_chart() reads chart_data["metadata"]["ayanamsa"] and
    ["engine_version"] for its table columns, and the Day 1 scaffold chart
    page reads metadata.latitude/longitude/ayanamsa/timezone. Strip
    `metadata` before re-validating a stored object against ChartData
    (extra="forbid").
    """
    birth = {
        **ephemeris["birth"],
        "place_label": place_label,
        # Birth-input toggle ships Day 4 (T4.4); false per docs/chart-schema.md.
        "approximate_time": False,
    }
    # Day 2 (T2.3): nakshatra fill per docs/nakshatra.md. Planets get the
    # full 7-key NakshatraBlock; cusps get the name STRING only — cusp KP
    # fields (cusp_star_lord/sub/sub_sub) are Day 4's, left null here.
    planets = [
        {**planet, "nakshatra": nakshatra_block(planet["longitude"])}
        for planet in ephemeris["planets"]
    ]
    houses = [
        {**house, "cusp_nakshatra": nakshatra_name(house["cusp_longitude"])}
        for house in ephemeris["houses"]
    ]
    chart_model = ChartData(
        schema_version="1.0",
        birth=birth,
        settings=ephemeris["settings"],
        ascendant=ephemeris["ascendant"],
        planets=planets,
        houses=houses,
    )
    payload = chart_model.model_dump(mode="json")
    payload["metadata"] = {
        "birth_date": request_data.birth_date,
        "birth_time": request_data.birth_time,
        "birth_city": request_data.birth_city,
        "latitude": geo_lat,
        "longitude": geo_lon,
        "timezone": timezone_str,
        "ayanamsa": ephemeris["settings"]["ayanamsa_value_deg"],
        "engine_version": settings.chart_engine_version,
    }
    return payload


@router.post("/generate", response_model=ChartGenerateResponse)
async def generate_chart(
    request_data: BirthDataRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id")
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
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Missing required X-User-Id header."
        )

    geocoder = GeocodingService()

    # 1. Geocode birth city using Nominatim
    try:
        geo_result = await geocoder.geocode(request_data.birth_city)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not geocode birth city '{request_data.birth_city}': {str(e)}"
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
    cached_record = get_chart_by_fingerprint(x_user_id, fingerprint)
    if cached_record:
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
            user_id=x_user_id,
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart generation calculation failed: {str(e)}"
        )
