from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..schemas import tag as tag_schema
from ..crud import tag as tag_crud

router = APIRouter()


@router.get("/", response_model=List[tag_schema.Tag])
def get_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all tags"""
    tags = tag_crud.get_tags(db=db, skip=skip, limit=limit)
    return tags


@router.post("/", response_model=tag_schema.Tag)
def create_tag(
    tag: tag_schema.TagCreate,
    db: Session = Depends(get_db)
):
    """Create a new tag"""
    # Check if tag with same name already exists
    existing_tag = tag_crud.get_tag_by_name(db=db, name=tag.name)
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    return tag_crud.create_tag(db=db, tag=tag)


@router.get("/{tag_id}", response_model=tag_schema.Tag)
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    """Get a specific tag by ID"""
    tag = tag_crud.get_tag(db=db, tag_id=tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.put("/{tag_id}", response_model=tag_schema.Tag)
def update_tag(
    tag_id: int,
    tag_update: tag_schema.TagUpdate,
    db: Session = Depends(get_db)
):
    """Update a tag"""
    # Check if new name already exists (if name is being updated)
    if tag_update.name:
        existing_tag = tag_crud.get_tag_by_name(db=db, name=tag_update.name)
        if existing_tag and existing_tag.id != tag_id:
            raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    tag = tag_crud.update_tag(db=db, tag_id=tag_id, tag_update=tag_update)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """Delete a tag"""
    success = tag_crud.delete_tag(db=db, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"message": "Tag deleted successfully"}