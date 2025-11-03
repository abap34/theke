from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.types import PositiveInt

from .tag import Tag


class PaperBase(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=500, description="Paper title")]
    authors: Annotated[
        List[str], 
        Field(min_length=1, description="List of authors")
    ]
    year: Annotated[
        Optional[int], 
        Field(ge=1800, le=2100, description="Publication year")
    ] = None
    doi: Annotated[
        Optional[str], 
        Field(pattern=r'^10\.\d+\/.*$', description="DOI in valid format")
    ] = None
    journal: Annotated[
        Optional[str], 
        Field(max_length=200, description="Journal name")
    ] = None
    abstract: Annotated[
        Optional[str], 
        Field(max_length=5000, description="Paper abstract")
    ] = None
    summary: Annotated[
        Optional[str],
        Field(max_length=10000, description="AI-generated summary")
    ] = None
    notes: Annotated[
        Optional[str], 
        Field(max_length=5000, description="User notes")
    ] = None
    external_id: Annotated[
        Optional[str], 
        Field(max_length=100, description="External identifier")
    ] = None

    # 外部ID管理と引用統計
    external_ids: Annotated[
        Optional[Dict[str, str]], 
        Field(description="External IDs from various sources")
    ] = None
    citation_count: Annotated[
        Optional[int], 
        Field(ge=0, description="Number of citations")
    ] = None
    reference_count: Annotated[
        Optional[int], 
        Field(ge=0, description="Number of references")
    ] = None

    @field_validator('authors')
    @classmethod
    def validate_authors_not_empty(cls, v: List[str]) -> List[str]:
        if not v or all(not author.strip() for author in v):
            raise ValueError('At least one non-empty author must be provided')
        return [author.strip() for author in v if author.strip()]
    
    @field_validator('title')
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @model_validator(mode='after')
    def validate_external_ids(self) -> 'PaperBase':
        if self.external_ids:
            valid_sources = {'arxiv', 'pubmed', 'doi', 'semantic_scholar', 'crossref'}
            for source in self.external_ids.keys():
                if source not in valid_sources:
                    raise ValueError(f'Invalid external ID source: {source}')
        return self


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
