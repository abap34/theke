from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    citing_paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    cited_paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)  # None if not in database
    
    # Citation metadata for unresolved citations
    cited_title = Column(String, nullable=True)
    cited_authors = Column(JSON, nullable=True)  # List[str]
    cited_year = Column(Integer, nullable=True)
    cited_doi = Column(String, nullable=True)
    cited_journal = Column(String, nullable=True)
    
    context = Column(Text, nullable=True)  # Citation context from the paper
    status = Column(String, nullable=False, default="unresolved")  # "resolved", "unresolved", "suggested"
    external_id = Column(String, nullable=True)  # arXiv ID, PubMed ID, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    citing_paper = relationship("Paper", foreign_keys=[citing_paper_id], back_populates="citing_citations")
    cited_paper = relationship("Paper", foreign_keys=[cited_paper_id], back_populates="cited_citations")