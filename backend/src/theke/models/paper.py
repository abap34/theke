from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    authors = Column(JSON, nullable=False)  # List[str]
    year = Column(Integer, nullable=True, index=True)
    doi = Column(String, nullable=True, unique=True, index=True)
    journal = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    pdf_path = Column(String, nullable=True)
    summary = Column(Text, nullable=True)  # LLM generated summary
    notes = Column(Text, nullable=True)  # User notes
    external_id = Column(String, nullable=True)  # arXiv ID, PubMed ID, etc.

    # 新規追加: 外部ID管理と引用統計
    external_ids = Column(
        JSON, nullable=True
    )  # {"openalex": "W123", "semantic_scholar": "456"}
    citation_count = Column(Integer, nullable=True)  # この論文を引用している論文数
    reference_count = Column(Integer, nullable=True)  # この論文が引用している論文数

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    citing_citations = relationship(
        "Citation",
        foreign_keys="Citation.citing_paper_id",
        back_populates="citing_paper",
    )
    cited_citations = relationship(
        "Citation", foreign_keys="Citation.cited_paper_id", back_populates="cited_paper"
    )
    tags = relationship("Tag", secondary="paper_tags", back_populates="papers")
    jobs = relationship("Job", back_populates="paper")
