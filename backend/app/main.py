from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.chart import router as chart_router

app = FastAPI(
    title="AskJunoPath API",
    version="1.0.0"
)

# Configure CORS (Allow all for Day 1 MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chart calculations router
app.include_router(chart_router)

@app.get("/health")
def health_check():
    """
    Health check endpoint for Azure Container Apps probes and local validation.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "askjunopath-api"
    }
