"""Shared test configuration.

Points Swiss Ephemeris at the repo's bundled ``backend/ephe`` ``.se1`` files
when ``SE_EPHE_PATH`` is not already set, so engines that read the env var at
call time (ephemeris / dasha / transit) use the real ephemeris instead of
falling back to Moshier. Importing conftest runs before test collection, so the
variable is in place before any engine call.
"""

from __future__ import annotations

import os
from pathlib import Path

_EPHE_DIR = Path(__file__).resolve().parent.parent / "ephe"

if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)

# app.core.config.Settings requires the Supabase values at import time
# (fail-loudly-at-startup, audit finding #3); default them here so engine
# modules that read shared config stay importable in this suite.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
