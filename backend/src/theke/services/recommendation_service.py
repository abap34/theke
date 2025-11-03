"""
Recommendation service for suggesting related papers based on various criteria.
Provides recommendations by author, tags, citations, and content similarity.
"""

from typing import List, Dict, Optional, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from collections import defaultdict, Counter
import logging
from dataclasses import dataclass

from ..models.paper import Paper
from ..models.tag import Tag
from ..crud.paper import get_paper

logger = logging.getLogger(__name__)

@dataclass
class RecommendationResult:
    """Represents a paper recommendation with score and reasoning."""
    paper: Paper
    score: float
    reasons: List[str]  # Why this paper was recommended
    recommendation_type: str  # e.g., "author_based", "tag_based", "citation_based"

class RecommendationService:
    """Service for generating paper recommendations."""
    
    def __init__(self):
        pass
    
    def get_related_papers(self, 
                          db: Session, 
                          paper_id: int, 
                          limit: int = 10,
                          include_types: List[str] = None) -> List[RecommendationResult]:
        """
        Get papers related to the given paper using multiple strategies.
        
        Args:
            db: Database session
            paper_id: ID of the reference paper
            limit: Maximum number of recommendations
            include_types: Types of recommendations to include 
                         (author_based, tag_based, citation_based, content_based)
        
        Returns:
            List of RecommendationResult objects
        """
        if include_types is None:
            include_types = ["author_based", "tag_based", "citation_based"]
        
        source_paper = get_paper(db, paper_id)
        if not source_paper:
            return []
        
        recommendations = []
        
        # Author-based recommendations
        if "author_based" in include_types:
            author_recs = self._get_author_based_recommendations(db, source_paper, limit // 2)
            recommendations.extend(author_recs)
        
        # Tag-based recommendations  
        if "tag_based" in include_types:
            tag_recs = self._get_tag_based_recommendations(db, source_paper, limit // 2)
            recommendations.extend(tag_recs)
        
        # Citation-based recommendations
        if "citation_based" in include_types:
            citation_recs = self._get_citation_based_recommendations(db, source_paper, limit // 2)
            recommendations.extend(citation_recs)
        
        # Content-based recommendations (basic keyword matching)
        if "content_based" in include_types:
            content_recs = self._get_content_based_recommendations(db, source_paper, limit // 2)
            recommendations.extend(content_recs)
        
        # Remove the source paper itself and deduplicate
        recommendations = self._deduplicate_and_score(recommendations, source_paper.id)
        
        # Sort by score and limit results
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:limit]
    
    def get_recommendations_by_author(self, 
                                    db: Session, 
                                    paper_id: int, 
                                    limit: int = 10) -> List[RecommendationResult]:
        """Get recommendations based on paper authors."""
        source_paper = get_paper(db, paper_id)
        if not source_paper:
            return []
        
        return self._get_author_based_recommendations(db, source_paper, limit)
    
    def get_recommendations_by_tags(self, 
                                  db: Session, 
                                  paper_id: int, 
                                  limit: int = 10) -> List[RecommendationResult]:
        """Get recommendations based on paper tags."""
        source_paper = get_paper(db, paper_id)
        if not source_paper:
            return []
        
        return self._get_tag_based_recommendations(db, source_paper, limit)
    
    def get_popular_papers(self, 
                          db: Session, 
                          limit: int = 10,
                          time_range_days: Optional[int] = None) -> List[Paper]:
        """Get popular papers (most tagged, most recent, etc.)."""
        query = db.query(Paper)
        
        # Filter by time range if specified
        if time_range_days:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
            query = query.filter(Paper.created_at >= cutoff_date)
        
        # Sort by number of tags (popularity proxy) and recent activity
        query = query.outerjoin(Paper.tags).group_by(Paper.id).order_by(
            func.count(Tag.id).desc(),
            Paper.updated_at.desc()
        )
        
        return query.limit(limit).all()
    
    def get_recommendations_for_user_interests(self,
                                             db: Session,
                                             tag_ids: List[int],
                                             author_names: List[str],
                                             limit: int = 10) -> List[RecommendationResult]:
        """Get recommendations based on user's stated interests."""
        recommendations = []
        
        # Tag-based recommendations
        if tag_ids:
            tag_papers = db.query(Paper).join(Paper.tags).filter(
                Tag.id.in_(tag_ids)
            ).limit(limit * 2).all()
            
            for paper in tag_papers:
                shared_tags = set(tag.id for tag in paper.tags) & set(tag_ids)
                score = len(shared_tags) / len(tag_ids) * 0.8  # Tag match score
                
                recommendations.append(RecommendationResult(
                    paper=paper,
                    score=score,
                    reasons=[f"Matches {len(shared_tags)} of your interested tags"],
                    recommendation_type="user_interest"
                ))
        
        # Author-based recommendations
        if author_names:
            for author in author_names:
                author_term = f"%{author}%"
                author_papers = db.query(Paper).filter(
                    text("JSON_EXTRACT(authors, '$') LIKE :author").params(author=author_term)
                ).limit(10).all()
                
                for paper in author_papers:
                    recommendations.append(RecommendationResult(
                        paper=paper,
                        score=0.7,
                        reasons=[f"By author of interest: {author}"],
                        recommendation_type="user_interest"
                    ))
        
        # Deduplicate and sort
        recommendations = self._deduplicate_and_score(recommendations)
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations[:limit]
    
    def _get_author_based_recommendations(self, 
                                        db: Session, 
                                        source_paper: Paper, 
                                        limit: int) -> List[RecommendationResult]:
        """Get recommendations based on shared authors."""
        if not source_paper.authors:
            return []
        
        recommendations = []
        
        # For each author in the source paper, find other papers
        for author in source_paper.authors:
            author_term = f"%{author}%"
            
            # Find papers by this author
            author_papers = db.query(Paper).filter(
                and_(
                    Paper.id != source_paper.id,
                    text("JSON_EXTRACT(authors, '$') LIKE :author").params(author=author_term)
                )
            ).limit(limit).all()
            
            for paper in author_papers:
                # Calculate author overlap score
                shared_authors = set(source_paper.authors) & set(paper.authors or [])
                score = len(shared_authors) / len(source_paper.authors) * 0.9  # Author similarity score
                
                reasons = [f"Shared author(s): {', '.join(shared_authors)}"]
                
                recommendations.append(RecommendationResult(
                    paper=paper,
                    score=score,
                    reasons=reasons,
                    recommendation_type="author_based"
                ))
        
        return recommendations
    
    def _get_tag_based_recommendations(self, 
                                     db: Session, 
                                     source_paper: Paper, 
                                     limit: int) -> List[RecommendationResult]:
        """Get recommendations based on shared tags."""
        if not source_paper.tags:
            return []
        
        source_tag_ids = [tag.id for tag in source_paper.tags]
        
        # Find papers that share tags
        tag_papers = db.query(Paper).join(Paper.tags).filter(
            and_(
                Paper.id != source_paper.id,
                Tag.id.in_(source_tag_ids)
            )
        ).limit(limit * 2).all()  # Get more to account for filtering
        
        recommendations = []
        for paper in tag_papers:
            paper_tag_ids = [tag.id for tag in paper.tags]
            shared_tag_ids = set(source_tag_ids) & set(paper_tag_ids)
            
            if shared_tag_ids:
                # Calculate tag similarity score
                score = len(shared_tag_ids) / len(source_tag_ids) * 0.8
                
                # Get shared tag names for reasons
                shared_tag_names = [tag.name for tag in paper.tags if tag.id in shared_tag_ids]
                reasons = [f"Shared tag(s): {', '.join(shared_tag_names)}"]
                
                recommendations.append(RecommendationResult(
                    paper=paper,
                    score=score,
                    reasons=reasons,
                    recommendation_type="tag_based"
                ))
        
        return recommendations
    
    def _get_citation_based_recommendations(self, 
                                          db: Session, 
                                          source_paper: Paper, 
                                          limit: int) -> List[RecommendationResult]:
        """Get recommendations based on citation relationships."""
        # This is a simplified version - in a full implementation, you'd have
        # a more sophisticated citation graph analysis
        
        recommendations = []
        
        # Find papers with similar titles (potential citations)
        if source_paper.title:
            title_words = source_paper.title.lower().split()
            key_words = [word for word in title_words if len(word) > 4][:3]  # Get key words
            
            if key_words:
                # Build search query for title similarity
                title_conditions = []
                params = {}
                for i, word in enumerate(key_words):
                    param_name = f"word_{i}"
                    title_conditions.append(f"Paper.title LIKE :{param_name}")
                    params[param_name] = f"%{word}%"
                
                if title_conditions:
                    similar_papers = db.query(Paper).filter(
                        and_(
                            Paper.id != source_paper.id,
                            or_(*[text(condition) for condition in title_conditions])
                        )
                    ).params(**params).limit(limit).all()
                    
                    for paper in similar_papers:
                        # Simple title similarity score
                        paper_words = set(paper.title.lower().split()) if paper.title else set()
                        source_words = set(source_paper.title.lower().split())
                        overlap = len(paper_words & source_words)
                        
                        if overlap >= 2:  # At least 2 words in common
                            score = min(overlap / len(source_words), 0.7)  # Cap at 0.7 for citation-based
                            
                            recommendations.append(RecommendationResult(
                                paper=paper,
                                score=score,
                                reasons=[f"Similar title (potential citation)"],
                                recommendation_type="citation_based"
                            ))
        
        return recommendations
    
    def _get_content_based_recommendations(self, 
                                         db: Session, 
                                         source_paper: Paper, 
                                         limit: int) -> List[RecommendationResult]:
        """Get recommendations based on content similarity."""
        recommendations = []
        
        # Extract keywords from abstract and title
        content = ""
        if source_paper.title:
            content += source_paper.title + " "
        if source_paper.abstract:
            content += source_paper.abstract + " "
        if source_paper.summary:
            content += source_paper.summary
        
        if not content.strip():
            return []
        
        # Extract key terms (simple keyword extraction)
        words = content.lower().split()
        # Filter out common words and get meaningful terms
        key_terms = [word for word in words if len(word) > 5 and word.isalpha()][:5]
        
        if key_terms:
            # Find papers with similar content
            search_conditions = []
            params = {}
            for i, term in enumerate(key_terms):
                param_name = f"term_{i}"
                search_conditions.append(
                    f"(Paper.title LIKE :{param_name} OR Paper.abstract LIKE :{param_name} OR Paper.summary LIKE :{param_name})"
                )
                params[param_name] = f"%{term}%"
            
            if search_conditions:
                similar_papers = db.query(Paper).filter(
                    and_(
                        Paper.id != source_paper.id,
                        or_(*[text(condition) for condition in search_conditions])
                    )
                ).params(**params).limit(limit).all()
                
                for paper in similar_papers:
                    # Calculate content similarity score (very basic)
                    paper_content = ""
                    if paper.title:
                        paper_content += paper.title + " "
                    if paper.abstract:
                        paper_content += paper.abstract + " "
                    if paper.summary:
                        paper_content += paper.summary
                    
                    paper_words = set(paper_content.lower().split())
                    source_words = set(content.lower().split())
                    overlap = len(paper_words & source_words)
                    
                    if overlap >= 3:
                        score = min(overlap / 20, 0.6)  # Content-based score cap
                        
                        recommendations.append(RecommendationResult(
                            paper=paper,
                            score=score,
                            reasons=["Similar content/keywords"],
                            recommendation_type="content_based"
                        ))
        
        return recommendations
    
    def _deduplicate_and_score(self, 
                              recommendations: List[RecommendationResult],
                              exclude_paper_id: Optional[int] = None) -> List[RecommendationResult]:
        """Remove duplicates and combine scores for papers recommended by multiple methods."""
        paper_recommendations = defaultdict(list)
        
        # Group by paper ID
        for rec in recommendations:
            if exclude_paper_id and rec.paper.id == exclude_paper_id:
                continue
            paper_recommendations[rec.paper.id].append(rec)
        
        # Combine scores and reasons for duplicate papers
        final_recommendations = []
        for paper_id, recs in paper_recommendations.items():
            if len(recs) == 1:
                final_recommendations.append(recs[0])
            else:
                # Combine multiple recommendations for same paper
                combined_score = sum(rec.score for rec in recs) / len(recs)  # Average score
                combined_score = min(combined_score * 1.1, 1.0)  # Slight boost for multiple matches
                
                combined_reasons = []
                recommendation_types = []
                for rec in recs:
                    combined_reasons.extend(rec.reasons)
                    recommendation_types.append(rec.recommendation_type)
                
                final_recommendations.append(RecommendationResult(
                    paper=recs[0].paper,  # Use the first paper instance
                    score=combined_score,
                    reasons=list(set(combined_reasons)),  # Remove duplicate reasons
                    recommendation_type=", ".join(set(recommendation_types))
                ))
        
        return final_recommendations


# Global service instance
recommendation_service = RecommendationService()