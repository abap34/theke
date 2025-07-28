import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import re

from ..core.config import settings


class ExternalPaper(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    external_id: Optional[str] = None
    source: str
    url: Optional[str] = None


async def search_arxiv(query: str, max_results: int = 10) -> List[ExternalPaper]:
    """Search papers in arXiv"""
    url = f"{settings.ARXIV_BASE_URL}"
    params = {
        'search_query': f'all:{query}',
        'start': 0,
        'max_results': max_results,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"arXiv API error: {response.status}")
            
            content = await response.text()
            return _parse_arxiv_response(content)


def _parse_arxiv_response(xml_content: str) -> List[ExternalPaper]:
    """Parse arXiv XML response"""
    try:
        root = ET.fromstring(xml_content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', namespace):
            title_elem = entry.find('atom:title', namespace)
            title = title_elem.text.strip() if title_elem is not None else ""
            
            # Parse authors
            authors = []
            for author in entry.findall('atom:author', namespace):
                name_elem = author.find('atom:name', namespace)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            
            # Parse published date for year
            published_elem = entry.find('atom:published', namespace)
            year = None
            if published_elem is not None:
                year_match = re.search(r'(\d{4})', published_elem.text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Parse arXiv ID
            id_elem = entry.find('atom:id', namespace)
            external_id = None
            url = None
            if id_elem is not None:
                arxiv_url = id_elem.text
                external_id = arxiv_url.split('/')[-1]  # Extract arXiv ID
                url = arxiv_url
            
            # Parse abstract
            summary_elem = entry.find('atom:summary', namespace)
            abstract = summary_elem.text.strip() if summary_elem is not None else ""
            
            if title:  # Only add if we have a title
                paper = ExternalPaper(
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    external_id=external_id,
                    source="arxiv",
                    url=url
                )
                papers.append(paper)
        
        return papers
        
    except ET.ParseError as e:
        raise Exception(f"Failed to parse arXiv response: {str(e)}")


async def search_crossref(query: str, max_results: int = 10) -> List[ExternalPaper]:
    """Search papers in Crossref"""
    url = f"{settings.CROSSREF_BASE_URL}"
    params = {
        'query': query,
        'rows': max_results,
        'sort': 'relevance',
        'order': 'desc'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Crossref API error: {response.status}")
            
            data = await response.json()
            return _parse_crossref_response(data)


def _parse_crossref_response(data: Dict[str, Any]) -> List[ExternalPaper]:
    """Parse Crossref JSON response"""
    papers = []
    items = data.get('message', {}).get('items', [])
    
    for item in items:
        # Parse title
        title_parts = item.get('title', [])
        title = title_parts[0] if title_parts else ""
        
        # Parse authors
        authors = []
        author_data = item.get('author', [])
        for author in author_data:
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                full_name = f"{given} {family}".strip()
                authors.append(full_name)
        
        # Parse year
        year = None
        published = item.get('published-print') or item.get('published-online')
        if published and 'date-parts' in published:
            date_parts = published['date-parts'][0]
            if date_parts:
                year = date_parts[0]
        
        # Parse DOI
        doi = item.get('DOI')
        
        # Parse journal
        journal = None
        container_title = item.get('container-title', [])
        if container_title:
            journal = container_title[0]
        
        # Parse abstract (if available)
        abstract = item.get('abstract', "")
        
        if title:  # Only add if we have a title
            paper = ExternalPaper(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                journal=journal,
                abstract=abstract,
                source="crossref",
                url=f"https://doi.org/{doi}" if doi else None
            )
            papers.append(paper)
    
    return papers


async def search_semantic_scholar(query: str, max_results: int = 10) -> List[ExternalPaper]:
    """Search papers in Semantic Scholar"""
    url = f"{settings.SEMANTIC_SCHOLAR_BASE_URL}/paper/search"
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,authors,year,abstract,journal,externalIds,url'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Semantic Scholar API error: {response.status}")
            
            data = await response.json()
            return _parse_semantic_scholar_response(data)


def _parse_semantic_scholar_response(data: Dict[str, Any]) -> List[ExternalPaper]:
    """Parse Semantic Scholar JSON response"""
    papers = []
    papers_data = data.get('data', [])
    
    for item in papers_data:
        title = item.get('title', '')
        
        # Parse authors
        authors = []
        author_data = item.get('authors', [])
        for author in author_data:
            name = author.get('name', '')
            if name:
                authors.append(name)
        
        year = item.get('year')
        abstract = item.get('abstract', '')
        
        # Parse journal
        journal_data = item.get('journal')
        journal = journal_data.get('name') if journal_data else None
        
        # Parse external IDs for DOI and arXiv
        external_ids = item.get('externalIds', {})
        doi = external_ids.get('DOI')
        arxiv_id = external_ids.get('ArXiv')
        
        # Use the most relevant external ID
        external_id = arxiv_id if arxiv_id else doi
        
        url = item.get('url')
        
        if title:  # Only add if we have a title
            paper = ExternalPaper(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                journal=journal,
                abstract=abstract,
                external_id=external_id,
                source="semantic_scholar",
                url=url
            )
            papers.append(paper)
    
    return papers


async def search_by_doi(doi: str) -> Optional[ExternalPaper]:
    """Search for a paper by DOI across multiple sources"""
    # Try Crossref first (most likely to have DOI)
    try:
        results = await search_crossref(f'doi:{doi}', max_results=1)
        if results:
            return results[0]
    except Exception:
        pass
    
    # Try Semantic Scholar
    try:
        results = await search_semantic_scholar(doi, max_results=1)
        if results:
            return results[0]
    except Exception:
        pass
    
    return None


async def search_by_title_and_authors(title: str, authors: List[str], max_results: int = 5) -> List[ExternalPaper]:
    """Search for papers by title and authors across all sources"""
    # Build search query
    query_parts = [title]
    if authors:
        query_parts.extend(authors[:3])  # Use first 3 authors
    query = " ".join(query_parts)
    
    # Search all sources concurrently
    tasks = [
        search_arxiv(query, max_results),
        search_crossref(query, max_results),
        search_semantic_scholar(query, max_results)
    ]
    
    all_results = []
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
    except Exception:
        pass
    
    return all_results[:max_results]