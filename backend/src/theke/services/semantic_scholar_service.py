import asyncio
import re
from typing import Any, Dict, List, Optional

import aiohttp


class SemanticScholarService:
    """Semantic Scholar API service for extracting paper citations"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_paper_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Search for a paper by title on Semantic Scholar"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Clean the title for search
            clean_title = re.sub(r"[^\w\s]", " ", title)
            clean_title = re.sub(r"\s+", " ", clean_title).strip()

            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": clean_title,
                "limit": 5,
                "fields": "paperId,title,authors,year,venue,citationCount,referenceCount,references",
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get("data", [])

                    # Find the best match by title similarity
                    for paper in papers:
                        if self._title_similarity(title, paper.get("title", "")) > 0.7:
                            return paper

                    # If no good match, return the first result
                    return papers[0] if papers else None
                else:
                    print(f"Semantic Scholar search failed: {response.status}")
                    return None

        except Exception as e:
            print(f"Error searching Semantic Scholar: {e}")
            return None

    async def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get paper information by DOI"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = f"{self.BASE_URL}/paper/DOI:{doi}"
            params = {
                "fields": "paperId,title,authors,year,venue,citationCount,referenceCount,references"
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Semantic Scholar DOI lookup failed: {response.status}")
                    return None

        except Exception as e:
            print(f"Error getting paper by DOI: {e}")
            return None

    async def get_paper_references(
        self, paper_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get all references for a paper"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = f"{self.BASE_URL}/paper/{paper_id}/references"
            params = {
                "fields": "title,authors,year,venue,doi,citationCount",
                "limit": limit,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    references = []

                    # The API can return {'data': null}, so we use 'or []' to handle it.
                    for ref in data.get("data") or []:
                        cited_paper = ref.get("citedPaper")
                        
                        # Ensure cited_paper exists and has a title before appending.
                        if cited_paper and cited_paper.get("title"):
                            references.append(
                                {
                                    "title": cited_paper.get("title"),
                                    "authors": [
                                        author.get("name", "")
                                        for author in cited_paper.get("authors") or []
                                    ],
                                    "year": cited_paper.get("year"),
                                    "venue": cited_paper.get("venue"),
                                    "doi": cited_paper.get("doi"),
                                    "citation_count": cited_paper.get(
                                        "citationCount", 0
                                    ),
                                }
                            )

                    return references
                else:
                    print(
                        f"Semantic Scholar references lookup failed: {response.status}"
                    )
                    return []

        except Exception as e:
            print(f"Error getting paper references: {e}")
            return []

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity"""
        if not title1 or not title2:
            return 0.0

        # Normalize titles
        t1 = re.sub(r"[^\w\s]", " ", title1.lower())
        t2 = re.sub(r"[^\w\s]", " ", title2.lower())
        t1 = re.sub(r"\s+", " ", t1).strip()
        t2 = re.sub(r"\s+", " ", t2).strip()

        # Split into words
        words1 = set(t1.split())
        words2 = set(t2.split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    async def find_doi_by_title_and_authors(
        self, title: str, authors: List[str]
    ) -> Optional[str]:
        """Find a paper's DOI by title and authors."""
        paper = await self.search_paper_by_title(title)
        if not paper or not paper.get("authors"):
            return None

        # Compare author lists to find the best match
        paper_authors = {author["name"].lower() for author in paper["authors"]}
        query_authors = {author.lower() for author in authors}

        # Check for partial match in authors
        if paper_authors.intersection(query_authors):
            return paper.get("doi")

        return None


async def extract_citations_from_semantic_scholar(
    paper_title: str, paper_doi: str = None
) -> List[Dict[str, Any]]:
    """Extract citations for a paper using Semantic Scholar API"""
    async with SemanticScholarService() as service:
        # Try to find the paper first
        paper = None

        # First try by DOI if available
        if paper_doi:
            paper = await service.get_paper_by_doi(paper_doi)

        # If no DOI is provided, try by title
        if not paper and paper_title:
            paper = await service.search_paper_by_title(paper_title)

        if not paper or not paper.get("paperId"):
            print(f"Could not find paper on Semantic Scholar: {paper_title}")
            return []

        print(
            f"Found paper on Semantic Scholar: {paper.get('title')} (ID: {paper.get('paperId')})"
        )

        # Get references
        references = await service.get_paper_references(paper["paperId"])

        print(f"Found {len(references)} references on Semantic Scholar")

        # Convert to our citation format
        citations = []
        for ref in references:
            if ref.get("title"):  # Only include references with titles
                citations.append(
                    {
                        "title": ref["title"],
                        "authors": ref.get("authors", []),
                        "year": ref.get("year"),
                        "journal": ref.get("venue"),
                        "doi": ref.get("doi"),
                        "citation_count": ref.get("citation_count", 0),
                    }
                )

        return citations
