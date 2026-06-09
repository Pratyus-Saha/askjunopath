# AskJunoPath Day 1 MVP Verification Checklist

Use this checklist to verify that the Day 1 MVP scaffold and chart caching function correctly in both local development and production environments.

## Local Backend Verification

- [ ] **Health Endpoint Works**
  - Command: `curl http://localhost:7860/health`
  - Expected Response: `{"status":"ok","version":"1.0.0","service":"askjunopath-api"}`

- [ ] **Astronomical Calculation Integrity**
  - Run the validation script: `python backend/scripts/test_chart.py`
  - Expected Output: Passes assertions for:
    - Ayanamsa value around `23.79` degrees.
    - Sun sidereal longitude between `270` and `276` degrees.
    - Rahu and Ketu separated by exactly `180.0` degrees.

- [ ] **First Chart Request (Cache MISS)**
  - Make a request to `/chart/generate` with a new profile.
  - Expected Response: `cache_status` is `"MISS"`, `chart_id` is returned, and data is saved to Supabase.

- [ ] **Second Chart Request (Cache HIT)**
  - Resend the exact same request with the same `X-User-Id`.
  - Expected Response: `cache_status` is `"HIT"`, `chart_id` is identical to the first request, and calculations are not rerun.

- [ ] **Database Integrity**
  - Inspect the Supabase database.
  - Expected Result: Exactly one row exists for that fingerprint. No duplicate rows created.

- [ ] **Docker Execution**
  - Build and run the docker container:
    ```bash
    docker build -t askjunopath-backend ./backend
    docker run -p 7860:7860 --env-file ./backend/.env askjunopath-backend
    ```
  - Verify `http://localhost:7860/health` returns status ok.

---

## Production / Cloud Backend Verification

- [ ] **Azure /health Works**
  - Verify that your Azure Container Apps backend URL `/health` endpoint is reachable and returns status `"ok"`.

- [ ] **Azure /chart/generate Cache MISS**
  - Send the first calculation request. Verify it returns `"MISS"`.

- [ ] **Azure /chart/generate Cache HIT**
  - Send the same calculation request again. Verify it returns `"HIT"`.

---

## End-to-End Verification

- [ ] **Local Frontend to Local Backend**
  - Run the Next.js frontend locally (`npm run dev` in `frontend/` with `NEXT_PUBLIC_API_URL=http://localhost:7860`).
  - Submit the form at `http://localhost:3000/chart`.
  - Verify that the page loads the chart successfully and shows `MISS` then `HIT` upon resubmission.

- [ ] **Vercel Frontend to Azure Backend**
  - Deploy frontend to Vercel with environment variable `NEXT_PUBLIC_API_URL` pointing to the live Azure Container App backend.
  - Test the page, verify `HIT` / `MISS` logic behaves correctly end-to-end.
