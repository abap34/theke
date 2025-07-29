from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import find_dotenv, set_key
from pydantic import BaseModel

from ..core.config import settings
from ..core.database import get_db
from ..schemas import paper as paper_schema, job as job_schema
from ..crud import paper as paper_crud, job as job_crud
from ..services.pdf_processor import extract_metadata_from_pdf
from ..services.llm_service import generate_summary
from ..services.thumbnail_generator import thumbnail_generator

router = APIRouter()


class PromptUpdate(BaseModel):
    prompt: str

# Legacy request model - keeping for compatibility
class SummaryRequest(BaseModel):
    custom_prompt: Optional[str] = None


@router.get("/settings/summary-prompt", response_model=PromptUpdate)
def get_summary_prompt():
    """Get the current summary prompt"""
    return PromptUpdate(prompt=settings.SUMMARY_PROMPT)

@router.put("/settings/summary-prompt")
def update_summary_prompt(prompt_update: PromptUpdate):
    """Update the summary prompt in the .env file"""
    try:
        env_path = find_dotenv()
        if not env_path:
            # If .env is not found, assume it's in the project root
            env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")

        if not os.path.exists(env_path):
             # Create the file if it doesn't exist
            with open(env_path, "w") as f:
                pass

        set_key(env_path, "SUMMARY_PROMPT", prompt_update.prompt)
        
        # Update the settings object in memory
        settings.SUMMARY_PROMPT = prompt_update.prompt
        
        return {"message": "Summary prompt updated successfully. Restart the application for the changes to take full effect."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update .env file: {str(e)}")



@router.get("/")
def get_papers(
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
    author: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all papers with advanced filtering, sorting, and search"""
    papers, total_count = paper_crud.get_papers(
        db=db, 
        skip=skip, 
        limit=limit, 
        tag_id=tag_id, 
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        year_from=year_from,
        year_to=year_to,
        has_summary=has_summary,
        has_pdf=has_pdf,
        author=author
    )
    
    return {
        "papers": papers,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total_count
    }


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
        # Reset file pointer to beginning
        await file.seek(0)
        
        # Extract metadata from PDF
        metadata = await extract_metadata_from_pdf(file, use_llm=use_llm_extraction)
        
        # Reset file pointer again for saving
        await file.seek(0)
        
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
        try:
            file_path = await paper_crud.save_pdf_file(paper.id, file)
            print(f"Got file_path from save_pdf_file: {file_path}")
            if file_path:
                paper_update = paper_schema.PaperUpdate(pdf_path=file_path)
                print(f"Updating paper with pdf_path: {file_path}")
                updated_paper = paper_crud.update_paper(db=db, paper_id=paper.id, paper_update=paper_update)
                if updated_paper:
                    paper = updated_paper
                    print(f"Paper updated successfully, pdf_path: {paper.pdf_path}")
                else:
                    print("Warning: update_paper returned None")
            else:
                print("Warning: save_pdf_file returned None")
        except Exception as file_save_error:
            print(f"File save error: {file_save_error}")
            # Continue without saving file, but paper record is still created
        
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


@router.get("/{paper_id}/thumbnail")
def get_paper_thumbnail(paper_id: int, db: Session = Depends(get_db)):
    """Get or generate a thumbnail for a paper's PDF"""
    paper = paper_crud.get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.pdf_path:
        raise HTTPException(status_code=404, detail="Paper does not have a PDF file")
    
    # Check if PDF file exists
    if not os.path.exists(paper.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Try to get existing thumbnail
    thumbnail_path = thumbnail_generator.get_thumbnail_path(paper.pdf_path)
    
    # Generate thumbnail if it doesn't exist
    if not thumbnail_path:
        thumbnail_path = thumbnail_generator.generate_thumbnail(paper.pdf_path)
    
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=500, detail="Failed to generate thumbnail")
    
    return FileResponse(
        thumbnail_path,
        media_type="image/png",
        filename=f"paper_{paper_id}_thumbnail.png"
    )


@router.post("/{paper_id}/generate-abstract")
async def generate_paper_abstract(
    paper_id: int,
    db: Session = Depends(get_db)
):
    """Generate abstract for a paper using LLM"""
    paper = paper_crud.get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.pdf_path:
        raise HTTPException(status_code=400, detail="Paper does not have a PDF file")
    
    try:
        # Extract text from PDF
        from ..services.pdf_processor import extract_text_from_pdf_file
        from pathlib import Path
        
        # Convert to absolute path
        pdf_path = Path(paper.pdf_path)
        if not pdf_path.is_absolute():
            from ..core.config import settings
            pdf_path = Path(settings.UPLOAD_DIR) / pdf_path.name
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        text_content = await extract_text_from_pdf_file(str(pdf_path))
        
        # Generate abstract using LLM
        from ..services.llm_service import get_llm_provider
        provider = get_llm_provider()
        
        abstract_prompt = """以下の学術論文から、簡潔で学術的なアブストラクト（要約）を日本語で生成してください。

アブストラクトは以下の要素を含むべきです：
1. 研究の目的と背景（2-3文）
2. 使用した手法やアプローチ（2-3文）
3. 主要な結果や発見（2-3文）
4. 未解決の問題や今後の研究の方向性（2-3文）
5. 結論や意義（2-3文）

全体で500-1000文字程度の簡潔なアブストラクトを作成してください。
学術的で客観的な文体で書いてください。
"""
        
        abstract = await provider.generate_summary(text_content, abstract_prompt)
        
        # Update paper with generated abstract
        from ..schemas.paper import PaperUpdate
        paper_update = PaperUpdate(abstract=abstract)
        updated_paper = paper_crud.update_paper(db=db, paper_id=paper_id, paper_update=paper_update)
        
        return {
            "message": "Abstract generated successfully", 
            "abstract": abstract,
            "paper_id": paper_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate abstract: {str(e)}")


@router.post("/{paper_id}/summary", response_model=job_schema.SummaryJobResponse)
async def generate_paper_summary(
    paper_id: int,
    request: job_schema.SummaryJobCreate,
    db: Session = Depends(get_db)
):
    """Start summary generation job for a paper"""
    paper = paper_crud.get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        # Create background job
        parameters = {}
        if request.custom_prompt:
            parameters["custom_prompt"] = request.custom_prompt
            
        job = job_crud.create_job(
            db=db,
            job_type="summary_generation",
            paper_id=paper_id,
            parameters=parameters
        )
        
        # Start background processing
        from ..services.background_tasks import start_background_task
        start_background_task(job.id, "summary_generation")
        
        return job_schema.SummaryJobResponse(
            job_id=job.id,
            status="pending",
            message="要約生成を開始しました。進行状況はジョブ状態APIで確認できます。"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start summary generation: {str(e)}")


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


@router.get("/jobs/{job_id}", response_model=job_schema.JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job status and progress"""
    job = job_crud.get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job