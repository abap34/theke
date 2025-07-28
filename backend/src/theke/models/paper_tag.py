from sqlalchemy import Column, Integer, ForeignKey, Table

from ..core.database import Base

# Association table for many-to-many relationship between papers and tags
paper_tags = Table(
    'paper_tags',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Alias for backward compatibility
PaperTag = paper_tags