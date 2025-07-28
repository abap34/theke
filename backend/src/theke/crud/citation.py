from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..models.citation import Citation
from ..models.paper import Paper
from ..schemas.citation import CitationCreate, CitationUpdate


def get_citation(db: Session, citation_id: int) -> Optional[Citation]:
    """Get a single citation by ID"""
    return db.query(Citation).filter(Citation.id == citation_id).first()


def get_citations(db: Session, skip: int = 0, limit: int = 100) -> List[Citation]:
    """Get all citations"""
    return db.query(Citation).offset(skip).limit(limit).all()


def get_citations_by_paper(db: Session, paper_id: int) -> List[Citation]:
    """Get citations for a specific paper"""
    return db.query(Citation).filter(Citation.citing_paper_id == paper_id).all()


def create_citation(db: Session, citation: CitationCreate) -> Citation:
    """Create a new citation"""
    db_citation = Citation(**citation.model_dump())
    db.add(db_citation)
    db.commit()
    db.refresh(db_citation)
    return db_citation


def update_citation(db: Session, citation_id: int, citation_update: CitationUpdate) -> Optional[Citation]:
    """Update a citation"""
    db_citation = get_citation(db, citation_id)
    if not db_citation:
        return None
    
    update_data = citation_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_citation, field, value)
    
    db.commit()
    db.refresh(db_citation)
    return db_citation


def delete_citation(db: Session, citation_id: int) -> bool:
    """Delete a citation"""
    db_citation = get_citation(db, citation_id)
    if not db_citation:
        return False
    
    db.delete(db_citation)
    db.commit()
    return True


def delete_citations_by_paper(db: Session, paper_id: int) -> int:
    """Delete all citations for a specific paper and return count of deleted citations"""
    citations = db.query(Citation).filter(Citation.citing_paper_id == paper_id).all()
    count = len(citations)
    
    for citation in citations:
        db.delete(citation)
    
    db.commit()
    return count


def get_citation_network(db: Session) -> Dict[str, Any]:
    """Get citation network data for graph visualization"""
    papers = db.query(Paper).all()
    citations = db.query(Citation).all()
    
    # Create nodes
    nodes = []
    for paper in papers:
        nodes.append({
            "id": f"paper_{paper.id}",
            "label": paper.title[:50] + "..." if len(paper.title) > 50 else paper.title,
            "type": "paper",
            "resolved": True,
            "data": {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year
            }
        })
    
    # Add unresolved citation nodes
    unresolved_citations = [c for c in citations if c.cited_paper_id is None]
    for citation in unresolved_citations:
        if citation.cited_title:
            nodes.append({
                "id": f"citation_{citation.id}",
                "label": citation.cited_title[:50] + "..." if len(citation.cited_title) > 50 else citation.cited_title,
                "type": "citation",
                "resolved": False,
                "data": {
                    "id": citation.id,
                    "title": citation.cited_title,
                    "authors": citation.cited_authors,
                    "year": citation.cited_year
                }
            })
    
    # Create edges
    edges = []
    for citation in citations:
        if citation.cited_paper_id:
            # Resolved citation
            edges.append({
                "id": f"edge_{citation.id}",
                "source": f"paper_{citation.citing_paper_id}",
                "target": f"paper_{citation.cited_paper_id}",
                "type": "citation"
            })
        elif citation.cited_title:
            # Unresolved citation
            edges.append({
                "id": f"edge_{citation.id}",
                "source": f"paper_{citation.citing_paper_id}",
                "target": f"citation_{citation.id}",
                "type": "citation"
            })
    
    return {"nodes": nodes, "edges": edges}


def resolve_citation(db: Session, citation_id: int, cited_paper_id: int) -> Optional[Citation]:
    """Resolve an unresolved citation by linking it to an existing paper"""
    citation = get_citation(db, citation_id)
    if not citation:
        return None
    
    cited_paper = db.query(Paper).filter(Paper.id == cited_paper_id).first()
    if not cited_paper:
        return None
    
    citation.cited_paper_id = cited_paper_id
    citation.status = "resolved"
    
    db.commit()
    db.refresh(citation)
    return citation