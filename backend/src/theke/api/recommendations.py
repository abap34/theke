"""
Recommendation API endpoints.
Provides paper recommendations based on authors, tags, citations, and content similarity.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..core.database import get_db
from ..services.recommendation_service import recommendation_service, RecommendationResult
from ..schemas.paper import Paper as PaperSchema

router = APIRouter()

# Pydantic models for requests/responses
class RecommendationResponse(BaseModel):
    paper: PaperSchema
    score: float
    reasons: List[str]
    recommendation_type: str

class UserInterestRequest(BaseModel):
    tag_ids: List[int] = []
    author_names: List[str] = []

@router.get("/related/{paper_id}")
async def get_related_papers(
    paper_id: int,
    limit: int = Query(10, description="Maximum number of recommendations", ge=1, le=50),
    types: List[str] = Query(
        ["author_based", "tag_based", "citation_based"], 
        description="Types of recommendations to include"
    ),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Get papers related to the specified paper using multiple recommendation strategies.
    """
    try:
        # Validate recommendation types
        valid_types = {"author_based", "tag_based", "citation_based", "content_based"}
        invalid_types = set(types) - valid_types
        if invalid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid recommendation types: {', '.join(invalid_types)}"
            )
        
        recommendations = recommendation_service.get_related_papers(
            db=db, 
            paper_id=paper_id, 
            limit=limit,
            include_types=types
        )
        
        # Convert to response format
        response = []
        for rec in recommendations:
            paper_dict = {
                "id": rec.paper.id,
                "title": rec.paper.title,
                "authors": rec.paper.authors,
                "year": rec.paper.year,
                "doi": rec.paper.doi,
                "journal": rec.paper.journal,
                "abstract": rec.paper.abstract,
                "summary": rec.paper.summary,
                "notes": rec.paper.notes,
                "pdf_path": rec.paper.pdf_path,
                "external_id": rec.paper.external_id,
                "created_at": rec.paper.created_at,
                "updated_at": rec.paper.updated_at,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in rec.paper.tags]
            }
            
            response.append(RecommendationResponse(
                paper=PaperSchema(**paper_dict),
                score=rec.score,
                reasons=rec.reasons,
                recommendation_type=rec.recommendation_type
            ))
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

@router.get("/by-author/{paper_id}")
async def get_recommendations_by_author(
    paper_id: int,
    limit: int = Query(10, description="Maximum number of recommendations", ge=1, le=50),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Get paper recommendations based on authors of the specified paper.
    """
    try:
        recommendations = recommendation_service.get_recommendations_by_author(
            db=db, 
            paper_id=paper_id, 
            limit=limit
        )
        
        # Convert to response format
        response = []
        for rec in recommendations:
            paper_dict = {
                "id": rec.paper.id,
                "title": rec.paper.title,
                "authors": rec.paper.authors,
                "year": rec.paper.year,
                "doi": rec.paper.doi,
                "journal": rec.paper.journal,
                "abstract": rec.paper.abstract,
                "summary": rec.paper.summary,
                "notes": rec.paper.notes,
                "pdf_path": rec.paper.pdf_path,
                "external_id": rec.paper.external_id,
                "created_at": rec.paper.created_at,
                "updated_at": rec.paper.updated_at,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in rec.paper.tags]
            }
            
            response.append(RecommendationResponse(
                paper=PaperSchema(**paper_dict),
                score=rec.score,
                reasons=rec.reasons,
                recommendation_type=rec.recommendation_type
            ))
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Author-based recommendation failed: {str(e)}")

@router.get("/by-tags/{paper_id}")
async def get_recommendations_by_tags(
    paper_id: int,
    limit: int = Query(10, description="Maximum number of recommendations", ge=1, le=50),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Get paper recommendations based on tags of the specified paper.
    """
    try:
        recommendations = recommendation_service.get_recommendations_by_tags(
            db=db, 
            paper_id=paper_id, 
            limit=limit
        )
        
        # Convert to response format
        response = []
        for rec in recommendations:
            paper_dict = {
                "id": rec.paper.id,
                "title": rec.paper.title,
                "authors": rec.paper.authors,
                "year": rec.paper.year,
                "doi": rec.paper.doi,
                "journal": rec.paper.journal,
                "abstract": rec.paper.abstract,
                "summary": rec.paper.summary,
                "notes": rec.paper.notes,
                "pdf_path": rec.paper.pdf_path,
                "external_id": rec.paper.external_id,
                "created_at": rec.paper.created_at,
                "updated_at": rec.paper.updated_at,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in rec.paper.tags]
            }
            
            response.append(RecommendationResponse(
                paper=PaperSchema(**paper_dict),
                score=rec.score,
                reasons=rec.reasons,
                recommendation_type=rec.recommendation_type
            ))
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag-based recommendation failed: {str(e)}")

@router.get("/popular")
async def get_popular_papers(
    limit: int = Query(10, description="Maximum number of papers", ge=1, le=50),
    days: Optional[int] = Query(None, description="Time range in days (recent papers)", ge=1, le=365),
    db: Session = Depends(get_db)
) -> List[PaperSchema]:
    """
    Get popular papers based on tags and recent activity.
    """
    try:
        papers = recommendation_service.get_popular_papers(
            db=db, 
            limit=limit,
            time_range_days=days
        )
        
        # Convert to response format
        response = []
        for paper in papers:
            paper_dict = {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "doi": paper.doi,
                "journal": paper.journal,
                "abstract": paper.abstract,
                "summary": paper.summary,
                "notes": paper.notes,
                "pdf_path": paper.pdf_path,
                "external_id": paper.external_id,
                "created_at": paper.created_at,
                "updated_at": paper.updated_at,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in paper.tags]
            }
            
            response.append(PaperSchema(**paper_dict))
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Popular papers query failed: {str(e)}")

@router.post("/by-interests")
async def get_recommendations_by_interests(
    interests: UserInterestRequest,
    limit: int = Query(10, description="Maximum number of recommendations", ge=1, le=50),
    db: Session = Depends(get_db)
) -> List[RecommendationResponse]:
    """
    Get paper recommendations based on user's stated interests (tags and authors).
    """
    try:
        if not interests.tag_ids and not interests.author_names:
            raise HTTPException(status_code=400, detail="At least one tag or author must be specified")
        
        recommendations = recommendation_service.get_recommendations_for_user_interests(
            db=db,
            tag_ids=interests.tag_ids,
            author_names=interests.author_names,
            limit=limit
        )
        
        # Convert to response format
        response = []
        for rec in recommendations:
            paper_dict = {
                "id": rec.paper.id,
                "title": rec.paper.title,
                "authors": rec.paper.authors,
                "year": rec.paper.year,
                "doi": rec.paper.doi,
                "journal": rec.paper.journal,
                "abstract": rec.paper.abstract,
                "summary": rec.paper.summary,
                "notes": rec.paper.notes,
                "pdf_path": rec.paper.pdf_path,
                "external_id": rec.paper.external_id,
                "created_at": rec.paper.created_at,
                "updated_at": rec.paper.updated_at,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in rec.paper.tags]
            }
            
            response.append(RecommendationResponse(
                paper=PaperSchema(**paper_dict),
                score=rec.score,
                reasons=rec.reasons,
                recommendation_type=rec.recommendation_type
            ))
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interest-based recommendation failed: {str(e)}")

@router.get("/stats")
async def get_recommendation_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics about the recommendation system.
    """
    try:
        from ..crud.paper import get_papers_count
        from ..crud.tag import get_all_tags
        
        total_papers = get_papers_count(db)
        total_tags = len(get_all_tags(db))
        
        # Count papers with different attributes for recommendation quality
        papers_with_authors = db.query(func.count(Paper.id)).filter(
            Paper.authors.isnot(None)
        ).scalar()
        
        papers_with_tags = db.query(func.count(Paper.id.distinct())).join(Paper.tags).scalar()
        
        papers_with_abstracts = db.query(func.count(Paper.id)).filter(
            and_(Paper.abstract.isnot(None), Paper.abstract != "")
        ).scalar()
        
        return {
            "total_papers": total_papers,
            "total_tags": total_tags,
            "papers_with_authors": papers_with_authors,
            "papers_with_tags": papers_with_tags,
            "papers_with_abstracts": papers_with_abstracts,
            "recommendation_coverage": {
                "author_based": round((papers_with_authors / total_papers) * 100, 1) if total_papers > 0 else 0,
                "tag_based": round((papers_with_tags / total_papers) * 100, 1) if total_papers > 0 else 0,
                "content_based": round((papers_with_abstracts / total_papers) * 100, 1) if total_papers > 0 else 0
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats query failed: {str(e)}")

@router.get("/test/{paper_id}")
async def test_recommendations(
    paper_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Test endpoint to debug recommendation generation for a specific paper.
    """
    try:
        from ..crud.paper import get_paper
        
        paper = get_paper(db, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Generate different types of recommendations
        author_recs = recommendation_service.get_recommendations_by_author(db, paper_id, 5)
        tag_recs = recommendation_service.get_recommendations_by_tags(db, paper_id, 5)
        
        return {
            "source_paper": {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "tags": [tag.name for tag in paper.tags]
            },
            "author_recommendations": len(author_recs),
            "tag_recommendations": len(tag_recs),
            "author_sample": [
                {
                    "title": rec.paper.title,
                    "score": rec.score,
                    "reasons": rec.reasons
                } for rec in author_recs[:3]
            ],
            "tag_sample": [
                {
                    "title": rec.paper.title,
                    "score": rec.score,
                    "reasons": rec.reasons
                } for rec in tag_recs[:3]
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")