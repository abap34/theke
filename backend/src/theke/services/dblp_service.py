"""
DBLP (Database Systems and Logic Programming) search service.
DBLP is a comprehensive computer science bibliography database,
particularly strong for programming languages and systems research.

API Documentation: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class DBLPPaper:
    """Represents a paper from DBLP search results."""
    dblp_key: str
    title: str
    authors: List[str]
    year: Optional[int]
    venue: Optional[str]  # Conference/journal name
    venue_type: str  # "conf" or "journal"
    url: Optional[str]  # DBLP URL
    doi: Optional[str]
    pages: Optional[str]
    volume: Optional[str]
    number: Optional[str]
    ee: Optional[str]  # Electronic edition URL
    
    def to_external_paper(self) -> Dict[str, Any]:
        """Convert to standard ExternalPaper format."""
        return {
            "external_id": self.dblp_key,
            "source": "dblp",
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.venue,
            "abstract": None,  # DBLP doesn't provide abstracts
            "doi": self.doi,
            "url": self.url,
            "metadata": {
                "venue_type": self.venue_type,
                "pages": self.pages,
                "volume": self.volume,
                "number": self.number,
                "electronic_edition": self.ee,
                "dblp_key": self.dblp_key
            }
        }

class DBLPService:
    """Service for searching DBLP computer science bibliography."""
    
    BASE_URL = "https://dblp.org"
    SEARCH_URL = f"{BASE_URL}/search/publ/api"
    MAX_RESULTS = 1000  # DBLP's maximum
    
    # PL-relevant conferences and journals for focused searches
    PL_VENUES = {
        # Major PL conferences
        "popl", "pldi", "icfp", "oopsla", "ecoop", "esop", "cc", "cgo",
        "ppdp", "pepm", "dls", "gpce", "sle", "onward",
        # Systems conferences with PL content
        "asplos", "osdi", "sosp", "eurosys", "pact",
        # Theory conferences
        "lics", "csl", "icalp", "focs", "stoc",
        # Security with PL
        "oakland", "ccs", "ndss", "usenix-security",
        # Software engineering with PL
        "icse", "fse", "ase", "issta",
        # Journals
        "toplas", "jfp", "scp", "tcs", "pacmpl"
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_by_title(self, title: str, max_results: int = 20) -> List[DBLPPaper]:
        """Search DBLP by paper title."""
        try:
            query = f"title:{title}"
            return await self._search_dblp(query, max_results)
        except Exception as e:
            logger.error(f"DBLP title search failed for '{title}': {e}")
            return []
    
    async def search_by_author(self, author: str, max_results: int = 50) -> List[DBLPPaper]:
        """Search DBLP by author name."""
        try:
            query = f"author:{author}"
            return await self._search_dblp(query, max_results)
        except Exception as e:
            logger.error(f"DBLP author search failed for '{author}': {e}")
            return []
    
    async def search_by_venue(self, venue: str, year: Optional[int] = None, max_results: int = 100) -> List[DBLPPaper]:
        """Search DBLP by conference or journal venue."""
        try:
            if year:
                query = f"venue:{venue} year:{year}"
            else:
                query = f"venue:{venue}"
            return await self._search_dblp(query, max_results)
        except Exception as e:
            logger.error(f"DBLP venue search failed for '{venue}': {e}")
            return []
    
    async def search_general(self, query: str, max_results: int = 20, pl_focus: bool = True) -> List[DBLPPaper]:
        """
        General search across DBLP with optional PL focus.
        
        Args:
            query: Search terms
            max_results: Maximum results to return
            pl_focus: If True, prioritize PL-relevant venues
        """
        try:
            results = await self._search_dblp(query, max_results * 2 if pl_focus else max_results)
            
            if pl_focus:
                # Filter and prioritize PL-relevant papers
                pl_papers = []
                other_papers = []
                
                for paper in results:
                    if self._is_pl_relevant(paper):
                        pl_papers.append(paper)
                    else:
                        other_papers.append(paper)
                
                # Return PL papers first, then others, up to max_results
                return (pl_papers + other_papers)[:max_results]
            
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"DBLP general search failed for '{query}': {e}")
            return []
    
    async def get_recent_pl_papers(self, days: int = 30, max_results: int = 50) -> List[DBLPPaper]:
        """Get recent papers from major PL venues."""
        try:
            from datetime import datetime, timedelta
            current_year = datetime.now().year
            results = []
            
            # Search recent years for major PL venues
            for venue in ["popl", "pldi", "icfp", "oopsla", "ecoop"]:
                for year in [current_year, current_year - 1]:
                    venue_papers = await self.search_by_venue(venue, year, 20)
                    results.extend(venue_papers)
            
            # Sort by year descending and return most recent
            results.sort(key=lambda p: p.year or 0, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"DBLP recent PL papers search failed: {e}")
            return []
    
    def _is_pl_relevant(self, paper: DBLPPaper) -> bool:
        """Check if a paper is relevant to programming languages research."""
        if not paper.venue:
            return False
        
        venue_lower = paper.venue.lower()
        
        # Check against known PL venues
        for pl_venue in self.PL_VENUES:
            if pl_venue in venue_lower:
                return True
        
        # Check title for PL keywords
        title_lower = paper.title.lower()
        pl_keywords = [
            "programming language", "type system", "compiler", "interpreter",
            "static analysis", "program analysis", "formal verification",
            "lambda calculus", "functional programming", "object-oriented",
            "memory management", "garbage collection", "runtime system",
            "program synthesis", "domain-specific language", "dsl",
            "abstract interpretation", "model checking", "proof assistant"
        ]
        
        for keyword in pl_keywords:
            if keyword in title_lower:
                return True
        
        return False
    
    async def _search_dblp(self, query: str, max_results: int) -> List[DBLPPaper]:
        """Execute search against DBLP API."""
        if not self.session:
            raise RuntimeError("DBLPService must be used as async context manager")
        
        # Encode query for URL
        encoded_query = quote_plus(query)
        
        params = {
            "q": encoded_query,
            "format": "xml",
            "h": min(max_results, self.MAX_RESULTS),
            "c": 0  # Start from first result
        }
        
        url = self.SEARCH_URL
        logger.info(f"Searching DBLP: {query}")
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"DBLP API error: {response.status}")
                    return []
                
                xml_content = await response.text()
                return self._parse_dblp_xml(xml_content)
                
        except asyncio.TimeoutError:
            logger.error("DBLP search timeout")
            return []
        except Exception as e:
            logger.error(f"DBLP search error: {e}")
            return []
    
    def _parse_dblp_xml(self, xml_content: str) -> List[DBLPPaper]:
        """Parse DBLP XML response into DBLPPaper objects."""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # DBLP XML structure: result -> hits -> hit -> info
            hits = root.find(".//hits")
            if hits is None:
                return papers
            
            for hit in hits.findall("hit"):
                info = hit.find("info")
                if info is None:
                    continue
                
                try:
                    paper = self._parse_dblp_paper(info)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing DBLP paper: {e}")
                    continue
            
        except ET.ParseError as e:
            logger.error(f"DBLP XML parse error: {e}")
        
        return papers
    
    def _parse_dblp_paper(self, info_element) -> Optional[DBLPPaper]:
        """Parse individual paper from DBLP XML info element."""
        try:
            # Extract basic info
            title = self._get_xml_text(info_element, "title")
            if not title:
                return None
            
            # Clean up title (remove extra whitespace)
            title = re.sub(r'\s+', ' ', title.strip())
            
            # Extract authors
            authors = []
            for author_elem in info_element.findall("authors/author"):
                author_name = author_elem.text
                if author_name:
                    authors.append(author_name.strip())
            
            # Extract venue information
            venue = self._get_xml_text(info_element, "venue")
            venue_type = info_element.get("type", "unknown")
            
            # Extract year
            year_str = self._get_xml_text(info_element, "year")
            year = int(year_str) if year_str and year_str.isdigit() else None
            
            # Extract URLs and identifiers
            url = self._get_xml_text(info_element, "url")
            doi = self._get_xml_text(info_element, "doi")
            ee = self._get_xml_text(info_element, "ee")  # Electronic edition
            
            # Extract publication details
            pages = self._get_xml_text(info_element, "pages")
            volume = self._get_xml_text(info_element, "volume")
            number = self._get_xml_text(info_element, "number")
            
            # Generate DBLP key from URL if available
            dblp_key = ""
            if url:
                # Extract key from DBLP URL pattern
                key_match = re.search(r'dblp\.org/db/([^.]+\.html)', url)
                if key_match:
                    dblp_key = key_match.group(1).replace('.html', '').replace('/', '-')
            
            if not dblp_key:
                # Generate fallback key
                first_author = authors[0].split()[-1] if authors else "unknown"
                year_str = str(year) if year else "nodate"
                dblp_key = f"{first_author}-{year_str}-{hash(title) % 10000}"
            
            return DBLPPaper(
                dblp_key=dblp_key,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                venue_type=venue_type,
                url=url,
                doi=doi,
                pages=pages,
                volume=volume,
                number=number,
                ee=ee
            )
            
        except Exception as e:
            logger.error(f"Error parsing DBLP paper element: {e}")
            return None
    
    def _get_xml_text(self, element, tag: str) -> Optional[str]:
        """Safely extract text from XML element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None


async def search_dblp_papers(query: str, max_results: int = 20, search_type: str = "general") -> List[Dict[str, Any]]:
    """
    Convenience function for searching DBLP papers.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        search_type: Type of search ("general", "title", "author", "venue")
    
    Returns:
        List of papers in ExternalPaper format
    """
    async with DBLPService() as dblp:
        if search_type == "title":
            papers = await dblp.search_by_title(query, max_results)
        elif search_type == "author":
            papers = await dblp.search_by_author(query, max_results)
        elif search_type == "venue":
            papers = await dblp.search_by_venue(query, max_results=max_results)
        else:  # general
            papers = await dblp.search_general(query, max_results)
    
    return [paper.to_external_paper() for paper in papers]


# Example usage and testing
async def main():
    """Test DBLP service functionality."""
    async with DBLPService() as dblp:
        # Test general search
        print("Testing general search for 'type systems'...")
        results = await dblp.search_general("type systems", max_results=5)
        for paper in results[:3]:
            print(f"- {paper.title} ({paper.year}) - {paper.venue}")
        
        # Test author search
        print("\nTesting author search for 'Philip Wadler'...")
        results = await dblp.search_by_author("Philip Wadler", max_results=5)
        for paper in results[:3]:
            print(f"- {paper.title} ({paper.year}) - {paper.venue}")
        
        # Test venue search
        print("\nTesting venue search for 'POPL'...")
        results = await dblp.search_by_venue("popl", year=2023, max_results=5)
        for paper in results[:3]:
            print(f"- {paper.title} ({paper.year}) - {paper.venue}")


if __name__ == "__main__":
    asyncio.run(main())