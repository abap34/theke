"""
Enhanced Citation Extractor
Implements the comprehensive citation extraction system described in the design document.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import PyPDF2


@dataclass
class ExtractedCitation:
    """Represents a citation extracted from various sources"""

    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    source: str = "unknown"
    context: Optional[str] = None
    page_number: Optional[int] = None
    confidence: float = 0.0


class EnhancedCitationExtractor:
    """Enhanced citation extraction with multiple sources and confidence scoring"""

    def __init__(self):
        self.citation_patterns = [
            # IEEE形式: [1] Author, A. (2020). "Title." Journal, vol. 1, pp. 1-10.
            {
                "pattern": r'\[(\d+)\]\s*([^()]+)\s*\((\d{4})\)\.\s*["\']([^"\']+)["\']\.?\s*([^,\n]+)',
                "groups": {
                    "number": 1,
                    "authors": 2,
                    "year": 3,
                    "title": 4,
                    "journal": 5,
                },
            },
            # APA形式: Author, A. (2020). Title. Journal, 1(1), 1-10.
            {
                "pattern": r"([^()]+)\s*\((\d{4})\)\.\s*([^.]+)\.\s*([^,]+),?\s*(\d+)?",
                "groups": {"authors": 1, "year": 2, "title": 3, "journal": 4},
            },
            # 自然言語形式: According to Smith et al. (2020), the method...
            {
                "pattern": r"([A-Z][a-zA-Z\s,]+et al\.?)\s*\((\d{4})\)",
                "groups": {"authors": 1, "year": 2},
            },
            # DOI pattern
            {
                "pattern": r"(?:doi:|DOI:)\s*(10\.\d+/[^\s]+)",
                "groups": {"doi": 1},
            },
            # 積極的な引用パターン - より多くのパターンを追加
            {
                "pattern": r"([A-Z][a-zA-Z\s]+)\s*\((\d{4})\)[,.]?\s*([^.\n]+)\.?",
                "groups": {"authors": 1, "year": 2, "title": 3},
            },
            # 番号付き引用
            {
                "pattern": r"\[(\d+)\]\s*([^\n]+)\n",
                "groups": {"number": 1, "title": 2},
            },
            # より緩い形式の引用
            {
                "pattern": r"([A-Z][^(]+)\s*\((\d{4}[a-z]?)\)",
                "groups": {"authors": 1, "year": 2},
            },
        ]

        # 参考文献セクションを特定するキーワード
        self.reference_keywords = [
            "References",
            "REFERENCES",
            "Bibliography",
            "BIBLIOGRAPHY",
            "参考文献",
            "引用文献",
            "文献",
            "Works Cited",
            "Literature Cited",
        ]

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if hasattr(self, "session"):
            await self.session.close()


    async def extract_citations_comprehensive(
        self,
        paper_title: str,
        paper_doi: Optional[str] = None,
        pdf_path: Optional[str] = None,
        preferred_source: str = "openalex",
    ) -> List[ExtractedCitation]:
        """
        Comprehensive citation extraction using multiple sources
        """
        all_citations = []

        # Phase 1: PDF本文からの抽出
        if pdf_path and Path(pdf_path).exists():
            try:
                pdf_citations = await self._extract_from_pdf(pdf_path)
                all_citations.extend(pdf_citations)
                print(f"Extracted {len(pdf_citations)} citations from PDF")
            except Exception as e:
                print(f"PDF extraction failed: {e}")

        # Phase 2: 外部APIからの抽出（並列実行）
        api_tasks = []

        if paper_doi or paper_title:
            api_tasks.extend(
                [
                    self._extract_from_crossref(paper_doi, paper_title),
                    self._extract_from_openalex(paper_doi, paper_title),
                    self._extract_from_semantic_scholar(paper_doi, paper_title),
                ]
            )

        if api_tasks:
            try:
                api_results = await asyncio.gather(*api_tasks, return_exceptions=True)

                for result in api_results:
                    if isinstance(result, list):
                        all_citations.extend(result)
                        print(f"Extracted {len(result)} citations from API")
                    elif isinstance(result, Exception):
                        print(f"API extraction failed: {result}")
            except Exception as e:
                print(f"API extraction batch failed: {e}")

        # Phase 3: 重複除去と統合
        merged_citations = self._merge_and_deduplicate(all_citations)

        # ソース別に整理
        merged_citations.sort(key=lambda x: x.source)

        print(f"Total citations after merge: {len(merged_citations)}")
        return merged_citations

    async def _extract_from_pdf(self, pdf_path: str) -> List[ExtractedCitation]:
        """PDF本文からの引用抽出"""

        def extract_text():
            try:
                with open(pdf_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    page_texts = []

                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        page_texts.append((i + 1, page_text))
                        text += f"\n--- Page {i + 1} ---\n" + page_text

                    return text, page_texts
            except Exception as e:
                print(f"Error extracting PDF text: {e}")
                return "", []

        # PDFテキスト抽出を別スレッドで実行
        with ThreadPoolExecutor() as executor:
            full_text, page_texts = await asyncio.get_event_loop().run_in_executor(
                executor, extract_text
            )

        if not full_text:
            return []

        citations = []

        # 参考文献セクションを特定
        references_section = self._find_references_section(full_text)
        if references_section:
            citations.extend(
                self._extract_citations_from_text(references_section, page_texts)
            )

        # 本文中の引用も抽出
        inline_citations = self._extract_inline_citations(full_text, page_texts)
        citations.extend(inline_citations)

        return citations

    def _find_references_section(self, text: str) -> Optional[str]:
        """参考文献セクションを特定"""
        for keyword in self.reference_keywords:
            pattern = rf"\b{re.escape(keyword)}\b.*?(?=\n\n|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _extract_citations_from_text(
        self, text: str, page_texts: List[Tuple[int, str]]
    ) -> List[ExtractedCitation]:
        """テキストから構造化された引用を抽出"""
        citations: List[ExtractedCitation] = []

        for pattern_info in self.citation_patterns:
            pattern = pattern_info["pattern"]
            groups = pattern_info["groups"]
            base_confidence = pattern_info["confidence"]

            matches = re.finditer(pattern, text, re.MULTILINE)

            for match in matches:
                citation = ExtractedCitation(source="pdf_extraction")

                # グループから情報を抽出
                for field, group_num in groups.items():
                    try:
                        value = match.group(group_num)
                        if value:
                            value = value.strip()
                            if field == "authors":
                                citation.authors = self._parse_authors(value)
                            elif field == "year":
                                citation.year = int(value)
                            elif field == "title":
                                citation.title = value
                            elif field == "journal":
                                citation.journal = value
                            elif field == "doi":
                                citation.doi = value
                    except (IndexError, ValueError):
                        continue

                # ページ番号を特定
                citation.page_number = self._find_page_number(
                    match.group(0), page_texts
                )

                # 文脈を抽出
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                citation.context = text[start:end].replace("\n", " ").strip()

                # 全ての引用を追加（フィルタリングなし）
                citations.append(citation)

        return citations

    def _extract_inline_citations(
        self, text: str, page_texts: List[Tuple[int, str]]
    ) -> List[ExtractedCitation]:
        """本文中のインライン引用を抽出"""
        citations: List[ExtractedCitation] = []

        # シンプルなインライン引用パターン
        inline_pattern = r"([A-Z][a-zA-Z\s,]+(?:et al\.?)?)\s*\((\d{4})\)"

        matches = re.finditer(inline_pattern, text)

        for match in matches:
            citation = ExtractedCitation(
                authors=self._parse_authors(match.group(1)),
                year=int(match.group(2)),
                source="pdf_extraction",
            )

            citation.page_number = self._find_page_number(match.group(0), page_texts)

            # 文脈を抽出
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            citation.context = text[start:end].replace("\n", " ").strip()

            citations.append(citation)

        return citations

    def _parse_authors(self, author_string: str) -> List[str]:
        """著者文字列をリストに分割"""
        if not author_string:
            return []

        # 一般的な区切り文字で分割
        authors = re.split(r"\s+and\s+|\s*[,;&]\s*|\s+et\s+", author_string)

        # 空の要素を除去し、適切にトリミング
        cleaned_authors = []
        for author in authors:
            author = author.strip()
            if author and author.lower() not in ["al", "al."]:
                cleaned_authors.append(author)

        return cleaned_authors

    def _find_page_number(
        self, text: str, page_texts: List[Tuple[int, str]]
    ) -> Optional[int]:
        """テキストが含まれるページ番号を特定"""
        for page_num, page_text in page_texts:
            if text in page_text:
                return page_num
        return None


    async def _extract_from_crossref(
        self, doi: Optional[str], title: str
    ) -> List[ExtractedCitation]:
        """CrossRef APIからの引用抽出"""
        citations: List[ExtractedCitation] = []

        if not self.session:
            return citations

        try:
            # DOIが利用可能な場合はそれを使用
            if doi:
                url = f"https://api.crossref.org/works/{doi}"
            else:
                # タイトルで検索
                url = f"https://api.crossref.org/works?query.title={title}&rows=1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if doi:
                        work = data.get("message", {})
                    else:
                        items = data.get("message", {}).get("items", [])
                        work = items[0] if items else {}

                    # 引用情報を抽出
                    references = work.get("reference", [])

                    for ref in references:
                        citation = ExtractedCitation(source="crossref")

                        if "title" in ref:
                            citation.title = ref["title"]
                        if "author" in ref:
                            citation.authors = [
                                f"{author.get('given', '')} {author.get('family', '')}"
                                for author in ref["author"]
                            ]
                        if "year" in ref:
                            citation.year = int(ref["year"])
                        if "DOI" in ref:
                            citation.doi = ref["DOI"]
                        if "container-title" in ref:
                            citation.journal = ref["container-title"]


                        citations.append(citation)

        except Exception as e:
            print(f"CrossRef extraction error: {e}")

        return citations

    async def _extract_from_openalex(
        self, doi: Optional[str], title: str
    ) -> List[ExtractedCitation]:
        """OpenAlex APIからの引用抽出"""
        citations: List[ExtractedCitation] = []

        if not self.session:
            return citations

        try:
            # DOIまたはタイトルで検索
            if doi:
                url = f"https://api.openalex.org/works?filter=doi:{doi}"
            else:
                url = f"https://api.openalex.org/works?search={title}&per-page=1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])

                    if results:
                        work = results[0]
                        referenced_works = work.get("referenced_works", [])

                        # 参照された論文の詳細を取得
                        if referenced_works:
                            work_ids = "|".join(
                                [
                                    work_id.split("/")[-1]
                                    for work_id in referenced_works[:50]
                                ]
                            )  # 最大50件
                            details_url = f"https://api.openalex.org/works?filter=openalex:{work_ids}"

                            async with self.session.get(
                                details_url
                            ) as details_response:
                                if details_response.status == 200:
                                    details_data = await details_response.json()

                                    for ref_work in details_data.get("results", []):
                                        citation = ExtractedCitation(source="openalex")

                                        citation.title = ref_work.get("title")
                                        if ref_work.get("authorships"):
                                            citation.authors = [
                                                auth.get("author", {}).get(
                                                    "display_name", ""
                                                )
                                                for auth in ref_work["authorships"]
                                            ]
                                        citation.year = ref_work.get("publication_year")
                                        citation.doi = (
                                            ref_work.get("doi", "").replace(
                                                "https://doi.org/", ""
                                            )
                                            if ref_work.get("doi")
                                            else None
                                        )

                                        host_venue = ref_work.get("host_venue", {})
                                        citation.journal = host_venue.get(
                                            "display_name"
                                        )


                                        citations.append(citation)

        except Exception as e:
            print(f"OpenAlex extraction error: {e}")

        return citations

    async def _extract_from_semantic_scholar(
        self, doi: Optional[str], title: str
    ) -> List[ExtractedCitation]:
        """Semantic Scholar APIからの引用抽出"""
        citations: List[ExtractedCitation] = []

        if not self.session:
            return citations

        try:
            # DOIまたはタイトルで検索
            if doi:
                search_query = doi
            else:
                search_query = title

            url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": search_query,
                "limit": 1,
                "fields": "references,references.title,references.authors,references.year,references.venue,references.externalIds",
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get("data", [])

                    if papers:
                        paper = papers[0]
                        references = paper.get("references", [])

                        for ref in references:
                            citation = ExtractedCitation(source="semantic_scholar")

                            citation.title = ref.get("title")
                            if ref.get("authors"):
                                citation.authors = [
                                    author.get("name", "") for author in ref["authors"]
                                ]
                            citation.year = ref.get("year")
                            citation.journal = ref.get("venue")

                            external_ids = ref.get("externalIds", {})
                            citation.doi = external_ids.get("DOI")


                            citations.append(citation)

        except Exception as e:
            print(f"Semantic Scholar extraction error: {e}")

        return citations

    def _merge_and_deduplicate(
        self, citations: List[ExtractedCitation]
    ) -> List[ExtractedCitation]:
        """重複する引用を統合"""
        if not citations:
            return []

        merged: List[ExtractedCitation] = []

        for citation in citations:
            # 類似する引用を検索
            similar_citation = None
            for existing in merged:
                if self._are_similar_citations(citation, existing):
                    similar_citation = existing
                    break

            if similar_citation:
                # 欠損情報を補完（信頼性に関係なく）
                if not similar_citation.title and citation.title:
                    similar_citation.title = citation.title
                if not similar_citation.authors and citation.authors:
                    similar_citation.authors = citation.authors
                if not similar_citation.year and citation.year:
                    similar_citation.year = citation.year
                if not similar_citation.doi and citation.doi:
                    similar_citation.doi = citation.doi
                if not similar_citation.journal and citation.journal:
                    similar_citation.journal = citation.journal

                # ソースを統合（優先順位に基づいて最良のソースを選択）
                source_priority = {
                    "openalex": 5,
                    "crossref": 4, 
                    "semantic_scholar": 3,
                    "pdf_extraction": 2,
                    "pdf_text": 2,
                    "llm": 1,
                    "merged": 6,  # 既に統合済み
                    "manual": 7,  # 手動入力が最優先
                    "unknown": 0
                }
                
                current_priority = source_priority.get(similar_citation.source, 0)
                new_priority = source_priority.get(citation.source, 0)
                
                if new_priority > current_priority:
                    similar_citation.source = citation.source
                elif current_priority > 0 and new_priority > 0 and current_priority == new_priority:
                    # 同じ優先度の場合は"merged"にマーク
                    similar_citation.source = "merged"
                
                # 信頼度を統合（より高い方を使用）
                if citation.confidence > similar_citation.confidence:
                    similar_citation.confidence = citation.confidence
            else:
                merged.append(citation)

        return merged

    def _are_similar_citations(
        self, cit1: ExtractedCitation, cit2: ExtractedCitation
    ) -> bool:
        """2つの引用が同じものかどうかを判定"""
        # DOIが一致する場合
        if cit1.doi and cit2.doi and cit1.doi == cit2.doi:
            return True

        # タイトルの類似度
        if cit1.title and cit2.title:
            title_similarity = self._calculate_string_similarity(
                cit1.title.lower(), cit2.title.lower()
            )
            if title_similarity > 0.8:
                return True

        # 著者と年の組み合わせ
        if (
            cit1.authors
            and cit2.authors
            and cit1.year
            and cit2.year
            and cit1.year == cit2.year
        ):
            author_similarity = self._calculate_author_similarity(
                cit1.authors, cit2.authors
            )
            if author_similarity > 0.7:
                return True

        return False

    def _calculate_string_similarity(self, s1: str, s2: str) -> float:
        """文字列の類似度を計算（簡易版）"""
        if not s1 or not s2:
            return 0.0

        # 共通する単語の割合を計算
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _calculate_author_similarity(
        self, authors1: List[str], authors2: List[str]
    ) -> float:
        """著者リストの類似度を計算"""
        if not authors1 or not authors2:
            return 0.0

        matches = 0
        for author1 in authors1:
            for author2 in authors2:
                if (
                    self._calculate_string_similarity(author1.lower(), author2.lower())
                    > 0.8
                ):
                    matches += 1
                    break

        return matches / max(len(authors1), len(authors2))
