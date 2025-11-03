"""
Auto-tagging API endpoints.
Provides automatic tag suggestions for papers based on content analysis.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..core.database import get_db
from ..crud.paper import get_paper
from ..crud.tag import get_or_create_tag
from ..services.auto_tagging_service import AutoTaggingService, TagSuggestion
from ..schemas.tag import TagCreate

router = APIRouter()

# Pydantic models for requests/responses
class TagSuggestionResponse(BaseModel):
    tag_name: str
    confidence: float
    reasons: List[str]
    category: str

class AutoTagRequest(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    existing_keywords: Optional[List[str]] = None

class ApplyAutoTagsRequest(BaseModel):
    tag_names: List[str]

# Initialize auto-tagging service
auto_tagging_service = AutoTaggingService()

@router.post("/suggest/{paper_id}")
async def suggest_tags_for_paper(
    paper_id: int,
    db: Session = Depends(get_db)
) -> List[TagSuggestionResponse]:
    """
    Suggest tags for a specific paper based on its metadata.
    """
    try:
        # Get paper from database
        paper = get_paper(db=db, paper_id=paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Generate tag suggestions
        suggestions = auto_tagging_service.suggest_tags(
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors,
            venue=paper.journal
        )
        
        # Convert to response format
        response_suggestions = []
        for suggestion in suggestions:
            response_suggestions.append(TagSuggestionResponse(
                tag_name=suggestion.tag_name,
                confidence=suggestion.confidence,
                reasons=suggestion.reasons,
                category=suggestion.category
            ))
        
        return response_suggestions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag suggestion failed: {str(e)}")

@router.post("/suggest-from-content")
async def suggest_tags_from_content(
    request: AutoTagRequest
) -> List[TagSuggestionResponse]:
    """
    Suggest tags based on provided content without needing an existing paper.
    """
    try:
        suggestions = auto_tagging_service.suggest_tags(
            title=request.title,
            abstract=request.abstract,
            authors=request.authors,
            venue=request.venue,
            existing_keywords=request.existing_keywords
        )
        
        # Convert to response format
        response_suggestions = []
        for suggestion in suggestions:
            response_suggestions.append(TagSuggestionResponse(
                tag_name=suggestion.tag_name,
                confidence=suggestion.confidence,
                reasons=suggestion.reasons,
                category=suggestion.category
            ))
        
        return response_suggestions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag suggestion failed: {str(e)}")

@router.post("/apply/{paper_id}")
async def apply_auto_tags(
    paper_id: int,
    request: ApplyAutoTagsRequest,
    db: Session = Depends(get_db)
):
    """
    Apply automatically suggested tags to a paper.
    Creates tags if they don't exist and associates them with the paper.
    """
    try:
        # Get paper from database
        paper = get_paper(db=db, paper_id=paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        applied_tags = []
        
        for tag_name in request.tag_names:
            # Create tag if it doesn't exist, or get existing tag
            tag = get_or_create_tag(db=db, tag_data=TagCreate(
                name=tag_name,
                color="#3B82F6"  # Default blue color
            ))
            
            # Associate tag with paper if not already associated
            if tag not in paper.tags:
                paper.tags.append(tag)
                applied_tags.append(tag_name)
        
        db.commit()
        
        return {
            "success": True,
            "applied_tags": applied_tags,
            "message": f"Applied {len(applied_tags)} tags to paper"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to apply tags: {str(e)}")

@router.get("/presets")
async def get_preset_tags() -> Dict[str, List[str]]:
    """
    Get predefined tag categories for UI selection.
    """
    try:
        presets = auto_tagging_service.get_preset_tags()
        return presets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preset tags: {str(e)}")

@router.post("/bulk-suggest")
async def bulk_suggest_tags(
    paper_ids: List[int],
    db: Session = Depends(get_db)
) -> Dict[int, List[TagSuggestionResponse]]:
    """
    Suggest tags for multiple papers at once.
    """
    try:
        results = {}
        
        for paper_id in paper_ids:
            # Get paper from database
            paper = get_paper(db=db, paper_id=paper_id)
            if not paper:
                results[paper_id] = {"error": "Paper not found"}
                continue
            
            # Generate suggestions
            suggestions = auto_tagging_service.suggest_tags(
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                venue=paper.journal
            )
            
            # Convert to response format
            response_suggestions = []
            for suggestion in suggestions:
                response_suggestions.append(TagSuggestionResponse(
                    tag_name=suggestion.tag_name,
                    confidence=suggestion.confidence,
                    reasons=suggestion.reasons,
                    category=suggestion.category
                ))
            
            results[paper_id] = response_suggestions
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk tag suggestion failed: {str(e)}")

@router.get("/categories")
async def get_tag_categories() -> Dict[str, Dict[str, Any]]:
    """
    Get information about tag categories and their descriptions.
    """
    try:
        categories = {
            "pl": {
                "name": "Programming Languages",
                "description": "Type systems, compilers, formal methods, language design",
                "color": "#8B5CF6"
            },
            "ml": {
                "name": "Machine Learning",
                "description": "Deep learning, neural networks, NLP, computer vision",
                "color": "#10B981"
            },
            "systems": {
                "name": "Systems",
                "description": "Operating systems, distributed systems, databases, networking",
                "color": "#F59E0B"
            },
            "theory": {
                "name": "Theory",
                "description": "Algorithms, complexity theory, cryptography",
                "color": "#EF4444"
            },
            "hci": {
                "name": "Human-Computer Interaction",
                "description": "User interfaces, visualization, usability",
                "color": "#06B6D4"
            }
        }
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.post("/suggest-by-venue")
async def suggest_tags_by_venue(
    venue: str,
    confidence_threshold: float = 0.5
) -> List[TagSuggestionResponse]:
    """
    Suggest tags based on venue/conference name alone.
    Useful for batch processing papers from specific venues.
    """
    try:
        suggestions = auto_tagging_service._analyze_venue(venue)
        
        # Filter by confidence threshold
        filtered_suggestions = [s for s in suggestions if s.confidence >= confidence_threshold]
        
        # Convert to response format
        response_suggestions = []
        for suggestion in filtered_suggestions:
            response_suggestions.append(TagSuggestionResponse(
                tag_name=suggestion.tag_name,
                confidence=suggestion.confidence,
                reasons=suggestion.reasons,
                category=suggestion.category
            ))
        
        return response_suggestions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Venue-based tag suggestion failed: {str(e)}")

@router.get("/statistics")
async def get_tagging_statistics(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics about current tagging in the system.
    """
    try:
        # Get total papers and tagged papers count
        from ..crud.paper import get_papers_count, get_tagged_papers_count
        from ..crud.tag import get_all_tags
        
        total_papers = get_papers_count(db)
        tagged_papers = get_tagged_papers_count(db)
        all_tags = get_all_tags(db)
        
        # Count tags by category (simplified estimation)
        category_counts = {
            "pl": 0,
            "ml": 0, 
            "systems": 0,
            "theory": 0,
            "hci": 0,
            "other": 0
        }
        
        for tag in all_tags:
            tag_name = tag.name.lower()
            categorized = False
            
            for category, keywords in auto_tagging_service.all_keywords.items():
                if any(keyword in tag_name for keyword in keywords["keywords"][:3]):
                    category_name = auto_tagging_service._determine_category(category)
                    if category_name in category_counts:
                        category_counts[category_name] += 1
                        categorized = True
                        break
            
            if not categorized:
                category_counts["other"] += 1
        
        return {
            "total_papers": total_papers,
            "tagged_papers": tagged_papers,
            "untagged_papers": total_papers - tagged_papers,
            "tagging_percentage": round((tagged_papers / total_papers) * 100, 1) if total_papers > 0 else 0,
            "total_tags": len(all_tags),
            "tags_by_category": category_counts
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")