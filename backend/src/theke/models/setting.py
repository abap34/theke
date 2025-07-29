from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from ..core.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50]}...')>"