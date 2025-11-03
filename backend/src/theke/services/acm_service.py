"""
ACM Digital Library search service.
ACM DL contains proceedings from major PL conferences like POPL, PLDI, ICFP, OOPSLA.

Note: ACM DL doesn't have a public API, so we use web scraping with respectful practices.
This implementation focuses on getting metadata from publicly available information.
"""

import asyncio
import aiohttp
import re
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus, urljoin
from dataclasses import dataclass
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ACMPaper:
    """Represents a paper from ACM Digital Library."""
    acm_id: str
    doi: str
    title: str
    authors: List[str]
    year: Optional[int]
    venue: Optional[str]
    venue_full: Optional[str]  # Full venue name
    abstract: Optional[str]
    pages: Optional[str]
    url: str
    pdf_url: Optional[str]
    keywords: List[str]
    
    def to_external_paper(self) -> Dict[str, Any]:
        """Convert to standard ExternalPaper format."""
        return {
            "external_id": self.acm_id,
            "source": "acm_dl",
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.venue_full or self.venue,
            "abstract": self.abstract,
            "doi": self.doi,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "metadata": {
                "venue_short": self.venue,
                "venue_full": self.venue_full,
                "pages": self.pages,
                "keywords": self.keywords,
                "acm_id": self.acm_id
            }
        }

class ACMDigitalLibraryService:
    """Service for searching ACM Digital Library."""
    
    BASE_URL = "https://dl.acm.org"
    SEARCH_URL = f"{BASE_URL}/action/doSearch"
    
    # Major PL conferences in ACM DL
    PL_CONFERENCES = {
        "POPL": "Proceedings of the ACM SIGPLAN Symposium on Principles of Programming Languages",
        "PLDI": "Proceedings of the ACM SIGPLAN Conference on Programming Language Design and Implementation", 
        "ICFP": "Proceedings of the ACM SIGPLAN International Conference on Functional Programming",
        "OOPSLA": "Proceedings of the Annual ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications",
        "CC": "Proceedings of the International Conference on Compiler Construction",
        "CGO": "Proceedings of the International Symposium on Code Generation and Optimization",
        "ECOOP": "European Conference on Object-Oriented Programming",
        "ESOP": "European Symposium on Programming",
        "PPDP": "Proceedings of the ACM SIGPLAN Conference on Principles and Practice of Declarative Programming",
        "PEPM": "Proceedings of the ACM SIGPLAN Workshop on Partial Evaluation and Program Manipulation",
        "DLS": "Proceedings of the Dynamic Languages Symposium",
        "GPCE": "Proceedings of the ACM SIGPLAN Conference on Generative Programming and Component Engineering",
        "SLE": "Proceedings of the ACM SIGPLAN Conference on Software Language Engineering",
        "Onward!": "Proceedings of the ACM SIGPLAN Conference on Systems, Programming, Languages and Applications: Software for Humanity"
    }
    
    def __init__(self, timeout: int = 30, delay: float = 1.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay = delay  # Respectful delay between requests
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Academic Research Bot; +https://example.com/bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout, 
            headers=self.headers,
            connector=connector
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_by_title(self, title: str, max_results: int = 10) -> List[ACMPaper]:
        """Search ACM DL by paper title."""
        try:
            query = f'Title:"{title}"'
            return await self._search_acm(query, max_results)
        except Exception as e:
            logger.error(f"ACM DL title search failed for '{title}': {e}")
            return []
    
    async def search_by_author(self, author: str, max_results: int = 20) -> List[ACMPaper]:
        """Search ACM DL by author name."""
        try:
            query = f'Author:"{author}"'
            return await self._search_acm(query, max_results)
        except Exception as e:
            logger.error(f"ACM DL author search failed for '{author}': {e}")
            return []
    
    async def search_by_conference(self, conference: str, year: Optional[int] = None, max_results: int = 50) -> List[ACMPaper]:
        """Search ACM DL by conference."""
        try:
            conference_upper = conference.upper()
            if conference_upper in self.PL_CONFERENCES:
                venue_query = f'PublicationTitle:"{conference_upper}"'
            else:
                venue_query = f'PublicationTitle:"{conference}"'
            
            if year:
                query = f'{venue_query} AND AfterYear:{year-1} AND BeforeYear:{year+1}'
            else:
                query = venue_query
                
            return await self._search_acm(query, max_results)
        except Exception as e:
            logger.error(f"ACM DL conference search failed for '{conference}': {e}")
            return []
    
    async def search_general(self, query: str, max_results: int = 20, pl_focus: bool = True) -> List[ACMPaper]:
        """
        General search with optional PL focus.
        
        Args:
            query: Search terms
            max_results: Maximum results to return
            pl_focus: If True, add PL-related filters
        """
        try:
            search_query = query
            
            if pl_focus:
                # Add PL conference filter to focus results
                pl_venues = " OR ".join([f'PublicationTitle:"{conf}"' for conf in ["POPL", "PLDI", "ICFP", "OOPSLA"]])
                search_query = f'({query}) AND ({pl_venues})'
            
            return await self._search_acm(search_query, max_results)
        except Exception as e:
            logger.error(f"ACM DL general search failed for '{query}': {e}")
            return []
    
    async def get_recent_pl_papers(self, max_results: int = 50) -> List[ACMPaper]:
        """Get recent papers from major PL conferences."""
        try:
            current_year = datetime.now().year
            results = []
            
            # Search each major PL conference for recent papers
            for conf_short in ["POPL", "PLDI", "ICFP", "OOPSLA"]:
                for year in [current_year, current_year - 1]:
                    conf_papers = await self.search_by_conference(conf_short, year, 15)
                    results.extend(conf_papers)
                    # Respectful delay between searches
                    await asyncio.sleep(self.delay)
            
            # Sort by year descending and return most recent
            results.sort(key=lambda p: p.year or 0, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"ACM DL recent PL papers search failed: {e}")
            return []
    
    async def search_by_doi(self, doi: str) -> Optional[ACMPaper]:
        """Search ACM DL by DOI."""
        try:
            query = f'DOI:"{doi}"'
            results = await self._search_acm(query, 1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"ACM DL DOI search failed for '{doi}': {e}")
            return None
    
    async def _search_acm(self, query: str, max_results: int) -> List[ACMPaper]:
        """Execute search against ACM DL."""
        if not self.session:
            raise RuntimeError("ACMDigitalLibraryService must be used as async context manager")
        
        params = {
            "AllField": query,
            "startPage": 0,
            "pageSize": min(max_results, 50),  # ACM DL limit per page
            "sortBy": "relevancy"
        }
        
        logger.info(f"Searching ACM DL: {query}")
        
        try:
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"ACM DL search failed with status {response.status}")
                    return []
                
                html_content = await response.text()
                papers = await self._parse_search_results(html_content)
                
                # Get detailed info for each paper
                detailed_papers = []
                for paper in papers[:max_results]:
                    try:
                        detailed_paper = await self._get_paper_details(paper)
                        if detailed_paper:
                            detailed_papers.append(detailed_paper)
                        # Respectful delay between detail requests
                        await asyncio.sleep(self.delay * 0.5)
                    except Exception as e:
                        logger.warning(f"Failed to get details for paper {paper.acm_id}: {e}")
                        detailed_papers.append(paper)  # Use basic info if detailed fetch fails
                
                return detailed_papers
                
        except asyncio.TimeoutError:
            logger.error("ACM DL search timeout")
            return []
        except Exception as e:
            logger.error(f"ACM DL search error: {e}")
            return []
    
    async def _parse_search_results(self, html_content: str) -> List[ACMPaper]:
        """Parse ACM DL search results HTML."""
        papers = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find search result items
            result_items = soup.find_all('div', class_='issue-item')
            
            for item in result_items:
                try:
                    paper = self._parse_result_item(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing ACM DL result item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing ACM DL search results: {e}")
        
        return papers
    
    def _parse_result_item(self, item) -> Optional[ACMPaper]:
        """Parse individual search result item."""
        try:
            # Extract title and URL
            title_link = item.find('h5', class_='issue-item__title').find('a')
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            paper_url = urljoin(self.BASE_URL, title_link['href'])
            
            # Extract ACM ID from URL
            acm_id_match = re.search(r'/doi/(abs|pdf|full)/(10\.1145/\d+\.\d+)', paper_url)
            if acm_id_match:
                doi = acm_id_match.group(2)
                acm_id = doi.replace('10.1145/', '')
            else:
                return None
            
            # Extract authors
            authors = []
            authors_section = item.find('div', class_='issue-item__detail')
            if authors_section:
                author_links = authors_section.find_all('a', href=re.compile(r'/profile/'))
                authors = [link.get_text(strip=True) for link in author_links]
            
            # Extract venue and year
            venue = None
            venue_full = None
            year = None
            
            venue_info = item.find('div', class_='issue-item__detail')
            if venue_info:
                venue_text = venue_info.get_text()
                
                # Extract year
                year_match = re.search(r'\b(19|20)\d{2}\b', venue_text)
                if year_match:
                    year = int(year_match.group())
                
                # Extract venue name
                venue_match = re.search(r'([A-Z]+\s*\d{2,4})', venue_text)
                if venue_match:
                    venue = venue_match.group().strip()
            
            return ACMPaper(
                acm_id=acm_id,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                venue_full=venue_full,
                abstract=None,  # Will be filled by detail request
                pages=None,
                url=paper_url,
                pdf_url=None,
                keywords=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing ACM result item: {e}")
            return None
    
    async def _get_paper_details(self, paper: ACMPaper) -> Optional[ACMPaper]:
        """Get detailed information for a paper."""
        if not self.session:
            return paper
        
        try:
            async with self.session.get(paper.url) as response:
                if response.status != 200:
                    return paper
                
                html_content = await response.text()
                return self._parse_paper_details(html_content, paper)
        
        except Exception as e:
            logger.warning(f"Failed to get paper details for {paper.acm_id}: {e}")
            return paper
    
    def _parse_paper_details(self, html_content: str, paper: ACMPaper) -> ACMPaper:
        """Parse detailed paper information from paper page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract abstract
            abstract_section = soup.find('div', class_='abstractSection')
            if abstract_section:
                abstract_p = abstract_section.find('p')
                if abstract_p:
                    paper.abstract = abstract_p.get_text(strip=True)
            
            # Extract keywords
            keywords_section = soup.find('div', class_='keywords')
            if keywords_section:
                keyword_links = keywords_section.find_all('a')
                paper.keywords = [link.get_text(strip=True) for link in keyword_links]
            
            # Extract full venue name
            venue_section = soup.find('div', class_='issue-item__detail')
            if venue_section:
                venue_text = venue_section.get_text()
                # Look for full conference name patterns
                for conf_short, conf_full in self.PL_CONFERENCES.items():
                    if conf_short.upper() in venue_text.upper():
                        paper.venue_full = conf_full
                        break
            
            # Extract pages
            pages_match = re.search(r'pp\.\s*(\d+[-–]\d+)', html_content)
            if pages_match:
                paper.pages = pages_match.group(1)
            
            # Look for PDF URL
            pdf_link = soup.find('a', href=re.compile(r'/doi/pdf/'))
            if pdf_link:
                paper.pdf_url = urljoin(self.BASE_URL, pdf_link['href'])
        
        except Exception as e:
            logger.warning(f"Error parsing paper details: {e}")
        
        return paper


async def search_acm_papers(query: str, max_results: int = 20, search_type: str = "general") -> List[Dict[str, Any]]:
    """
    Convenience function for searching ACM Digital Library papers.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        search_type: Type of search ("general", "title", "author", "conference")
    
    Returns:
        List of papers in ExternalPaper format
    """
    async with ACMDigitalLibraryService() as acm:
        if search_type == "title":
            papers = await acm.search_by_title(query, max_results)
        elif search_type == "author":
            papers = await acm.search_by_author(query, max_results)
        elif search_type == "conference":
            papers = await acm.search_by_conference(query, max_results=max_results)
        else:  # general
            papers = await acm.search_general(query, max_results)
    
    return [paper.to_external_paper() for paper in papers]


# Example usage and testing
async def main():
    """Test ACM DL service functionality."""
    async with ACMDigitalLibraryService() as acm:
        # Test conference search
        print("Testing POPL 2023 search...")
        results = await acm.search_by_conference("POPL", 2023, max_results=3)
        for paper in results:
            print(f"- {paper.title}")
            print(f"  Authors: {', '.join(paper.authors[:3])}...")
            print(f"  DOI: {paper.doi}")
        
        # Test title search
        print("\nTesting title search...")
        results = await acm.search_by_title("linear types", max_results=2)
        for paper in results:
            print(f"- {paper.title} ({paper.year})")
        
        # Test author search
        print("\nTesting author search...")
        results = await acm.search_by_author("Simon Peyton Jones", max_results=2)
        for paper in results:
            print(f"- {paper.title} ({paper.year}) - {paper.venue}")


if __name__ == "__main__":
    asyncio.run(main())