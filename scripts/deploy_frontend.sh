#!/usr/bin/env bash
set -euo pipefail

echo "Deploying frontend to Vercel..."
cd frontend
npx vercel --prod --yes

echo "Frontend deploy complete."
