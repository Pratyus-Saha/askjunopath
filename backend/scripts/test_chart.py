import sys
import os
from datetime import datetime

# Adjust Python path to allow app imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.chart_engine import generate_chart_data

def run_test():
    print("=" * 80)
    print("ASKJUNOPATH ASTRONOMICAL VALIDATION TEST")
    print("=" * 80)
    
    # New Delhi is Asia/Kolkata
    # Jan 15 1990, 14:30 IST -> 1990-01-15 09:00 UTC
    utc_dt = datetime(1990, 1, 15, 9, 0, 0)
    lat = 28.6139
    lon = 77.2090
    city = "New Delhi"
    
    metadata = {
        "birth_date": "1990-01-15",
        "birth_time": "14:30",
        "birth_city": city,
        "timezone": "Asia/Kolkata",
        "engine_version": "1.0.0"
    }
    
    # Compute
    chart = generate_chart_data(utc_dt, lat, lon, metadata)
    
    # Extract values
    ayanamsa = chart["metadata"]["ayanamsa"]
    asc = chart["ascendant"]
    planets = chart["planets"]
    
    print(f"Birth Details: {city} on Jan 15 1990, 14:30 IST (UTC: 1990-01-15 09:00)")
    print(f"Coordinates: Latitude: {lat}, Longitude: {lon}")
    print(f"Calculated Ayanamsa (Krishnamurti): {ayanamsa:.6f} degrees")
    print("-" * 80)
    
    print(f"Ascendant (Lagna) Details:")
    print(f"  Tropical Longitude: {asc['tropical_longitude']:.4f}")
    print(f"  Sidereal Longitude: {asc['sidereal_longitude']:.4f}")
    print(f"  Zodiac Sign:        {asc['sign']}")
    print(f"  Degree in Sign:     {asc['degree_in_sign']:.4f}")
    print(f"  Nakshatra:          {asc['nakshatra']}")
    print(f"  Nakshatra Lord:     {asc['nakshatra_lord']}")
    print("-" * 80)
    
    print(f"{'Planet':<8} | {'Tropical Long':<13} | {'Sidereal Long':<13} | {'Sign':<11} | {'Nakshatra':<15} | {'Lord':<8} | {'Retro':<5}")
    print("-" * 85)
    for name, data in planets.items():
        print(f"{name:<8} | {data['tropical_longitude']:13.4f} | {data['sidereal_longitude']:13.4f} | {data['sign']:<11} | {data['nakshatra']:<15} | {data['nakshatra_lord']:<8} | {str(data['is_retrograde']):<5}")
    
    print("=" * 80)
    print("VERIFYING ASTROLOGICAL RULES:")
    
    # 1. Ayanamsa Check (around 23.62 to 23.79 degrees)
    print(f" Rule 1 (Ayanamsa check): Calculated {ayanamsa:.4f}")
    assert 23.5 <= ayanamsa <= 23.85, f"Validation Failed: Ayanamsa {ayanamsa} is outside the expected range [23.5, 23.85]"
    
    # 2. Sun Sidereal Check (~270-275 degrees, Sagittarius/Capricorn transition)
    sun_sidereal = planets["Sun"]["sidereal_longitude"]
    print(f" Rule 2 (Sun Sidereal ~270-275): Calculated {sun_sidereal:.4f}")
    assert 270.0 <= sun_sidereal <= 276.0, f"Validation Failed: Sun sidereal longitude {sun_sidereal} is outside [270, 276]"
    
    # 3. Rahu & Ketu exactly 180 degrees apart
    rahu_sid = planets["Rahu"]["sidereal_longitude"]
    ketu_sid = planets["Ketu"]["sidereal_longitude"]
    node_diff = abs(rahu_sid - ketu_sid)
    node_diff = min(node_diff, 360.0 - node_diff)
    print(f" Rule 3 (Rahu & Ketu exact 180° offset): Difference is {node_diff:.6f} degrees")
    assert abs(node_diff - 180.0) < 1e-4, f"Validation Failed: Node difference is {node_diff}, not 180.0"
    
    print("\n[SUCCESS] All astronomical calculation assertions PASSED successfully!")
    print("=" * 80)

if __name__ == "__main__":
    run_test()
