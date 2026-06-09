# AskJunoPath - Day 1 MVP Scaffold with Chart Caching

AskJunoPath is an astrological calculation application that combines KP astrology, planetary math (via Swiss Ephemeris), and user chart caching.

This repository contains the Day 1 MVP scaffolding:
- **Backend**: Python + FastAPI + Swiss Ephemeris (`pyswisseph`) + Supabase DB.
- **Frontend**: Next.js App Router (TypeScript, Tailwind).
- **Infrastructure**: Docker + GitHub Container Registry + Azure Container Apps.

---

## 1. Supabase SQL Setup

Before running the backend, set up the database. Open your Supabase Dashboard, navigate to the **SQL Editor**, and run the following commands to create the `user_charts` table:

```sql
-- Create the chart cache table
CREATE TABLE IF NOT EXISTS user_charts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    chart_fingerprint VARCHAR(64) NOT NULL,
    birth_date DATE NOT NULL,
    birth_time TIME NOT NULL,
    birth_city VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    timezone VARCHAR(100) NOT NULL,
    ayanamsa DOUBLE PRECISION NOT NULL,
    engine_version VARCHAR(50) NOT NULL,
    chart JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_fingerprint UNIQUE (user_id, chart_fingerprint)
);

-- Optimize lookup speed for cached fingerprints
CREATE INDEX IF NOT EXISTS idx_user_charts_user_fingerprint 
ON user_charts(user_id, chart_fingerprint);
```

---

## 2. Local Backend Setup

The backend runs on **FastAPI** and requires Python 3.10 or 3.11.

### Step 2.1: Clone and Configuration
Navigate to the `backend/` directory and configure environment variables:
```bash
cd backend
cp .env.example .env
```
Ensure `.env` contains:
```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
CHART_ENGINE_VERSION=1.0.0
ENVIRONMENT=development
```

### Step 2.2: Setup Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2.3: Run Astronomical Calculations Verification
Verify that the Swiss Ephemeris engine is working and returns mathematically correct Vedic structures:
```bash
python scripts/test_chart.py
```

### Step 2.4: Run the API Server
Start the Uvicorn local development server:
```bash
uvicorn app.main:app --reload --port 7860
```
- API Docs: `http://localhost:7860/docs`
- Health check: `http://localhost:7860/health`

---

## 3. Local Frontend Setup

The frontend is a **Next.js** App Router project.

### Step 3.1: Configuration
Navigate to `frontend/` and configure environments:
```bash
cd ../frontend
cp .env.example .env
```
Ensure `frontend/.env` is set to point to your local backend API:
```env
NEXT_PUBLIC_API_URL=http://localhost:7860
```

### Step 3.2: Install and Run Next.js
```bash
npm install
npm run dev
```
Open `http://localhost:3000` to load the application homepage. Go to `/chart` to search and generate charts.

---

## 4. Docker Build & Test Local

To verify that the application compiles correctly in containerized environments:

```bash
# Build the Docker image
docker build -t askjunopath-backend ./backend

# Run the container locally
docker run -p 7860:7860 --env-file ./backend/.env askjunopath-backend
```
Test the `/health` endpoint at `http://localhost:7860/health`.

---

## 5. Deployment Guide

Refer to [deployment-notes.md](file:///c:/Users/assas/askjunopath/deployment-notes.md) for full commands on:
1. Building and publishing the container image to **GitHub Container Registry (GHCR)**.
2. Deploying to **Azure Container Apps**.
3. Deploying the frontend to **Vercel**.

---

## 6. End-to-End Validation Checklist

Refer to [day1-checklist.md](file:///c:/Users/assas/askjunopath/day1-checklist.md) for verifying compilation, caching hits, database updates, and integration.
