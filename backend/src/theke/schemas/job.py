from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class JobCreate(BaseModel):
    type: str
    paper_id: int
    parameters: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    id: str
    type: str
    paper_id: int
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    progress_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SummaryJobCreate(BaseModel):
    custom_prompt: Optional[str] = None


class SummaryJobResponse(BaseModel):
    job_id: str
    status: str
    message: str