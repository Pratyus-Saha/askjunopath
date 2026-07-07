from fastapi import HTTPException, Request, status
from supabase import Client, create_client

from app.core.config import settings

# Auth verifies Supabase JWTs against the PUBLIC/ANON key, never the
# service-role key (db.py owns the service-role client; that key bypasses RLS
# and must never sit on the request-auth path). Both values come from Settings
# (env var or .env), where SUPABASE_KEY is required — a missing anon key fails
# loudly at startup rather than 500-ing every authed request.
SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key  # anon/public key


def _get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth not configured",
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


async def get_current_user(request: Request) -> str:
    """Extract and verify the user_id from a Supabase JWT bearer token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.split(" ", 1)[1]

    try:
        client = _get_supabase()
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return user_response.user.id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
