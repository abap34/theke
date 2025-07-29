"""
Bidirectional Citation Service
Implements forward and backward citation extraction for comprehensive citation analysis.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
from sqlalchemy.orm import Session

from .enhanced_citation_extractor import ExtractedCitation


@dataclass
class CitationRelation:
    """Represents a bidirectional citation relationship"""

    paper_id: int
    related_paper_title: str
    related_paper_authors: List[str]
    related_paper_year: Optional[int]
    related_paper_doi: Optional[str]
    related_paper_journal: Optional[str]
    relation_type: str  # "cites" or "cited_by"
    confidence: float
    source: str


class BidirectionalCitationService:
    """Service for extracting both forward and backward citations"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def extract_references(
        self, paper_id: int, paper_title: str, paper_doi: Optional[str] = None, pdf_path: Optional[str] = None
    ) -> List[CitationRelation]:
        """論文が引用している文献を抽出（Forward Citations）"""
        relations = []

        # 既存の強化された抽出器を使用
        from .enhanced_citation_extractor import EnhancedCitationExtractor

        async with EnhancedCitationExtractor() as extractor:
            citations = await extractor.extract_citations_comprehensive(
                paper_title=paper_title, paper_doi=paper_doi, pdf_path=pdf_path
            )

            for citation in citations:
                relation = CitationRelation(
                    paper_id=paper_id,
                    related_paper_title=citation.title or "",
                    related_paper_authors=citation.authors or [],
                    related_paper_year=citation.year,
                    related_paper_doi=citation.doi,
                    related_paper_journal=citation.journal,
                    relation_type="cites",
                    confidence=citation.confidence,
                    source=citation.source,
                )
                relations.append(relation)

        return relations

    async def extract_citing_papers(
        self, paper_id: int, paper_title: str, paper_doi: Optional[str] = None
    ) -> List[CitationRelation]:
        """この論文を引用している文献を抽出（Backward Citations）"""
        relations = []

        # 複数のAPIから並列で取得
        tasks = [
            self._get_citing_papers_from_openalex(paper_title, paper_doi),
            self._get_citing_papers_from_semantic_scholar(paper_title, paper_doi),
            self._get_citing_papers_from_crossref(paper_title, paper_doi),
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    for citing_paper in result:
                        relation = CitationRelation(
                            paper_id=paper_id,
                            related_paper_title=citing_paper.get("title", ""),
                            related_paper_authors=citing_paper.get("authors", []),
                            related_paper_year=citing_paper.get("year"),
                            related_paper_doi=citing_paper.get("doi"),
                            related_paper_journal=citing_paper.get("journal"),
                            relation_type="cited_by",
                            confidence=citing_paper.get("confidence", 0.8),
                            source=citing_paper.get("source", "unknown"),
                        )
                        relations.append(relation)
                elif isinstance(result, Exception):
                    print(f"Error in citing papers extraction: {result}")

        except Exception as e:
            print(f"Failed to extract citing papers: {e}")

        return relations

    async def extract_comprehensive_relations(
        self,
        paper_id: int,
        paper_title: str,
        paper_doi: Optional[str] = None,
        pdf_path: Optional[str] = None,
        direction: str = "both",
    ) -> Dict[str, List[CitationRelation]]:
        """包括的な引用関係の抽出"""

        results: Dict[str, List[CitationRelation]] = {
            "references": [],
            "citing_papers": [],
        }

        tasks = []

        if direction in ["both", "references"]:
            tasks.append(
                (
                    "references",
                    self.extract_references(paper_id, paper_title, paper_doi, pdf_path),
                )
            )

        if direction in ["both", "citing_papers"]:
            tasks.append(
                (
                    "citing_papers",
                    self.extract_citing_papers(paper_id, paper_title, paper_doi),
                )
            )

        if tasks:
            task_results = await asyncio.gather(
                *[task[1] for task in tasks], return_exceptions=True
            )

            for i, (relation_type, result) in enumerate(
                zip([task[0] for task in tasks], task_results)
            ):
                if isinstance(result, list):
                    results[relation_type] = result
                elif isinstance(result, Exception):
                    print(f"Error extracting {relation_type}: {result}")
                    results[relation_type] = []

        return results

    async def _get_citing_papers_from_openalex(
        self, title: str, doi: Optional[str]
    ) -> List[Dict[str, Any]]:
        """OpenAlexからの引用元論文取得"""
        citing_papers: List[Dict[str, Any]] = []

        if not self.session:
            return citing_papers

        try:
            # まず対象論文を特定
            if doi:
                search_url = f"https://api.openalex.org/works?filter=doi:{doi}"
            else:
                search_url = f"https://api.openalex.org/works?search={title}&per-page=1"

            async with self.session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])

                    if results:
                        work = results[0]
                        openalex_id = work.get("id", "").split("/")[
                            -1
                        ]  # Extract ID from URL

                        # この論文を引用している論文を取得
                        citing_url = f"https://api.openalex.org/works?filter=cites:{openalex_id}&per-page=50"

                        async with self.session.get(citing_url) as citing_response:
                            if citing_response.status == 200:
                                citing_data = await citing_response.json()

                                for citing_work in citing_data.get("results", []):
                                    paper_info = {
                                        "title": citing_work.get("title", ""),
                                        "authors": [
                                            auth.get("author", {}).get(
                                                "display_name", ""
                                            )
                                            for auth in citing_work.get(
                                                "authorships", []
                                            )
                                        ],
                                        "year": citing_work.get("publication_year"),
                                        "doi": (
                                            citing_work.get("doi", "").replace(
                                                "https://doi.org/", ""
                                            )
                                            if citing_work.get("doi")
                                            else None
                                        ),
                                        "journal": citing_work.get(
                                            "host_venue", {}
                                        ).get("display_name"),
                                        "confidence": 0.9,  # OpenAlexは高信頼性
                                        "source": "openalex",
                                    }
                                    citing_papers.append(paper_info)

        except Exception as e:
            print(f"OpenAlex citing papers extraction error: {e}")

        return citing_papers

    async def _get_citing_papers_from_semantic_scholar(
        self, title: str, doi: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Semantic Scholarからの引用元論文取得"""
        citing_papers: List[Dict[str, Any]] = []

        if not self.session:
            return citing_papers

        try:
            # まず対象論文を検索
            search_query = doi if doi else title
            search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": search_query,
                "limit": 1,
                "fields": "paperId,citations,citations.title,citations.authors,citations.year,citations.venue,citations.externalIds",
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get("data", [])

                    if papers:
                        paper = papers[0]
                        citations = paper.get("citations", [])

                        for citation in citations:
                            paper_info = {
                                "title": citation.get("title", ""),
                                "authors": [
                                    author.get("name", "")
                                    for author in citation.get("authors", [])
                                ],
                                "year": citation.get("year"),
                                "doi": citation.get("externalIds", {}).get("DOI"),
                                "journal": citation.get("venue"),
                                "confidence": 0.8,  # Semantic Scholarは中程度の信頼性
                                "source": "semantic_scholar",
                            }
                            citing_papers.append(paper_info)

        except Exception as e:
            print(f"Semantic Scholar citing papers extraction error: {e}")

        return citing_papers

    async def _get_citing_papers_from_crossref(
        self, title: str, doi: Optional[str]
    ) -> List[Dict[str, Any]]:
        """CrossRefからの引用元論文取得"""
        citing_papers: List[Dict[str, Any]] = []

        if not self.session:
            return citing_papers

        try:
            # CrossRefは直接的な被引用検索はサポートしていないが、
            # イベントデータAPIを使用して引用情報を取得可能
            if doi:
                # CrossRef Event Data API
                events_url = f"https://api.eventdata.crossref.org/v1/events?obj-id={doi}&source=crossref"

                async with self.session.get(events_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        events = data.get("message", {}).get("events", [])

                        for event in events:
                            if event.get("relation_type_id") == "cites":
                                subj = event.get("subj", {})

                                # 引用している論文の情報を取得
                                citing_doi = subj.get("pid")
                                if citing_doi:
                                    # CrossRef APIで論文詳細を取得
                                    work_url = (
                                        f"https://api.crossref.org/works/{citing_doi}"
                                    )

                                    async with self.session.get(
                                        work_url
                                    ) as work_response:
                                        if work_response.status == 200:
                                            work_data = await work_response.json()
                                            work = work_data.get("message", {})

                                            authors = []
                                            if work.get("author"):
                                                authors = [
                                                    f"{author.get('given', '')} {author.get('family', '')}"
                                                    for author in work["author"]
                                                ]

                                            paper_info = {
                                                "title": (
                                                    work.get("title", [""])[0]
                                                    if work.get("title")
                                                    else ""
                                                ),
                                                "authors": authors,
                                                "year": work.get(
                                                    "published-print", {}
                                                ).get("date-parts", [[None]])[0][0]
                                                or work.get("published-online", {}).get(
                                                    "date-parts", [[None]]
                                                )[0][0],
                                                "doi": work.get("DOI"),
                                                "journal": (
                                                    work.get("container-title", [""])[0]
                                                    if work.get("container-title")
                                                    else None
                                                ),
                                                "confidence": 0.95,  # CrossRefは最高信頼性
                                                "source": "crossref",
                                            }
                                            citing_papers.append(paper_info)

        except Exception as e:
            print(f"CrossRef citing papers extraction error: {e}")

        return citing_papers

    def build_citation_network(
        self, relations: Dict[str, List[CitationRelation]]
    ) -> Dict[str, Any]:
        """引用ネットワークのグラフデータを構築"""
        nodes = []
        edges = []
        node_ids = set()

        # 中心ノード（対象論文）
        refs = relations.get("references", [])
        citing_papers = relations.get("citing_papers", [])
        center_paper_id = (
            refs[0].paper_id
            if refs
            else (citing_papers[0].paper_id if citing_papers else 0)
        )
        center_node_id = f"paper_{center_paper_id}"

        # 中心論文の情報を取得（最初の関係から）
        center_title = "Target Paper"
        if refs:
            # 参照文献がある場合は、そこから中心論文の情報を推測
            center_title = f"Paper {center_paper_id}"
        elif citing_papers:
            # 被引用文献がある場合
            center_title = f"Paper {center_paper_id}"

        if center_node_id not in node_ids:
            nodes.append(
                {
                    "id": center_node_id,
                    "label": center_title,
                    "type": "center",
                    "size": 20,
                    "confidence": 1.0,
                }
            )
            node_ids.add(center_node_id)

        # 参照文献（この論文が引用している論文）
        for i, ref in enumerate(relations.get("references", [])):
            # より安定したIDを生成
            node_id = f"ref_{center_paper_id}_{i}"

            if node_id not in node_ids:
                title = ref.related_paper_title or "Unknown Title"
                nodes.append(
                    {
                        "id": node_id,
                        "label": (title[:50] + "..." if len(title) > 50 else title),
                        "type": "reference",
                        "size": 10,
                        "confidence": ref.confidence,
                        "authors": ref.related_paper_authors,
                        "year": ref.related_paper_year,
                        "journal": ref.related_paper_journal,
                    }
                )
                node_ids.add(node_id)

            # エッジID を明示的に設定
            edge_id = f"edge_ref_{center_paper_id}_{i}"
            edges.append(
                {
                    "id": edge_id,
                    "source": center_node_id,
                    "target": node_id,
                    "type": "cites",
                    "confidence": ref.confidence,
                    "label": f"cites ({ref.confidence:.2f})",
                }
            )

        # 引用元文献（この論文を引用している論文）
        for i, cit in enumerate(relations.get("citing_papers", [])):
            # より安定したIDを生成
            node_id = f"cit_{center_paper_id}_{i}"

            if node_id not in node_ids:
                title = cit.related_paper_title or "Unknown Title"
                nodes.append(
                    {
                        "id": node_id,
                        "label": (title[:50] + "..." if len(title) > 50 else title),
                        "type": "citing",
                        "size": 10,
                        "confidence": cit.confidence,
                        "authors": cit.related_paper_authors,
                        "year": cit.related_paper_year,
                        "journal": cit.related_paper_journal,
                    }
                )
                node_ids.add(node_id)

            # エッジID を明示的に設定
            edge_id = f"edge_cit_{center_paper_id}_{i}"
            edges.append(
                {
                    "id": edge_id,
                    "source": node_id,
                    "target": center_node_id,
                    "type": "cited_by",
                    "confidence": cit.confidence,
                    "label": f"cited by ({cit.confidence:.2f})",
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_references": len(relations.get("references", [])),
                "total_citing_papers": len(relations.get("citing_papers", [])),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }
