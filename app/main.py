from fastapi import FastAPI
from app.config import settings
from app.database import engine, Base
from app.api.logs import router as logs_router

# Database tables are managed via Alembic migrations

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "app": settings.app_name,
        "status": "healthy",
        "documentation": "/docs"
    }

# Include API routes
app.include_router(logs_router)
