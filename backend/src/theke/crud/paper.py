from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, desc, asc, func
from typing import List, Optional, Literal
from pathlib import Path
import aiofiles
import uuid
from datetime import datetime

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
    search: Optional[str] = None,
    sort_by: Optional[str] = "updated_at",
    sort_order: Optional[str] = "desc",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    has_summary: Optional[bool] = None,
    has_pdf: Optional[bool] = None,
    author: Optional[str] = None
) -> tuple[List[Paper], int]:
    """Get papers with advanced filtering, sorting, and search"""
    query = db.query(Paper)
    count_query = db.query(func.count(Paper.id))
    
    # Apply filters to both queries
    filters = []
    
    # Filter by tag
    if tag_id:
        filters.append(Paper.tags.any(Tag.id == tag_id))
    
    # Year range filter
    if year_from:
        filters.append(Paper.year >= year_from)
    if year_to:
        filters.append(Paper.year <= year_to)
    
    # Summary filter
    if has_summary is not None:
        if has_summary:
            filters.append(Paper.summary.isnot(None))
            filters.append(Paper.summary != "")
        else:
            filters.append(
                or_(Paper.summary.is_(None), Paper.summary == "")
            )
    
    # PDF filter
    if has_pdf is not None:
        if has_pdf:
            filters.append(Paper.pdf_path.isnot(None))
            filters.append(Paper.pdf_path != "")
        else:
            filters.append(
                or_(Paper.pdf_path.is_(None), Paper.pdf_path == "")
            )
    
    # Author filter
    if author:
        author_term = f"%{author}%"
        filters.append(
            text("JSON_EXTRACT(authors, '$') LIKE :author").params(author=author_term)
        )
    
    # Search in title, authors, abstract, summary, notes
    if search:
        search_term = f"%{search}%"
        search_filter = or_(
            Paper.title.ilike(search_term),
            text("JSON_EXTRACT(authors, '$') LIKE :search").params(search=search_term),
            Paper.abstract.ilike(search_term),
            Paper.summary.ilike(search_term),
            Paper.notes.ilike(search_term),
            Paper.doi.ilike(search_term),
            Paper.journal.ilike(search_term)
        )
        filters.append(search_filter)
    
    # Apply all filters
    if filters:
        query = query.filter(and_(*filters))
        count_query = count_query.filter(and_(*filters))
    
    # Get total count
    total_count = count_query.scalar()
    
    # Apply sorting
    sort_column = getattr(Paper, sort_by, Paper.updated_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    papers = query.offset(skip).limit(limit).all()
    
    return papers, total_count


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
    try:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        filename = f"{paper_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = upload_dir / filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            print(f"File content size: {len(content) if content else 0} bytes")
            if not content:
                raise ValueError(f"File content is empty for file: {file.filename}")
            await f.write(content)
        
        # Verify file was saved
        if not file_path.exists():
            raise ValueError("File was not saved successfully")
        
        # Return relative path for database storage (just the filename with directory name)
        upload_dir_name = Path(settings.UPLOAD_DIR).name
        result_path = f"{upload_dir_name}/{filename}"
        print(f"Returning file path: {result_path}")
        return result_path
        
    except Exception as e:
        print(f"Error in save_pdf_file: {str(e)}")
        raise


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