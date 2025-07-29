from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pathlib import Path
import asyncio

from .api import papers, tags, citations, external, settings as settings_api
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

# Middleware to handle long-running requests
@app.middleware("http")
async def timeout_middleware(request, call_next):
    """Set longer timeout for summary generation endpoints"""
    if "/summary" in str(request.url):
        # Set a much longer timeout for summary generation (10 minutes)
        try:
            response = await asyncio.wait_for(call_next(request), timeout=600.0)
            return response
        except asyncio.TimeoutError:
            from fastapi import HTTPException
            raise HTTPException(status_code=504, detail="要約生成がタイムアウトしました。論文が長すぎるか、LLMサービスが応答していません。")
    else:
        # Normal timeout for other endpoints
        try:
            response = await asyncio.wait_for(call_next(request), timeout=30.0)
            return response
        except asyncio.TimeoutError:
            from fastapi import HTTPException
            raise HTTPException(status_code=504, detail="リクエストがタイムアウトしました。")


# Static files for uploads
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Include API routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(citations.router, prefix="/api/citations", tags=["citations"])
app.include_router(external.router, prefix="/api/external", tags=["external"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    create_tables()
    
    # Initialize default settings
    from .core.database import get_db
    from .crud.setting import initialize_default_settings
    
    db = next(get_db())
    try:
        initialize_default_settings(db)
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Theke Backend API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}