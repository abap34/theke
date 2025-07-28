from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from typing import List, Optional
from pathlib import Path
import aiofiles
import uuid

from ..models.paper import Paper
from ..models.tag import Tag
from ..schemas.paper import PaperCreate, PaperUpdate
from ..core.config import settings


def get_paper(db: Session, paper_id: int) -> Optional[Paper]:
    """Get a single paper by ID"""
    return db.query(Paper).filter(Paper.id == paper_id).first()


def get_papers(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    tag_id: Optional[int] = None,
    search: Optional[str] = None
) -> List[Paper]:
    """Get papers with optional filtering"""
    query = db.query(Paper)
    
    # Filter by tag
    if tag_id:
        query = query.join(Paper.tags).filter(Tag.id == tag_id)
    
    # Search in title, authors, abstract
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Paper.title.ilike(search_term),
                text("JSON_EXTRACT(authors, '$') LIKE :search").params(search=search_term),
                Paper.abstract.ilike(search_term)
            )
        )
    
    return query.offset(skip).limit(limit).all()


def create_paper(db: Session, paper: PaperCreate) -> Paper:
    """Create a new paper"""
    db_paper = Paper(**paper.model_dump())
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper


def update_paper(db: Session, paper_id: int, paper_update: PaperUpdate) -> Optional[Paper]:
    """Update a paper"""
    db_paper = get_paper(db, paper_id)
    if not db_paper:
        return None
    
    update_data = paper_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_paper, field, value)
    
    db.commit()
    db.refresh(db_paper)
    return db_paper


def delete_paper(db: Session, paper_id: int) -> bool:
    """Delete a paper"""
    db_paper = get_paper(db, paper_id)
    if not db_paper:
        return False
    
    # Delete associated PDF file if exists
    if db_paper.pdf_path:
        pdf_path = Path(db_paper.pdf_path)
        if pdf_path.exists():
            pdf_path.unlink()
    
    db.delete(db_paper)
    db.commit()
    return True


async def save_pdf_file(paper_id: int, file) -> str:
    """Save uploaded PDF file"""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    filename = f"{paper_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Return relative path for database storage
    return f"uploads/{filename}"


def add_tag_to_paper(db: Session, paper_id: int, tag_id: int) -> bool:
    """Add a tag to a paper"""
    paper = get_paper(db, paper_id)
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    
    if not paper or not tag:
        return False
    
    if tag not in paper.tags:
        paper.tags.append(tag)
        db.commit()
    
    return True


def remove_tag_from_paper(db: Session, paper_id: int, tag_id: int) -> bool:
    """Remove a tag from a paper"""
    paper = get_paper(db, paper_id)
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    
    if not paper or not tag:
        return False
    
    if tag in paper.tags:
        paper.tags.remove(tag)
        db.commit()
    
    return True