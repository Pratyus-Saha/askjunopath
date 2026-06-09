import httpx
from timezonefinder import TimezoneFinder
from datetime import datetime
from zoneinfo import ZoneInfo

class GeocodingService:
    _instance = None
    _tf = None
    _cache = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GeocodingService, cls).__new__(cls, *args, **kwargs)
            cls._instance._tf = TimezoneFinder()
            cls._instance._cache = {}
        return cls._instance

    async def geocode(self, city_name: str) -> dict:
        """
        Geocodes a city name using OpenStreetMap Nominatim API.
        Caches results in-memory. Resolves the timezone using timezonefinder.
        """
        city_key = city_name.strip().lower()
        if city_key in self._cache:
            return self._cache[city_key]

        url = "https://nominatim.openstreetmap.org/search"
        headers = {
            "User-Agent": "askjunopath/1.0"
        }
        params = {
            "q": city_name,
            "format": "json",
            "limit": 1
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        if not data:
            raise ValueError(f"Could not geocode city: {city_name}")

        location = data[0]
        lat = float(location["lat"])
        lon = float(location["lon"])
        
        # Detect timezone using timezonefinder
        timezone_str = self._tf.timezone_at(lng=lon, lat=lat)
        if not timezone_str:
            timezone_str = "UTC"  # Safe default fallback

        # Extract country from display_name
        display_name = location.get("display_name", city_name)
        parts = [p.strip() for p in display_name.split(",") if p.strip()]
        country = parts[-1] if parts else "Unknown"

        result = {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone_str,
            "display_name": display_name,
            "country": country
        }
        
        self._cache[city_key] = result
        return result

    def convert_local_to_utc(self, birth_date: str, birth_time: str, timezone_str: str) -> datetime:
        """
        Converts a local birth date and time in a specific timezone to UTC datetime.
        """
        local_dt_naive = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
        tz = ZoneInfo(timezone_str)
        local_dt = local_dt_naive.replace(tzinfo=tz)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        return utc_dt
