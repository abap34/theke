from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class CitationBase(BaseModel):
    citing_paper_id: int
    cited_paper_id: Optional[int] = None
    cited_title: Optional[str] = None
    cited_authors: Optional[List[str]] = None
    cited_year: Optional[int] = None
    cited_doi: Optional[str] = None
    cited_journal: Optional[str] = None
    context: Optional[str] = None
    status: str = "unresolved"
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
    context: Optional[str] = None
    status: Optional[str] = None
    external_id: Optional[str] = None


class CitationInDB(CitationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class Citation(CitationInDB):
    pass