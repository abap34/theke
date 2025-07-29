from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CitationBase(BaseModel):
    citing_paper_id: int
    cited_paper_id: Optional[int] = None

    # 抽出された引用情報
    cited_title: Optional[str] = None
    cited_authors: Optional[List[str]] = None
    cited_year: Optional[int] = None
    cited_doi: Optional[str] = None
    cited_journal: Optional[str] = None

    # メタデータ
    extraction_source: str = "unknown"
    confidence_score: float = 0.0
    context: Optional[str] = None
    page_number: Optional[int] = None

    # ステータス
    status: str = "pending"
    external_id: Optional[str] = None


class CitationCreate(CitationBase):
    pass


class CitationUpdate(BaseModel):
    citing_paper_id: Optional[int] = None
    cited_paper_id: Optional[int] = None
    cited_title: Optional[str] = None
    cited_authors: Optional[List[str]] = None
    cited_year: Optional[int] = None
    cited_doi: Optional[str] = None
    cited_journal: Optional[str] = None
    extraction_source: Optional[str] = None
    confidence_score: Optional[float] = None
    context: Optional[str] = None
    page_number: Optional[int] = None
    status: Optional[str] = None
    external_id: Optional[str] = None


class CitationInDB(CitationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class Citation(CitationInDB):
    pass
