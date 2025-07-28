try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./data/theke.db"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    DEFAULT_MODEL: str = "gpt-4"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    SUMMARY_PROMPT: str = "Please provide a concise summary of this academic paper in Japanese, focusing on the main research question, methodology, key findings, and implications."
    
    # External APIs
    ARXIV_BASE_URL: str = "http://export.arxiv.org/api/query"
    CROSSREF_BASE_URL: str = "https://api.crossref.org/works"
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()