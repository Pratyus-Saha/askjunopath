"""Shared env defaults for the root test suite.

``app.core.config.Settings`` requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
and SUPABASE_KEY at import time (fail-loudly-at-startup, audit finding #3).
conftest is imported before any test module, so the defaults set here are in
place before the first ``app`` import. Individual test modules may still
``setdefault`` their own values; those remain no-ops after this.
"""

from __future__ import annotations

import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
