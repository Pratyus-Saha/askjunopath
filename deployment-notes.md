> **OUTDATED — DO NOT RUN ANY COMMAND IN THIS FILE.**
> The app is `askjunopath-backend` (NOT `askjunopath-api`), port `8000` (NOT
> `7860`), current image `v1.2.1+`, tags never reused (D019). Deploys happen
> only via `scripts/deploy_backend.sh` / `deploy_frontend.sh` (D008, built
> Jun 13). Until then: no deploys.

---

# Deployment Notes - AskJunoPath Backend

This guide outlines the steps to build, publish, and deploy the AskJunoPath FastAPI backend using GitHub Container Registry (GHCR) and Azure Container Apps.

---

## 1. Build and Publish Docker Image to GHCR

Replace `YOUR_USERNAME` with your GitHub username (in lowercase).

### Step 1.1: Log in to GHCR
Generate a GitHub Personal Access Token (PAT) with `read:packages` and `write:packages` permissions, then log in:
```bash
echo "YOUR_PAT_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Step 1.2: Build the Container Image
Run this from the project root directory:
```bash
docker build -t ghcr.io/YOUR_USERNAME/askjunopath-backend:v1.0.0 ./backend
```

### Step 1.3: Push the Image to GHCR
```bash
docker push ghcr.io/YOUR_USERNAME/askjunopath-backend:v1.0.0
```

---

## 2. Deploy to Azure Container Apps

### Step 2.1: Create Azure Resource Group
Create a resource group in your preferred location (e.g., `centralindia`):
```bash
az group create --name askjunopath-rg --location centralindia
```

### Step 2.2: Create Container Apps Environment
```bash
az containerapp env create \
  --name askjunopath-env \
  --resource-group askjunopath-rg \
  --location centralindia
```

### Step 2.3: Deploy the Container App
Deploy the container app with ingress set to external, binding port 7860. Pass registry credentials if your GHCR repository is private:

```bash
az containerapp create \
  --name askjunopath-api \
  --resource-group askjunopath-rg \
  --environment askjunopath-env \
  --image ghcr.io/YOUR_USERNAME/askjunopath-backend:v1.0.0 \
  --target-port 7860 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --registry-server ghcr.io \
  --registry-username YOUR_USERNAME \
  --registry-password YOUR_PAT_TOKEN
```

### Step 2.4: Set Environment Variables / Secrets
Set the required Supabase secrets on your container app:

```bash
az containerapp secret set \
  --name askjunopath-api \
  --resource-group askjunopath-rg \
  --secrets \
    supabase-url="https://your-project-ref.supabase.co" \
    supabase-role-key="your_service_role_key_here"

az containerapp update \
  --name askjunopath-api \
  --resource-group askjunopath-rg \
  --set-env-vars \
    SUPABASE_URL=secretref:supabase-url \
    SUPABASE_SERVICE_ROLE_KEY=secretref:supabase-role-key \
    CHART_ENGINE_VERSION=1.0.0 \
    ENVIRONMENT=production
```

Once updated, your container app will restart with the secrets mounted. Retrieve the app's FQDN (URL) using:
```bash
az containerapp show \
  --name askjunopath-api \
  --resource-group askjunopath-rg \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```
This is the URL you will set as the `NEXT_PUBLIC_API_URL` for your frontend Vercel deployment.
