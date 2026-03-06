from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import auth, biomarkers, documents, events, trends

settings = get_settings()

app = FastAPI(
    title="Telivex API",
    description="Patient-controlled longitudinal health reconstruction platform",
    version="0.1.0",
)

# CORS - permissive for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(biomarkers.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(trends.router, prefix=settings.api_prefix)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "Telivex API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
