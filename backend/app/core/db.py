from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client defensively to prevent crash on invalid developer-provided credentials
supabase: Client | None = None
try:
    if settings.supabase_url and settings.supabase_service_role_key:
        supabase = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_role_key
        )
except Exception as e:
    print(f"Database Warning: Failed to initialize Supabase client on startup. Error: {e}")
    supabase = None

def get_chart_by_fingerprint(user_id: str, chart_fingerprint: str) -> dict | None:
    """
    Checks the user_charts table in Supabase for a cached chart with matching user_id and fingerprint.
    Returns the row dictionary if found, or None.
    """
    if not supabase:
        print("Database lookup skipped: Supabase client is not initialized.")
        return None
    try:
        response = supabase.table("user_charts") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("chart_fingerprint", chart_fingerprint) \
            .limit(1) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Database warning: Failed to lookup chart by fingerprint. Error: {e}")
        return None

def save_chart(user_id: str, chart_fingerprint: str, birth_data: dict, chart_data: dict) -> dict:
    """
    Inserts a newly generated chart and its query parameters into Supabase user_charts table.
    Raises RuntimeError on failure and returns the actual inserted row.
    """
    if not supabase:
        raise RuntimeError("Database insert failed: Supabase client is not initialized.")
    try:
        row = {
            "user_id": user_id,
            "chart_fingerprint": chart_fingerprint,
            "birth_date": birth_data["birth_date"],
            "birth_time": birth_data["birth_time"],
            "birth_city": birth_data["birth_city"],
            "birth_country": birth_data.get("birth_country", "Unknown"),
            "latitude": birth_data["latitude"],
            "longitude": birth_data["longitude"],
            "timezone": birth_data["timezone"],
            "ayanamsa": chart_data["metadata"]["ayanamsa"],
            "house_system": "placidus",
            "node_type": "true_node",
            "engine_version": chart_data["metadata"]["engine_version"],
            "chart_json": chart_data
        }
        
        response = supabase.table("user_charts").insert(row).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        raise RuntimeError("Database insert failed: No data returned from insert operation.")
    except Exception as e:
        err_msg = str(e)
        # Safely redact any service role keys if they are somehow present in the message
        if settings.supabase_service_role_key and settings.supabase_service_role_key in err_msg:
            err_msg = err_msg.replace(settings.supabase_service_role_key, "[REDACTED]")
        raise RuntimeError(f"Database insert failed: {err_msg}")
