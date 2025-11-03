from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.tag import Tag
from ..schemas.tag import TagCreate, TagUpdate


def get_tag(db: Session, tag_id: int) -> Optional[Tag]:
    """Get a single tag by ID"""
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_tag_by_name(db: Session, name: str) -> Optional[Tag]:
    """Get a tag by name"""
    return db.query(Tag).filter(Tag.name == name).first()


def get_tags(db: Session, skip: int = 0, limit: int = 100) -> List[Tag]:
    """Get all tags"""
    return db.query(Tag).offset(skip).limit(limit).all()


def create_tag(db: Session, tag: TagCreate) -> Tag:
    """Create a new tag"""
    db_tag = Tag(**tag.model_dump())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def update_tag(db: Session, tag_id: int, tag_update: TagUpdate) -> Optional[Tag]:
    """Update a tag"""
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return None
    
    update_data = tag_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tag, field, value)
    
    db.commit()
    db.refresh(db_tag)
    return db_tag


def delete_tag(db: Session, tag_id: int) -> bool:
    """Delete a tag"""
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return False
    
    db.delete(db_tag)
    db.commit()
    return True


def get_or_create_tag(db: Session, tag_data: TagCreate) -> Tag:
    """Get an existing tag by name, or create a new one if it doesn't exist"""
    # First try to get existing tag by name
    existing_tag = get_tag_by_name(db, tag_data.name)
    if existing_tag:
        return existing_tag
    
    # If not found, create new tag
    return create_tag(db, tag_data)


def get_all_tags(db: Session) -> List[Tag]:
    """Get all tags without pagination"""
    return db.query(Tag).all()