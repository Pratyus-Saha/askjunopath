#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/pratyus-saha/askjunopath-backend:main"
APP_NAME="askjunopath-backend"
RESOURCE_GROUP="askjunopath-rg"

echo "Building Docker image..."
docker build -t "$IMAGE" ./backend

echo "Pushing to GHCR..."
docker push "$IMAGE"

echo "Updating Azure Container App..."
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$IMAGE"

echo "Backend deploy complete."
