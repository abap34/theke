from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..schemas import paper as paper_schema
from ..crud import paper as paper_crud
from ..services.pdf_processor import extract_metadata_from_pdf
from ..services.llm_service import generate_summary

router = APIRouter()


@router.get("/", response_model=List[paper_schema.Paper])
def get_papers(
    skip: int = 0,
    limit: int = 100,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all papers with optional filtering"""
    papers = paper_crud.get_papers(
        db=db, 
        skip=skip, 
        limit=limit, 
        tag_id=tag_id, 
        search=search
    )
    return papers


@router.post("/", response_model=paper_schema.Paper)
def create_paper(
    paper: paper_schema.PaperCreate,
    db: Session = Depends(get_db)
):
    """Create a new paper"""
    return paper_crud.create_paper(db=db, paper=paper)


@router.post("/extract-metadata")
async def extract_metadata_from_upload(
    file: UploadFile = File(...),
    use_llm: bool = Form(False)
):
    """Extract metadata from PDF without creating a paper"""
    try:
        # Extract metadata from PDF
        metadata = await extract_metadata_from_pdf(file, use_llm=use_llm)
        return {"metadata": metadata}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/upload", response_model=paper_schema.Paper)
async def upload_paper(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),  # JSON string
    use_llm_extraction: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Upload a PDF and create a paper entry with extracted metadata"""
    try:
        # Extract metadata from PDF
        metadata = await extract_metadata_from_pdf(file, use_llm=use_llm_extraction)
        
        # Override with form data if provided
        if title:
            metadata["title"] = title
        if authors:
            import json
            metadata["authors"] = json.loads(authors)
        
        # Create paper
        paper_data = paper_schema.PaperCreate(**metadata)
        paper = paper_crud.create_paper(db=db, paper=paper_data)
        
        # Save PDF file and update paper with file path
        file_path = await paper_crud.save_pdf_file(paper.id, file)
        paper_update = paper_schema.PaperUpdate(pdf_path=file_path)
        paper = paper_crud.update_paper(db=db, paper_id=paper.id, paper_update=paper_update)
        
        return paper
        
    except ValueError as e:
        # Configuration errors (API key missing, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        # Library missing errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # General errors
        error_msg = str(e)
        if "API key" in error_msg.lower():
            raise HTTPException(status_code=400, detail="LLM API key is not configured or invalid")
        else:
            raise HTTPException(status_code=400, detail=f"Upload failed: {error_msg}")


@router.get("/{paper_id}", response_model=paper_schema.Paper)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Get a specific paper by ID"""
    paper = paper_crud.get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.put("/{paper_id}", response_model=paper_schema.Paper)
def update_paper(
    paper_id: int,
    paper_update: paper_schema.PaperUpdate,
    db: Session = Depends(get_db)
):
    """Update a paper"""
    paper = paper_crud.update_paper(db=db, paper_id=paper_id, paper_update=paper_update)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """Delete a paper"""
    success = paper_crud.delete_paper(db=db, paper_id=paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"message": "Paper deleted successfully"}


@router.post("/{paper_id}/summary", response_model=paper_schema.Paper)
async def generate_paper_summary(
    paper_id: int,
    db: Session = Depends(get_db)
):
    """Generate a summary for a paper using LLM"""
    paper = paper_crud.get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        # Generate summary using LLM
        summary = await generate_summary(paper)
        
        # Update paper with summary
        paper_update = paper_schema.PaperUpdate(summary=summary)
        updated_paper = paper_crud.update_paper(db=db, paper_id=paper_id, paper_update=paper_update)
        
        return updated_paper
        
    except ValueError as e:
        # Configuration errors (API key missing, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        # Library missing errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # General API errors
        error_msg = str(e)
        if "API key" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid API key or authentication failed")
        elif "rate limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="API rate limit exceeded. Please try again later")
        elif "quota" in error_msg.lower():
            raise HTTPException(status_code=402, detail="API quota exceeded. Please check your billing")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to generate summary: {error_msg}")


@router.post("/{paper_id}/tags/{tag_id}")
def add_tag_to_paper(
    paper_id: int,
    tag_id: int,
    db: Session = Depends(get_db)
):
    """Add a tag to a paper"""
    success = paper_crud.add_tag_to_paper(db=db, paper_id=paper_id, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper or tag not found")
    return {"message": "Tag added to paper successfully"}


@router.delete("/{paper_id}/tags/{tag_id}")
def remove_tag_from_paper(
    paper_id: int,
    tag_id: int,
    db: Session = Depends(get_db)
):
    """Remove a tag from a paper"""
    success = paper_crud.remove_tag_from_paper(db=db, paper_id=paper_id, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper or tag not found")
    return {"message": "Tag removed from paper successfully"}