from datetime import datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import PositiveInt


ExtractionSource = Literal[
    "manual", 
    "crossref", 
    "semantic_scholar", 
    "openalex", 
    "arxiv",
    "pdf_extraction", 
    "pdf_text",  # PDF text extraction
    "llm", 
    "legacy",  # Migration compatibility
    "merged",  # Merged from multiple sources
    "unknown"
]
CitationStatus = Literal["pending", "verified", "rejected", "matched"]

class CitationBase(BaseModel):
    citing_paper_id: PositiveInt
    cited_paper_id: Optional[PositiveInt] = None

    # 抽出された引用情報
    cited_title: Annotated[
        Optional[str], 
        Field(max_length=500, description="Title of cited paper")
    ] = None
    cited_authors: Annotated[
        Optional[List[str]], 
        Field(description="Authors of cited paper")
    ] = None
    cited_year: Annotated[
        Optional[int], 
        Field(ge=1800, le=2100, description="Publication year of cited paper")
    ] = None
    cited_doi: Annotated[
        Optional[str], 
        Field(pattern=r'^10\.\d+\/.*$', description="DOI of cited paper")
    ] = None
    cited_journal: Annotated[
        Optional[str], 
        Field(max_length=200, description="Journal of cited paper")
    ] = None

    # メタデータ
    extraction_source: ExtractionSource = "unknown"
    confidence_score: Annotated[
        float, 
        Field(ge=0.0, le=1.0, description="Confidence score for extraction")
    ] = 0.0
    context: Annotated[
        Optional[str], 
        Field(max_length=1000, description="Citation context from source")
    ] = None
    page_number: Annotated[
        Optional[PositiveInt], 
        Field(description="Page number where citation appears")
    ] = None

    # ステータス
    status: CitationStatus = "pending"
    external_id: Annotated[
        Optional[str], 
        Field(max_length=100, description="External identifier")
    ] = None

    @field_validator('cited_authors')
    @classmethod
    def validate_cited_authors(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            return [author.strip() for author in v if author.strip()]
        return v
    
    @field_validator('cited_title')
    @classmethod
    def validate_cited_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v


class CitationCreate(CitationBase):
    pass


class CitationUpdate(BaseModel):
    citing_paper_id: Optional[PositiveInt] = None
    cited_paper_id: Optional[PositiveInt] = None
    cited_title: Optional[str] = None
    cited_authors: Optional[List[str]] = None
    cited_year: Optional[int] = None
    cited_doi: Optional[str] = None
    cited_journal: Optional[str] = None
    extraction_source: Optional[ExtractionSource] = None
    confidence_score: Optional[float] = None
    context: Optional[str] = None
    page_number: Optional[PositiveInt] = None
    status: Optional[CitationStatus] = None
    external_id: Optional[str] = None


class CitationInDB(CitationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class Citation(CitationInDB):
    pass


class CitationPublic(BaseModel):
    """Public citation schema without sensitive fields like confidence and extraction_source"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    citing_paper_id: int
    cited_paper_id: Optional[int] = None
    
    # 基本的な引用情報のみ
    cited_title: Optional[str] = None
    cited_authors: Optional[List[str]] = None
    cited_year: Optional[int] = None
    cited_doi: Optional[str] = None
    cited_journal: Optional[str] = None
    
    # 公開可能なメタデータ（抽出ソースは除外）
    context: Optional[str] = None
    page_number: Optional[int] = None
    status: CitationStatus = "pending"
    external_id: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
