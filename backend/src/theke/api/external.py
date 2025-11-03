from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio

from ..core.database import get_db
from ..schemas.paper import PaperCreate, Paper as PaperSchema
from ..crud.paper import create_paper
from ..services.external_search import (
    search_arxiv,
    search_crossref,
    search_semantic_scholar,
    ExternalPaper
)
from ..services.dblp_service import search_dblp_papers
from ..services.acm_service import search_acm_papers  
from ..services.github_service import search_github_repositories

router = APIRouter()


@router.get("/arxiv/search")
async def search_arxiv_papers(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search papers in arXiv"""
    try:
        results = await search_arxiv(query, max_results)
        return [paper.dict() for paper in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"arXiv search failed: {str(e)}")


@router.get("/crossref/search")
async def search_crossref_papers(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search papers in Crossref"""
    try:
        results = await search_crossref(query, max_results)
        return [paper.dict() for paper in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crossref search failed: {str(e)}")


@router.get("/semantic-scholar/search")
async def search_semantic_scholar_papers(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search papers in Semantic Scholar"""
    try:
        results = await search_semantic_scholar(query, max_results)
        return [paper.dict() for paper in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic Scholar search failed: {str(e)}")


@router.get("/search")
async def search_all_sources(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(5, description="Maximum results per source"),
    sources: List[str] = Query(["arxiv", "crossref", "semantic_scholar"], description="Sources to search")
) -> Dict[str, List[Dict[str, Any]]]:
    """Search papers across multiple external sources"""
    results = {}
    
    # Create search tasks for each requested source
    tasks = []
    if "arxiv" in sources:
        tasks.append(("arxiv", search_arxiv(query, max_results)))
    if "crossref" in sources:
        tasks.append(("crossref", search_crossref(query, max_results)))
    if "semantic_scholar" in sources:
        tasks.append(("semantic_scholar", search_semantic_scholar(query, max_results)))
    
    # Execute searches concurrently
    for source, task in tasks:
        try:
            papers = await task
            results[source] = [paper.dict() for paper in papers]
        except Exception as e:
            results[source] = {"error": str(e)}
    
    return results


@router.post("/add-from-external", response_model=PaperSchema)
async def add_paper_from_external(
    external_paper: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Add a paper to the database from external search results"""
    try:
        # Convert external paper format to our PaperCreate schema
        paper_data = PaperCreate(
            title=external_paper.get("title", ""),
            authors=external_paper.get("authors", []),
            year=external_paper.get("year"),
            doi=external_paper.get("doi"),
            journal=external_paper.get("journal"),
            abstract="",  # Keep abstract empty - generate on demand
            external_id=external_paper.get("external_id")
        )
        
        # Create paper in database
        paper = create_paper(db=db, paper=paper_data)
        return paper
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add paper: {str(e)}")


@router.get("/resolve-citation")
async def resolve_citation_with_search(
    title: str = Query(..., description="Citation title to search for"),
    authors: List[str] = Query(None, description="Authors to help with matching"),
    max_results: int = Query(3, description="Maximum number of suggestions")
) -> List[Dict[str, Any]]:
    """Search for a citation across external sources to help resolve it"""
    
    # Build search query from title and authors
    query_parts = [title]
    if authors:
        query_parts.extend(authors[:2])  # Use first 2 authors
    query = " ".join(query_parts)
    
    try:
        # Search across all sources with smaller result sets
        results = await search_all_sources(query, max_results=max_results, sources=["arxiv", "crossref", "semantic_scholar"])
        
        # Flatten results and score by relevance
        suggestions = []
        for source, papers in results.items():
            if isinstance(papers, list):  # Skip error results
                for paper in papers:
                    paper["source"] = source
                    paper["relevance_score"] = _calculate_relevance_score(
                        paper.get("title", ""), 
                        title, 
                        paper.get("authors", []), 
                        authors or []
                    )
                    suggestions.append(paper)
        
        # Sort by relevance score and return top results
        suggestions.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return suggestions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citation resolution failed: {str(e)}")


# New enhanced search endpoints for PL research

@router.get("/dblp/search")
async def search_dblp_endpoint(
    query: str = Query(..., description="Search query"),
    search_type: str = Query("general", description="Search type: general, title, author, venue"),
    max_results: int = Query(20, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search papers in DBLP (Database Systems and Logic Programming)"""
    try:
        results = await search_dblp_papers(query, max_results, search_type)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DBLP search failed: {str(e)}")


@router.get("/acm-dl/search")
async def search_acm_dl_endpoint(
    query: str = Query(..., description="Search query"),
    search_type: str = Query("general", description="Search type: general, title, author, conference"),
    max_results: int = Query(20, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search papers in ACM Digital Library"""
    try:
        results = await search_acm_papers(query, max_results, search_type)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ACM DL search failed: {str(e)}")


@router.get("/github/search")
async def search_github_endpoint(
    query: str = Query(..., description="Search query"),
    search_type: str = Query("general", description="Search type: general, paper_implementation, author, academic"),
    field: str = Query("pl", description="Academic field for academic search: pl, ml, systems, theory, hci"),
    max_results: int = Query(20, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """Search repositories in GitHub"""
    try:
        results = await search_github_repositories(query, search_type, max_results, field)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub search failed: {str(e)}")


@router.get("/search-all")
async def search_all_enhanced_sources(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum results per source"),
    sources: List[str] = Query(
        ["arxiv", "crossref", "semantic_scholar", "dblp", "acm_dl"], 
        description="Sources to search: arxiv, crossref, semantic_scholar, dblp, acm_dl, github"
    )
) -> Dict[str, List[Dict[str, Any]]]:
    """Enhanced search across multiple external sources including DBLP, ACM DL, and GitHub"""
    results = {}
    
    # Create search tasks for each requested source
    tasks = []
    
    # Original sources
    if "arxiv" in sources:
        tasks.append(("arxiv", search_arxiv(query, max_results)))
    if "crossref" in sources:
        tasks.append(("crossref", search_crossref(query, max_results)))
    if "semantic_scholar" in sources:
        tasks.append(("semantic_scholar", search_semantic_scholar(query, max_results)))
    
    # New PL-focused sources
    if "dblp" in sources:
        tasks.append(("dblp", search_dblp_papers(query, max_results, "general")))
    if "acm_dl" in sources:
        tasks.append(("acm_dl", search_acm_papers(query, max_results, "general")))
    if "github" in sources:
        tasks.append(("github", search_github_repositories(query, "academic", max_results, "pl")))
    
    # Execute searches concurrently
    for source, task in tasks:
        try:
            if source in ["arxiv", "crossref", "semantic_scholar"]:
                papers = await task
                results[source] = [paper.dict() for paper in papers]
            else:
                # New sources already return Dict format
                papers = await task
                results[source] = papers
        except Exception as e:
            results[source] = {"error": str(e)}
    
    return results


@router.get("/pl-focused-search")
async def pl_focused_search(
    query: str = Query(..., description="Search query"),
    include_implementations: bool = Query(True, description="Include GitHub implementations"),
    max_results_per_source: int = Query(10, description="Maximum results per source")
) -> Dict[str, Any]:
    """
    Programming Languages research focused search across academic databases and implementations.
    Specifically designed for PL researchers to find papers, venues, and code implementations.
    """
    try:
        all_results = {}
        
        # Academic paper sources with PL focus
        academic_tasks = [
            ("dblp", search_dblp_papers(query, max_results_per_source, "general")),
            ("acm_dl", search_acm_papers(query, max_results_per_source, "general")),
            ("semantic_scholar", search_semantic_scholar(query, max_results_per_source))
        ]
        
        # Execute academic searches
        for source, task in academic_tasks:
            try:
                if source == "semantic_scholar":
                    papers = await task
                    all_results[source] = [paper.dict() for paper in papers]
                else:
                    papers = await task
                    all_results[source] = papers
            except Exception as e:
                all_results[source] = {"error": str(e)}
        
        # GitHub implementations if requested
        if include_implementations:
            try:
                github_results = await search_github_repositories(query, "academic", max_results_per_source, "pl")
                all_results["github_implementations"] = github_results
            except Exception as e:
                all_results["github_implementations"] = {"error": str(e)}
        
        # Compile summary statistics
        total_papers = 0
        total_implementations = 0
        
        for source, data in all_results.items():
            if isinstance(data, list):
                if source == "github_implementations":
                    total_implementations += len(data)
                else:
                    total_papers += len(data)
        
        return {
            "query": query,
            "summary": {
                "total_papers_found": total_papers,
                "total_implementations_found": total_implementations,
                "sources_searched": list(all_results.keys())
            },
            "results": all_results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PL-focused search failed: {str(e)}")


@router.get("/search-by-venue")
async def search_by_venue(
    venue: str = Query(..., description="Conference or journal name (e.g., POPL, PLDI, ICFP)"),
    year: Optional[int] = Query(None, description="Publication year"),
    max_results: int = Query(50, description="Maximum number of results")
) -> Dict[str, List[Dict[str, Any]]]:
    """Search papers by specific venue across DBLP and ACM DL"""
    results = {}
    
    try:
        # Search DBLP for venue
        dblp_results = await search_dblp_papers(f"venue:{venue}" + (f" year:{year}" if year else ""), max_results, "general")
        results["dblp"] = dblp_results
    except Exception as e:
        results["dblp"] = {"error": str(e)}
    
    try:
        # Search ACM DL for venue
        acm_results = await search_acm_papers(venue, max_results, "conference")
        results["acm_dl"] = acm_results
    except Exception as e:
        results["acm_dl"] = {"error": str(e)}
    
    return results


def _calculate_relevance_score(found_title: str, target_title: str, found_authors: List[str], target_authors: List[str]) -> float:
    """Calculate relevance score between found paper and target citation"""
    score = 0.0
    
    # Title similarity (simple word overlap)
    found_words = set(found_title.lower().split())
    target_words = set(target_title.lower().split())
    if target_words:
        title_overlap = len(found_words & target_words) / len(target_words)
        score += title_overlap * 0.7
    
    # Author similarity
    if target_authors and found_authors:
        found_author_names = set(author.lower() for author in found_authors)
        target_author_names = set(author.lower() for author in target_authors)
        if target_author_names:
            author_overlap = len(found_author_names & target_author_names) / len(target_author_names)
            score += author_overlap * 0.3
    
    return score