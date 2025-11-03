"""Type definitions and protocols for Theke backend."""

from typing import Any, Dict, List, Optional, Protocol, TypedDict
from abc import abstractmethod
from datetime import datetime


# Network graph types
class NodeData(TypedDict):
    """Data structure for graph nodes."""
    id: int
    title: str
    authors: List[str]
    year: Optional[int]


class GraphNode(TypedDict):
    """Structure for graph visualization nodes."""
    id: str
    label: str
    type: str
    resolved: bool
    data: NodeData


class GraphEdge(TypedDict):
    """Structure for graph visualization edges."""
    id: str
    from_: str
    to: str
    type: str


class CitationNetwork(TypedDict):
    """Complete citation network data."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Citation extraction types
class ExtractedCitation(TypedDict):
    """Structure for extracted citation data."""
    title: Optional[str]
    authors: Optional[List[str]]
    year: Optional[int]
    doi: Optional[str]
    journal: Optional[str]
    context: Optional[str]
    confidence_score: float
    extraction_source: str
    page_number: Optional[int]


# Service protocols
class CitationExtractorProtocol(Protocol):
    """Protocol for citation extraction services."""
    
    @abstractmethod
    async def extract_citations(self, paper_id: int, text: str) -> List[ExtractedCitation]:
        """Extract citations from text."""
        ...


class LLMServiceProtocol(Protocol):
    """Protocol for LLM service providers."""
    
    @abstractmethod
    async def generate_summary(self, text: str) -> str:
        """Generate summary from text."""
        ...
    
    @abstractmethod
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from text."""
        ...


class ExternalSearchProtocol(Protocol):
    """Protocol for external search services."""
    
    @abstractmethod
    async def search_papers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for papers using external API."""
        ...


# Configuration types
class DatabaseConfig(TypedDict):
    """Database configuration."""
    url: str
    echo: bool


class LLMConfig(TypedDict):
    """LLM service configuration."""
    provider: str
    api_key: str
    model: str
    max_tokens: Optional[int]


class AppConfig(TypedDict):
    """Application configuration."""
    database: DatabaseConfig
    llm: LLMConfig
    upload_dir: str
    debug: bool


# Error types
class ServiceError(Exception):
    """Base exception for service errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class ValidationError(ServiceError):
    """Validation error with field details."""
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field


class ExternalAPIError(ServiceError):
    """External API service error."""
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.service = service
        self.status_code = status_code


# Job types
class JobStatus(TypedDict):
    """Background job status."""
    job_id: str
    status: str
    progress: int
    message: Optional[str]
    result: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime