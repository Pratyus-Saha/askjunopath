# Security Notes - Secrets & Credentials Management

This guide documents the security protocols and environment configuration rules for the **AskJunoPath** project. Adhering to these rules prevents credential leaks and keeps production databases secure.

---

## 1. Local Environment Configs (`.env`)

- **`backend/.env`**: Used only for local execution of the FastAPI server. It contains highly sensitive keys like `SUPABASE_SERVICE_ROLE_KEY`. This file is gitignored and must **never** be committed to public or private source repositories.
- **`frontend/.env`**: Used only for local Next.js variables. This is also gitignored and must not be committed.

---

## 2. Client vs. Server Key Separation

- **Browser/Client Restrictions**: The frontend Next.js code runs in the user's browser. It must **only** use keys prefixed with `NEXT_PUBLIC_` (e.g., `NEXT_PUBLIC_API_URL`).
- **No Service Role Keys in Frontend**: The `SUPABASE_SERVICE_ROLE_KEY` is a superuser bypass key that grants full write/read access to the database. It must **never** be imported, hardcoded, or set as an environment variable in client-side/frontend code.

---

## 3. Production Environment Secret Storage

- **FastAPI Backend (Azure Container Apps)**:
  - Production credentials must not be packaged inside the Docker container or stored in source files.
  - They should be injected at runtime using **Azure Container Apps Secrets** and mapped to environment variables (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, etc.).
  - See [deployment-notes.md](file:///c:/Users/assas/askjunopath/deployment-notes.md) for the exact `az containerapp secret set` CLI syntax.

- **Next.js Frontend (Vercel)**:
  - Frontend environment variables (such as `NEXT_PUBLIC_API_URL`) must be configured in the **Vercel Project Settings -> Environment Variables** dashboard.
