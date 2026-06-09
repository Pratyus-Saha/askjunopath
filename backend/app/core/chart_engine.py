import swisseph as swe
from datetime import datetime

# Zodiac signs list (30 degrees each)
SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Nakshatras list (13°20' or 13.333333° each)
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Vimshottari lord cycle starting from Ashwini (Ketu)
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
]

def get_zodiac_sign(longitude: float) -> str:
    """Returns the Zodiac sign name for a given longitude."""
    idx = int((longitude % 360) // 30)
    return SIGNS[idx]

def get_nakshatra_details(longitude: float) -> tuple[str, str]:
    """Returns the Nakshatra name and its lord for a given longitude."""
    long_normalized = longitude % 360
    nak_degree = 360.0 / 27.0  # 13.333333 degrees
    idx = int(long_normalized // nak_degree)
    idx = min(idx, 26)  # Guard against rounding edge cases at 360.0
    return NAKSHATRAS[idx], NAKSHATRA_LORDS[idx % 9]

def generate_chart_data(utc_dt: datetime, latitude: float, longitude: float, birth_metadata: dict) -> dict:
    """
    Computes astronomical chart coordinates using Swiss Ephemeris.
    Sets Krishnamurti sidereal mode, calculates 9 planets + Ascendant, 
    and handles tropical/sidereal differences, nakshatras, and house calculation.
    """
    # Convert UTC datetime to Julian Day (UT1)
    # flag = 1 indicates UTC time
    jd_tuple = swe.utc_to_jd(
        utc_dt.year, 
        utc_dt.month, 
        utc_dt.day, 
        utc_dt.hour, 
        utc_dt.minute, 
        utc_dt.second, 
        1
    )
    jd_ut = jd_tuple[1]

    # Configure Sidereal Mode for Krishnamurti Ayanamsa
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0.0, 0.0)
    ayanamsa_value = swe.get_ayanamsa_ut(jd_ut)

    # Use Swiss Ephemeris flag and speed flag (to detect retrograde motion)
    flags_tropical = swe.FLG_SWIEPH | swe.FLG_SPEED

    # Calculate Placidus House cusps and Ascendant
    # 'B' stands for Placidus houses
    cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b'B', flags_tropical)
    tropical_asc = ascmc[0]
    sidereal_asc = (tropical_asc - ayanamsa_value) % 360

    asc_sign = get_zodiac_sign(sidereal_asc)
    asc_deg = sidereal_asc % 30
    asc_nak, asc_lord = get_nakshatra_details(sidereal_asc)

    ascendant_data = {
        "tropical_longitude": tropical_asc,
        "sidereal_longitude": sidereal_asc,
        "sign": asc_sign,
        "degree_in_sign": asc_deg,
        "nakshatra": asc_nak,
        "nakshatra_lord": asc_lord
    }

    # Planet configuration IDs
    planet_ids = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.TRUE_NODE  # North Node (True Node)
    }

    planets_data = {}

    for name, p_id in planet_ids.items():
        res, ret = swe.calc_ut(jd_ut, p_id, flags_tropical)
        tropical_long = res[0]
        speed_long = res[3]
        
        sidereal_long = (tropical_long - ayanamsa_value) % 360
        is_retro = speed_long < 0

        sign_name = get_zodiac_sign(sidereal_long)
        deg_in_sign = sidereal_long % 30
        nak_name, nak_lord = get_nakshatra_details(sidereal_long)

        planets_data[name] = {
            "tropical_longitude": tropical_long,
            "sidereal_longitude": sidereal_long,
            "sign": sign_name,
            "degree_in_sign": deg_in_sign,
            "nakshatra": nak_name,
            "nakshatra_lord": nak_lord,
            "is_retrograde": is_retro
        }

    # Ketu is calculated exactly 180 degrees away from Rahu (North Node)
    rahu_data = planets_data["Rahu"]
    ketu_tropical = (rahu_data["tropical_longitude"] + 180.0) % 360.0
    ketu_sidereal = (rahu_data["sidereal_longitude"] + 180.0) % 360.0

    ketu_sign = get_zodiac_sign(ketu_sidereal)
    ketu_deg = ketu_sidereal % 30
    ketu_nak, ketu_lord = get_nakshatra_details(ketu_sidereal)

    planets_data["Ketu"] = {
        "tropical_longitude": ketu_tropical,
        "sidereal_longitude": ketu_sidereal,
        "sign": ketu_sign,
        "degree_in_sign": ketu_deg,
        "nakshatra": ketu_nak,
        "nakshatra_lord": ketu_lord,
        "is_retrograde": rahu_data["is_retrograde"]  # Ketu moves in sync with Rahu
    }

    # Clean up (releases Swiss Ephemeris resources)
    swe.close()

    return {
        "metadata": {
            "birth_date": birth_metadata["birth_date"],
            "birth_time": birth_metadata["birth_time"],
            "birth_city": birth_metadata["birth_city"],
            "latitude": latitude,
            "longitude": longitude,
            "timezone": birth_metadata["timezone"],
            "ayanamsa": ayanamsa_value,
            "engine_version": birth_metadata.get("engine_version", "1.0.0")
        },
        "ascendant": ascendant_data,
        "planets": planets_data
    }
