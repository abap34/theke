from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from .tag import Tag


class PaperBase(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    external_id: Optional[str] = None

    # 新規追加: 外部ID管理と引用統計
    external_ids: Optional[Dict[str, str]] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None


class PaperCreate(PaperBase):
    pass


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    external_id: Optional[str] = None
    external_ids: Optional[Dict[str, str]] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    pdf_path: Optional[str] = None


class PaperInDB(PaperBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[Tag] = []


class Paper(PaperInDB):
    pass
