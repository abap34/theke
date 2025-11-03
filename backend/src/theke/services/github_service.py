"""
GitHub search service for finding research-related repositories, code implementations,
and academic projects. Particularly useful for PL research where implementations
are often available on GitHub.

Uses GitHub REST API v4 with proper authentication and rate limiting.
"""

import asyncio
import aiohttp
import json
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class GitHubRepository:
    """Represents a GitHub repository from search results."""
    github_id: int
    name: str
    full_name: str  # owner/repo
    owner: str
    description: Optional[str]
    url: str
    clone_url: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime]
    size: int  # KB
    has_issues: bool
    has_wiki: bool
    has_pages: bool
    archived: bool
    license_name: Optional[str]
    readme_content: Optional[str]  # Filled separately if requested
    
    def to_external_paper(self) -> Dict[str, Any]:
        """Convert to external paper format for consistency."""
        return {
            "external_id": str(self.github_id),
            "source": "github",
            "title": self.name,
            "authors": [self.owner],  # Repository owner as author
            "year": self.created_at.year,
            "journal": "GitHub Repository",
            "abstract": self.description,
            "url": self.url,
            "metadata": {
                "full_name": self.full_name,
                "clone_url": self.clone_url,
                "stars": self.stars,
                "forks": self.forks,
                "language": self.language,
                "topics": self.topics,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
                "size_kb": self.size,
                "has_issues": self.has_issues,
                "has_wiki": self.has_wiki,
                "has_pages": self.has_pages,
                "archived": self.archived,
                "license": self.license_name,
                "readme_content": self.readme_content
            }
        }

class GitHubService:
    """Service for searching GitHub repositories related to academic research."""
    
    BASE_URL = "https://api.github.com"
    SEARCH_URL = f"{BASE_URL}/search/repositories"
    
    # PL and CS research related topics and keywords
    PL_TOPICS = {
        "programming-languages", "compiler", "interpreter", "type-system",
        "static-analysis", "program-analysis", "formal-verification",
        "functional-programming", "object-oriented-programming",
        "memory-management", "garbage-collection", "runtime-system",
        "program-synthesis", "domain-specific-language", "dsl",
        "abstract-interpretation", "model-checking", "proof-assistant",
        "llvm", "webassembly", "jvm", "bytecode"
    }
    
    CS_RESEARCH_TOPICS = {
        "machine-learning", "deep-learning", "neural-networks",
        "computer-vision", "natural-language-processing", "nlp",
        "algorithms", "data-structures", "distributed-systems",
        "database", "networking", "security", "cryptography",
        "human-computer-interaction", "hci", "visualization",
        "operating-systems", "computer-graphics", "robotics"
    }
    
    def __init__(self, github_token: Optional[str] = None, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.github_token = github_token
        
        # Set up headers
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Academic-Research-Tool/1.0"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        # Rate limiting info
        self.rate_limit_remaining = 60  # Default for unauthenticated requests
        self.rate_limit_reset = datetime.now()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout, headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_repositories(self, 
                                query: str, 
                                sort: str = "stars",
                                order: str = "desc",
                                max_results: int = 30,
                                language: Optional[str] = None,
                                min_stars: int = 1,
                                topics: Optional[List[str]] = None) -> List[GitHubRepository]:
        """
        Search GitHub repositories with various filters.
        
        Args:
            query: Search query
            sort: Sort by "stars", "forks", "updated"
            order: "asc" or "desc"
            max_results: Maximum results to return
            language: Filter by programming language
            min_stars: Minimum number of stars
            topics: Filter by repository topics
        """
        try:
            # Build search query
            search_terms = [query]
            
            if language:
                search_terms.append(f"language:{language}")
            
            if min_stars > 1:
                search_terms.append(f"stars:>={min_stars}")
            
            if topics:
                for topic in topics:
                    search_terms.append(f"topic:{topic}")
            
            full_query = " ".join(search_terms)
            
            params = {
                "q": full_query,
                "sort": sort,
                "order": order,
                "per_page": min(max_results, 100),  # GitHub API limit
                "page": 1
            }
            
            return await self._search_github(params)
            
        except Exception as e:
            logger.error(f"GitHub repository search failed for '{query}': {e}")
            return []
    
    async def search_by_paper_title(self, title: str, max_results: int = 10) -> List[GitHubRepository]:
        """Search for repositories that might implement a specific paper."""
        try:
            # Extract key terms from title for better matching
            key_terms = self._extract_key_terms(title)
            search_query = " ".join(key_terms)
            
            return await self.search_repositories(
                query=search_query,
                sort="stars",
                max_results=max_results,
                min_stars=2  # Filter out very low-quality repos
            )
        except Exception as e:
            logger.error(f"GitHub paper implementation search failed for '{title}': {e}")
            return []
    
    async def search_academic_repositories(self, 
                                        query: str, 
                                        field: str = "pl",
                                        max_results: int = 20) -> List[GitHubRepository]:
        """
        Search for academic repositories in a specific field.
        
        Args:
            query: Search query
            field: Academic field ("pl", "ml", "systems", "theory", "hci")
            max_results: Maximum results
        """
        try:
            # Add field-specific terms and topics
            academic_terms = ["research", "paper", "implementation", "academic"]
            
            if field == "pl":
                topics = ["programming-languages", "compiler", "type-system"]
                academic_terms.extend(["language", "compiler", "type", "analysis"])
            elif field == "ml":
                topics = ["machine-learning", "deep-learning", "neural-networks"]
                academic_terms.extend(["learning", "neural", "model"])
            elif field == "systems":
                topics = ["distributed-systems", "operating-systems", "database"]
                academic_terms.extend(["system", "distributed", "performance"])
            elif field == "theory":
                topics = ["algorithms", "data-structures", "formal-verification"]
                academic_terms.extend(["algorithm", "proof", "verification"])
            elif field == "hci":
                topics = ["human-computer-interaction", "visualization", "user-interface"]
                academic_terms.extend(["interface", "user", "visualization"])
            else:
                topics = []
            
            # Combine query with academic terms
            full_query = f"{query} {' OR '.join(academic_terms[:3])}"
            
            return await self.search_repositories(
                query=full_query,
                topics=topics[:2],  # Don't overwhelm the query
                min_stars=3,
                max_results=max_results
            )
        except Exception as e:
            logger.error(f"GitHub academic search failed for '{query}' in field '{field}': {e}")
            return []
    
    async def search_by_author(self, author: str, max_results: int = 20) -> List[GitHubRepository]:
        """Search repositories by a specific author/researcher."""
        try:
            # Try both username and organization search
            user_query = f"user:{author}"
            org_query = f"org:{author}"
            
            # Search user repositories
            user_repos = await self.search_repositories(
                query=user_query,
                sort="updated",
                max_results=max_results // 2
            )
            
            # Search organization repositories
            org_repos = await self.search_repositories(
                query=org_query,
                sort="updated", 
                max_results=max_results // 2
            )
            
            # Combine and deduplicate
            all_repos = user_repos + org_repos
            seen_ids = set()
            unique_repos = []
            
            for repo in all_repos:
                if repo.github_id not in seen_ids:
                    seen_ids.add(repo.github_id)
                    unique_repos.append(repo)
            
            return unique_repos[:max_results]
            
        except Exception as e:
            logger.error(f"GitHub author search failed for '{author}': {e}")
            return []
    
    async def get_popular_pl_repositories(self, max_results: int = 30) -> List[GitHubRepository]:
        """Get popular repositories related to programming languages research."""
        try:
            # Search for popular PL repositories
            pl_query = "programming language OR compiler OR interpreter OR type system"
            
            return await self.search_repositories(
                query=pl_query,
                sort="stars",
                topics=["programming-languages", "compiler"],
                min_stars=50,
                max_results=max_results
            )
        except Exception as e:
            logger.error(f"GitHub popular PL repositories search failed: {e}")
            return []
    
    async def get_repository_readme(self, full_name: str) -> Optional[str]:
        """Get README content for a repository."""
        if not self.session:
            return None
        
        try:
            readme_url = f"{self.BASE_URL}/repos/{full_name}/readme"
            
            async with self.session.get(readme_url) as response:
                if response.status == 200:
                    data = await response.json()
                    # README content is base64 encoded
                    import base64
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content[:2000]  # Limit size
                return None
        except Exception as e:
            logger.warning(f"Failed to get README for {full_name}: {e}")
            return None
    
    def _extract_key_terms(self, title: str) -> List[str]:
        """Extract key terms from a paper title for GitHub search."""
        # Remove common academic words
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "paper", "approach", "method", "study",
            "analysis", "evaluation", "system", "using", "based", "new", "novel"
        }
        
        # Extract words, remove stop words and short words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        key_terms = [word for word in words if word not in stop_words]
        
        # Return most distinctive terms (limit to avoid too complex queries)
        return key_terms[:5]
    
    async def _search_github(self, params: Dict[str, Any]) -> List[GitHubRepository]:
        """Execute search against GitHub API."""
        if not self.session:
            raise RuntimeError("GitHubService must be used as async context manager")
        
        # Check rate limiting
        if self.rate_limit_remaining <= 1 and datetime.now() < self.rate_limit_reset:
            logger.warning("GitHub API rate limit exceeded")
            return []
        
        logger.info(f"Searching GitHub: {params['q']}")
        
        try:
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                # Update rate limiting info
                self._update_rate_limit_info(response)
                
                if response.status == 403:
                    logger.error("GitHub API rate limit exceeded")
                    return []
                elif response.status != 200:
                    logger.error(f"GitHub API error: {response.status}")
                    return []
                
                data = await response.json()
                repositories = []
                
                for item in data.get("items", []):
                    try:
                        repo = self._parse_repository(item)
                        if repo:
                            repositories.append(repo)
                    except Exception as e:
                        logger.warning(f"Error parsing GitHub repository: {e}")
                        continue
                
                return repositories
                
        except asyncio.TimeoutError:
            logger.error("GitHub search timeout")
            return []
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []
    
    def _parse_repository(self, item: Dict[str, Any]) -> Optional[GitHubRepository]:
        """Parse repository data from GitHub API response."""
        try:
            # Parse timestamps
            created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            
            pushed_at = None
            if item.get("pushed_at"):
                pushed_at = datetime.fromisoformat(item["pushed_at"].replace("Z", "+00:00"))
            
            # Extract license name
            license_name = None
            if item.get("license") and item["license"]["name"]:
                license_name = item["license"]["name"]
            
            return GitHubRepository(
                github_id=item["id"],
                name=item["name"],
                full_name=item["full_name"],
                owner=item["owner"]["login"],
                description=item.get("description"),
                url=item["html_url"],
                clone_url=item["clone_url"],
                stars=item["stargazers_count"],
                forks=item["forks_count"],
                language=item.get("language"),
                topics=item.get("topics", []),
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at,
                size=item["size"],
                has_issues=item["has_issues"],
                has_wiki=item["has_wiki"],
                has_pages=item["has_pages"],
                archived=item["archived"],
                license_name=license_name,
                readme_content=None  # Will be filled separately if requested
            )
        except Exception as e:
            logger.error(f"Error parsing GitHub repository data: {e}")
            return None
    
    def _update_rate_limit_info(self, response):
        """Update rate limiting information from response headers."""
        try:
            self.rate_limit_remaining = int(response.headers.get("x-ratelimit-remaining", 60))
            reset_timestamp = int(response.headers.get("x-ratelimit-reset", 0))
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
        except (ValueError, TypeError):
            pass


async def search_github_repositories(query: str, 
                                   search_type: str = "general",
                                   max_results: int = 20,
                                   field: str = "pl") -> List[Dict[str, Any]]:
    """
    Convenience function for searching GitHub repositories.
    
    Args:
        query: Search query
        search_type: "general", "paper_implementation", "author", "academic"
        max_results: Maximum results
        field: Academic field for academic search
    
    Returns:
        List of repositories in ExternalPaper format
    """
    # Note: In production, you should pass actual GitHub token
    github_token = None  # os.getenv("GITHUB_TOKEN")
    
    async with GitHubService(github_token=github_token) as github:
        if search_type == "paper_implementation":
            repos = await github.search_by_paper_title(query, max_results)
        elif search_type == "author":
            repos = await github.search_by_author(query, max_results)
        elif search_type == "academic":
            repos = await github.search_academic_repositories(query, field, max_results)
        else:  # general
            repos = await github.search_repositories(query, max_results=max_results)
    
    return [repo.to_external_paper() for repo in repos]


# Example usage and testing
async def main():
    """Test GitHub service functionality."""
    async with GitHubService() as github:
        # Test paper implementation search
        print("Testing paper implementation search for 'linear types'...")
        results = await github.search_by_paper_title("linear types", max_results=3)
        for repo in results:
            print(f"- {repo.full_name} ({repo.stars}⭐) - {repo.description}")
        
        # Test academic search
        print("\nTesting academic search for 'type system'...")
        results = await github.search_academic_repositories("type system", "pl", max_results=3)
        for repo in results:
            print(f"- {repo.full_name} ({repo.language}) - {repo.description}")
        
        # Test author search
        print("\nTesting author search for 'octocat'...")
        results = await github.search_by_author("octocat", max_results=3)
        for repo in results:
            print(f"- {repo.full_name} - {repo.description}")


if __name__ == "__main__":
    asyncio.run(main())