from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    citing_paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    cited_paper_id = Column(
        Integer, ForeignKey("papers.id"), nullable=True
    )  # None if not in database

    # 抽出された引用情報
    cited_title = Column(String, nullable=True)
    cited_authors = Column(JSON, nullable=True)  # List[str]
    cited_year = Column(Integer, nullable=True)
    cited_doi = Column(String, nullable=True)
    cited_journal = Column(String, nullable=True)

    # メタデータ
    extraction_source = Column(
        String, nullable=False, default="unknown"
    )  # "pdf_text", "openalex", "crossref", "semantic_scholar"
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    context = Column(Text, nullable=True)  # 引用箇所の文脈
    page_number = Column(Integer, nullable=True)  # PDF内のページ番号

    # ステータス
    status = Column(
        String, nullable=False, default="pending"
    )  # "pending", "verified", "resolved", "rejected"
    external_id = Column(String, nullable=True)  # arXiv ID, PubMed ID, etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    citing_paper = relationship(
        "Paper", foreign_keys=[citing_paper_id], back_populates="citing_citations"
    )
    cited_paper = relationship(
        "Paper", foreign_keys=[cited_paper_id], back_populates="cited_citations"
    )
