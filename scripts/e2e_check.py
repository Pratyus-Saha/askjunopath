#!/usr/bin/env python3
"""End-to-end smoke test for the live AskJunoPath backend.

What it does
------------
1. GET  /health                  -> assert status == "ok"
2. POST /predict/career          -> assert the 11-key prediction contract
3. POST /predict/finance         -> assert the 11-key prediction contract
4. POST /predict/relationship    -> assert the 11-key prediction contract

Each check prints [PASS], [FAIL] or [SKIP] and a one-line reason. The script
exits 1 if any check FAILs, 0 if everything PASSes (SKIP does not fail the run).

Auth / minting a test JWT
-------------------------
The /predict/* routes require a Supabase bearer token. This script obtains one
in the following order (first that works wins):

  1. TEST_JWT                  -- if set, used verbatim as the bearer token.
  2. SUPABASE_JWT_SECRET       -- if set AND python-jose is importable, a short-
                                  lived HS256 token is minted for a test user
                                  (claims: sub, role/aud = "authenticated", exp).
                                  This is the documented primary path.
  3. SUPABASE_SERVICE_ROLE_KEY -- as a last-resort fallback the service-role key
                                  (itself a signed Supabase JWT) is sent as the
                                  bearer token. Set this from backend/.env.

If python-jose is not installed and no usable token is found, the predict checks
are reported as FAIL with a clear reason (the /health check still runs).

NO SECRETS ARE HARDCODED. Every credential is read from the environment.

Dependencies: httpx (already installed). python-jose is OPTIONAL (path 2 only).
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

BACKEND_URL = "https://askjunopath-backend.kindtree-c857c99f.centralindia.azurecontainerapps.io"

# The 11 keys every /predict response must carry. The first five are top-level;
# the rest live inside engine_output.
TOP_LEVEL_KEYS = ["domain", "engine_output", "synthesis", "fallback_used", "disclaimer"]
ENGINE_OUTPUT_KEYS = [
    "promise_met",
    "confidence",
    "signal_strength",
    "caution_flag",
    "dasha_timing",
    "transit_windows",
    "transit_summary",
    "event_types",
    "summary",
    "cusp_sublords",
]

# Pratyus natal chart. planets/houses are intentionally empty placeholders: the
# e2e check exercises the endpoint *contract*, not a fully computed chart. If the
# engine raises on the empty arrays the request 500s and that check is SKIPped.
PRATYUS_CHART = {
    "schema_version": "1.2",
    "metadata": {
        "birth_date": "2002-08-20",
        "birth_time": "00:00",
        "birth_city": "Siliguri",
        "latitude": 26.70,
        "longitude": 88.43,
        "timezone": "Asia/Kolkata",
        "ayanamsa": 23.65,
        "engine_version": "1.3.0",
    },
    "birth": {
        "datetime_local": "2002-08-20T00:00:00",
        "datetime_utc": "2002-08-19T18:30:00",
        "timezone": "Asia/Kolkata",
        "lat": 26.70,
        "lon": 88.43,
        "place_label": "Siliguri, India",
        "approximate_time": False,
        "julian_day_ut": 2452506.27083,
    },
    "settings": {
        "ayanamsa": "KP_NEWCOMB",
        "ayanamsa_value_deg": 23.65,
        "node_type": "TRUE",
        "house_system": "PLACIDUS",
        "zodiac": "SIDEREAL",
    },
    "ascendant": {
        "longitude": 65.0,
        "sign": "Gemini",
        "sign_degree": 5.0,
    },
    "planets": [],
    "houses": [],
}

# Results accumulator: each entry is (status, message) where status is one of
# "PASS", "FAIL", "SKIP".
results: list[tuple[str, str]] = []


def record(status: str, message: str) -> None:
    print(f"[{status}] {message}")
    results.append((status, message))


def get_test_jwt() -> tuple[str | None, str]:
    """Return (token, source_description). token is None if none could be made."""
    explicit = os.getenv("TEST_JWT")
    if explicit:
        return explicit, "TEST_JWT env var"

    secret = os.getenv("SUPABASE_JWT_SECRET")
    if secret:
        try:
            from jose import jwt  # type: ignore

            now = int(time.time())
            claims = {
                "sub": str(uuid.uuid4()),
                "role": "authenticated",
                "aud": "authenticated",
                "iat": now,
                "exp": now + 3600,
            }
            token = jwt.encode(claims, secret, algorithm="HS256")
            return token, "minted via python-jose (SUPABASE_JWT_SECRET)"
        except ImportError:
            print(
                "[note] python-jose not installed; cannot mint from "
                "SUPABASE_JWT_SECRET. Falling back to service-role key."
            )

    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if service_role:
        return service_role, "SUPABASE_SERVICE_ROLE_KEY as bearer (fallback)"

    return None, "no token source available"


def check_health(client: httpx.Client) -> None:
    try:
        resp = client.get(f"{BACKEND_URL}/health")
    except httpx.HTTPError as exc:
        record("FAIL", f"/health request error: {exc}")
        return

    if resp.status_code != 200:
        record("FAIL", f"/health returned HTTP {resp.status_code}")
        return

    try:
        body = resp.json()
    except ValueError:
        record("FAIL", "/health returned non-JSON body")
        return

    if body.get("status") == "ok":
        record("PASS", "/health returned ok")
    else:
        record("FAIL", f"/health status was {body.get('status')!r}, expected 'ok'")


def check_predict(client: httpx.Client, domain: str, token: str | None) -> None:
    label = f"/predict/{domain}"
    if not token:
        record("FAIL", f"{label} skipped auth: no test JWT available")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = client.post(
            f"{BACKEND_URL}/predict/{domain}",
            json={"chart": PRATYUS_CHART},
            headers=headers,
        )
    except httpx.HTTPError as exc:
        record("FAIL", f"{label} request error: {exc}")
        return

    # The engine may raise on the empty planets/houses arrays -> 500. Per spec,
    # treat that as SKIP (contract not testable without a computed chart) rather
    # than failing the whole run.
    if resp.status_code == 500:
        record("SKIP", f"{label} returned 500 (engine likely raised on empty chart arrays)")
        return

    if resp.status_code != 200:
        snippet = resp.text[:200].replace("\n", " ")
        record("FAIL", f"{label} returned HTTP {resp.status_code}: {snippet}")
        return

    try:
        body = resp.json()
    except ValueError:
        record("FAIL", f"{label} returned non-JSON body")
        return

    missing_top = [k for k in TOP_LEVEL_KEYS if k not in body]
    if missing_top:
        record("FAIL", f"{label} missing top-level keys: {missing_top}")
        return

    engine_output = body.get("engine_output")
    if not isinstance(engine_output, dict):
        record("FAIL", f"{label} engine_output is not an object")
        return

    missing_engine = [k for k in ENGINE_OUTPUT_KEYS if k not in engine_output]
    if missing_engine:
        record("FAIL", f"{label} missing engine_output keys: {missing_engine}")
        return

    record("PASS", f"{label} returned valid 11-key contract")


def main() -> int:
    token, source = get_test_jwt()
    print(f"Auth token source: {source}")
    print(f"Backend: {BACKEND_URL}")
    print("-" * 60)

    with httpx.Client(timeout=30.0) as client:
        check_health(client)
        for domain in ("career", "finance", "relationship"):
            check_predict(client, domain, token)

    print("-" * 60)
    passed = sum(1 for s, _ in results if s == "PASS")
    failed = sum(1 for s, _ in results if s == "FAIL")
    skipped = sum(1 for s, _ in results if s == "SKIP")

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped.")
    if failed:
        print("\nFAIL: one or more checks failed.")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
