import json
import hashlib

def generate_chart_fingerprint(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: str,
    ayanamsa: str = "krishnamurti",
    house_system: str = "placidus",
    node_type: str = "true_node",
    engine_version: str = "1.0.0"
) -> str:
    """
    Creates a SHA-256 fingerprint representing a unique birth and calculation configuration.
    """
    data = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "timezone": timezone,
        "ayanamsa": ayanamsa,
        "house_system": house_system,
        "node_type": node_type,
        "engine_version": engine_version
    }
    
    # Use sorted JSON keys for consistent hashing
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
