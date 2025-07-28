from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..core.database import get_db
from ..schemas import citation as citation_schema
from ..crud import citation as citation_crud
from ..services.llm_service import extract_citations_from_paper
from ..services.citation_formatter import format_citation, CITATION_STYLES

router = APIRouter()


@router.get("/", response_model=List[citation_schema.Citation])
def get_citations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all citations"""
    citations = citation_crud.get_citations(db=db, skip=skip, limit=limit)
    return citations


@router.post("/", response_model=citation_schema.Citation)
def create_citation(
    citation: citation_schema.CitationCreate,
    db: Session = Depends(get_db)
):
    """Create a new citation"""
    return citation_crud.create_citation(db=db, citation=citation)


@router.get("/network")
def get_citation_network(db: Session = Depends(get_db)):
    """Get citation network data for graph visualization"""
    return citation_crud.get_citation_network(db=db)


@router.get("/format/{style}")
def format_citation_endpoint(
    style: str,
    paper_id: int,
    db: Session = Depends(get_db)
):
    """Generate formatted citation for a paper"""
    if style not in CITATION_STYLES:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported citation style. Available: {list(CITATION_STYLES.keys())}"
        )
    
    from ..crud.paper import get_paper
    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        formatted_citation = format_citation(paper, style)
        return {"citation": formatted_citation, "style": style}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/{paper_id}", response_model=List[citation_schema.Citation])
async def extract_citations(
    paper_id: int,
    db: Session = Depends(get_db)
):
    """Extract citations from a paper using Semantic Scholar API"""
    from ..crud.paper import get_paper
    from ..services.semantic_scholar_service import extract_citations_from_semantic_scholar
    
    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        # Extract citations using Semantic Scholar
        extracted_citations = await extract_citations_from_semantic_scholar(
            paper_title=paper.title,
            paper_doi=paper.doi
        )
        
        if not extracted_citations:
            raise HTTPException(
                status_code=404, 
                detail="Paper not found on Semantic Scholar or no references available"
            )
        
        # Clear existing citations for this paper
        citation_crud.delete_citations_by_paper(db=db, paper_id=paper_id)
        
        # Save extracted citations to database
        saved_citations = []
        for citation_data in extracted_citations:
            citation_create = citation_schema.CitationCreate(
                citing_paper_id=paper_id,
                cited_title=citation_data.get('title'),
                cited_authors=citation_data.get('authors', []),
                cited_year=citation_data.get('year'),
                cited_journal=citation_data.get('journal'),
                cited_doi=citation_data.get('doi'),
                status="unresolved"
            )
            saved_citation = citation_crud.create_citation(db=db, citation=citation_create)
            saved_citations.append(saved_citation)
        
        return saved_citations
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract citations: {str(e)}")


@router.get("/{citation_id}", response_model=citation_schema.Citation)
def get_citation(citation_id: int, db: Session = Depends(get_db)):
    """Get a specific citation by ID"""
    citation = citation_crud.get_citation(db=db, citation_id=citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation


@router.put("/{citation_id}", response_model=citation_schema.Citation)
def update_citation(
    citation_id: int,
    citation_update: citation_schema.CitationUpdate,
    db: Session = Depends(get_db)
):
    """Update a citation"""
    citation = citation_crud.update_citation(db=db, citation_id=citation_id, citation_update=citation_update)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation


@router.delete("/{citation_id}")
def delete_citation(citation_id: int, db: Session = Depends(get_db)):
    """Delete a citation"""
    success = citation_crud.delete_citation(db=db, citation_id=citation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Citation not found")
    return {"message": "Citation deleted successfully"}


@router.post("/{citation_id}/resolve")
def resolve_citation(
    citation_id: int,
    cited_paper_id: int,
    db: Session = Depends(get_db)
):
    """Resolve an unresolved citation by linking it to an existing paper"""
    citation = citation_crud.resolve_citation(db=db, citation_id=citation_id, cited_paper_id=cited_paper_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation or target paper not found")
    return citation


@router.get("/paper/{paper_id}", response_model=List[citation_schema.Citation])
def get_paper_citations(paper_id: int, db: Session = Depends(get_db)):
    """Get all citations for a specific paper"""
    citations = citation_crud.get_citations_by_paper(db=db, paper_id=paper_id)
    return citations