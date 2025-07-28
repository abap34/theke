from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .api import papers, tags, citations, external
from .core.config import settings
from .core.database import create_tables

app = FastAPI(
    title="Theke Backend",
    description="Backend API for Theke paper management system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Include API routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(citations.router, prefix="/api/citations", tags=["citations"])
app.include_router(external.router, prefix="/api/external", tags=["external"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    create_tables()

@app.get("/")
async def root():
    return {"message": "Theke Backend API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}