from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    type = Column(String(50), nullable=False)  # "summary_generation", "citation_extraction", etc.
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    
    # Job parameters (JSON string)
    parameters = Column(Text)
    
    # Results
    result = Column(Text)  # Success result (JSON string)
    error_message = Column(Text)  # Error message if failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    progress_message = Column(String(255))

    # Relationship to paper
    paper = relationship("Paper", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id='{self.id}', type='{self.type}', status='{self.status}')>"