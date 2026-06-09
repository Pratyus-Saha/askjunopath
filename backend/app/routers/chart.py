from fastapi import APIRouter, Header, HTTPException, status
from app.schemas.models import BirthDataRequest, ChartGenerateResponse
from app.utils.geocode import GeocodingService
from app.core.fingerprint import generate_chart_fingerprint
from app.core.chart_engine import generate_chart_data
from app.core.db import get_chart_by_fingerprint, save_chart
from app.core.config import settings
import uuid

router = APIRouter(prefix="/chart", tags=["chart"])

@router.post("/generate", response_model=ChartGenerateResponse)
async def generate_chart(
    request_data: BirthDataRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id")
):
    """
    Day 1 MVP endpoint to generate an astrological chart with fingerprint caching.
    Authenticates via X-User-Id header.
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
        
    # 4. MISS: Run calculations using Swiss Ephemeris
    try:
        # Resolve UTC timestamp
        utc_dt = geocoder.convert_local_to_utc(
            birth_date=request_data.birth_date,
            birth_time=request_data.birth_time,
            timezone_str=timezone_str
        )
        
        # Prepare calculation request metadata
        birth_metadata = {
            "birth_date": request_data.birth_date,
            "birth_time": request_data.birth_time,
            "birth_city": request_data.birth_city,
            "timezone": timezone_str,
            "engine_version": settings.chart_engine_version
        }
        
        # Calculate
        chart_data = generate_chart_data(
            utc_dt=utc_dt,
            latitude=lat,
            longitude=lon,
            birth_metadata=birth_metadata
        )
        
        # Save output to Supabase cache
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
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart generation calculation failed: {str(e)}"
        )
