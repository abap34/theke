"""
改善された引用抽出サービス
本文からの抽出とSemantic Scholarからの抽出を組み合わせて高精度な引用抽出を実現
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from .llm_service import get_llm_provider, AnthropicProvider
from .pdf_processor import extract_text_from_pdf_file


@dataclass
class CitationMatch:
    """引用のマッチング結果"""

    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    confidence: float = 0.0
    source: str = "unknown"  # "pdf", "semantic_scholar", "merged"
    raw_text: Optional[str] = None


class EnhancedCitationExtractor:
    """強化された引用抽出器"""

    def __init__(self):
        self.semantic_scholar = None

    async def __aenter__(self):
        self.semantic_scholar = SemanticScholarService()
        await self.semantic_scholar.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.semantic_scholar:
            await self.semantic_scholar.__aexit__(exc_type, exc_val, exc_tb)

    async def extract_citations_comprehensive(
        self,
        paper_title: str,
        paper_doi: Optional[str] = None,
        pdf_path: Optional[str] = None,
        preferred_source: str = "openalex",
    ) -> List[CitationMatch]:
        """
        包括的な引用抽出：複数のAPIとPDFから抽出して統合

        Args:
            paper_title: 論文タイトル
            paper_doi: 論文DOI
            pdf_path: PDFファイルパス
            preferred_source: 優先する外部ソース ("openalex", "crossref", "semantic_scholar")
        """
        print(f"Starting comprehensive citation extraction for: {paper_title}")
        print(f"Preferred source: {preferred_source}")

        # 並列で複数のソースから抽出
        tasks = []

        # 1. 優先外部ソースから抽出
        if preferred_source == "openalex":
            tasks.append(self._extract_from_openalex(paper_title, paper_doi))
        elif preferred_source == "crossref":
            tasks.append(self._extract_from_crossref(paper_title, paper_doi))
        elif preferred_source == "semantic_scholar":
            tasks.append(self._extract_from_semantic_scholar(paper_title, paper_doi))
        else:
            # デフォルトはOpenAlex
            tasks.append(self._extract_from_openalex(paper_title, paper_doi))

        # 2. PDFからの抽出（利用可能な場合）
        if pdf_path:
            tasks.append(self._extract_from_pdf(pdf_path))
        else:
            tasks.append(asyncio.create_task(self._empty_extraction()))

        # 3. フォールバック用の追加ソース（優先ソースが失敗した場合用）
        if preferred_source != "crossref":
            tasks.append(self._extract_from_crossref(paper_title, paper_doi))
        else:
            tasks.append(asyncio.create_task(self._empty_extraction()))

        external_citations, pdf_citations, fallback_citations = await asyncio.gather(
            *tasks
        )

        print(f"{preferred_source.title()} found: {len(external_citations)} citations")
        print(f"PDF extraction found: {len(pdf_citations)} citations")
        print(f"Fallback source found: {len(fallback_citations)} citations")

        # 4. すべての結果をマージして重複を除去
        # 優先順位: 外部ソース > フォールバック > PDF
        all_citations = external_citations + fallback_citations + pdf_citations
        merged_citations = self._deduplicate_citations(all_citations)

        print(
            f"After merging and deduplication: {len(merged_citations)} unique citations"
        )

        return merged_citations

    async def _extract_from_openalex(
        self, paper_title: str, paper_doi: Optional[str] = None
    ) -> List[CitationMatch]:
        """OpenAlexからの引用抽出"""
        try:
            from .openalex_service import extract_citations_from_openalex

            citations_data = await extract_citations_from_openalex(
                paper_title=paper_title,
                paper_doi=paper_doi,
                email="theke@example.com",  # 設定から取得することも可能
            )

            citations = []
            for citation_data in citations_data:
                if citation_data.get("title"):
                    citation = CitationMatch(
                        title=citation_data["title"],
                        authors=citation_data.get("authors", []),
                        year=citation_data.get("year"),
                        journal=citation_data.get("journal"),
                        doi=citation_data.get("doi"),
                        confidence=0.9,  # OpenAlexは信頼性が高い
                        source="openalex",
                    )
                    citations.append(citation)

            return citations

        except Exception as e:
            print(f"Error extracting from OpenAlex: {e}")
            return []

    async def _extract_from_crossref(
        self, paper_title: str, paper_doi: Optional[str] = None
    ) -> List[CitationMatch]:
        """Crossrefからの引用抽出"""
        try:
            from .crossref_service import extract_citations_from_crossref

            citations_data = await extract_citations_from_crossref(
                paper_title=paper_title,
                paper_doi=paper_doi,
                email="theke@example.com",  # 設定から取得することも可能
            )

            citations = []
            for citation_data in citations_data:
                if citation_data.get("title"):
                    citation = CitationMatch(
                        title=citation_data["title"],
                        authors=citation_data.get("authors", []),
                        year=citation_data.get("year"),
                        journal=citation_data.get("journal"),
                        doi=citation_data.get("doi"),
                        confidence=0.85,  # Crossrefは高信頼性
                        source="crossref",
                    )
                    citations.append(citation)

            return citations

        except Exception as e:
            print(f"Error extracting from Crossref: {e}")
            return []

    async def _extract_from_semantic_scholar(
        self, paper_title: str, paper_doi: Optional[str] = None
    ) -> List[CitationMatch]:
        """Semantic Scholarからの引用抽出（フォールバック用）"""
        try:
            # 論文を検索
            paper = None
            if paper_doi:
                paper = await self.semantic_scholar.get_paper_by_doi(paper_doi)

            if not paper and paper_title:
                paper = await self.semantic_scholar.search_paper_by_title(paper_title)

            if not paper or not paper.get("paperId"):
                print("Paper not found on Semantic Scholar")
                return []

            # 引用文献を取得
            references = await self.semantic_scholar.get_paper_references(
                paper["paperId"]
            )

            citations = []
            for ref in references:
                if ref.get("title"):
                    citation = CitationMatch(
                        title=ref["title"],
                        authors=ref.get("authors", []),
                        year=ref.get("year"),
                        journal=ref.get("venue"),
                        doi=ref.get("doi"),
                        confidence=0.8,  # 信頼性を少し下げる（Rate Limit問題のため）
                        source="semantic_scholar",
                    )
                    citations.append(citation)

            return citations

        except Exception as e:
            print(f"Error extracting from Semantic Scholar: {e}")
            return []

    async def _extract_from_pdf(self, pdf_path: str) -> List[CitationMatch]:
        """PDFからの引用抽出（LLM + 正規表現の組み合わせ）"""
        try:
            from pathlib import Path
            import os

            # PDFパスを絶対パスに変換
            if not os.path.isabs(pdf_path):
                # 相対パスの場合、現在の作業ディレクトリからの絶対パスに変換
                abs_pdf_path = os.path.abspath(pdf_path)
            else:
                abs_pdf_path = pdf_path

            # ファイル存在確認
            if not os.path.exists(abs_pdf_path):
                print(f"PDF file not found: {abs_pdf_path}")
                return []

            citations = []

            # 1. LLMを使った抽出
            llm_citations = await self._extract_with_llm(abs_pdf_path)
            citations.extend(llm_citations)

            # 2. 正規表現を使った補完抽出
            regex_citations = await self._extract_with_regex(abs_pdf_path)
            citations.extend(regex_citations)

            # 3. 重複除去
            unique_citations = self._deduplicate_citations(citations)

            return unique_citations

        except Exception as e:
            print(f"Error extracting from PDF: {e}")
            return []

    async def _extract_with_llm(self, pdf_path: str) -> List[CitationMatch]:
        """LLMを使った引用抽出"""
        try:
            provider = get_llm_provider()

            # Anthropicの場合は直接PDF処理
            if isinstance(provider, AnthropicProvider):
                citations_data = await provider.extract_citations_from_pdf(pdf_path)
            else:
                # 他のプロバイダーの場合はテキスト抽出してから処理
                text = await extract_text_from_pdf_file(pdf_path)
                citations_data = await provider.extract_citations(text)

            citations = []
            for citation_data in citations_data:
                if citation_data.get("title"):
                    citation = CitationMatch(
                        title=citation_data["title"],
                        authors=citation_data.get("authors", []),
                        year=citation_data.get("year"),
                        journal=citation_data.get("journal"),
                        doi=citation_data.get("doi"),
                        confidence=0.7,  # LLM抽出は中程度の信頼性
                        source="pdf",
                    )
                    citations.append(citation)

            return citations

        except Exception as e:
            print(f"Error in LLM extraction: {e}")
            return []

    async def _extract_with_regex(self, pdf_path: str) -> List[CitationMatch]:
        """正規表現を使った引用抽出（補完用）"""
        try:
            text = await extract_text_from_pdf_file(pdf_path)
            citations = []

            print(f"PDF text length: {len(text)} characters")

            # 参考文献セクションを探す
            references_section = self._find_references_section(text)
            if not references_section:
                print("No references section found, using full text")
                references_section = text
            else:
                print(
                    f"References section found, length: {len(references_section)} characters"
                )

            # より強化された引用パターン
            citation_patterns = [
                # [1] Author, A. (2020). Title. Journal.
                (
                    r"\[(\d+)\]\s*([^()]+)\s*\((\d{4})\)\.\s*([^.]+)\.\s*([^.\n]+)",
                    ["number", "authors", "year", "title", "journal"],
                ),
                # Author, A. (2020). Title. Journal, volume(issue), pages.
                (
                    r"([^()]+)\s*\((\d{4})\)\.\s*([^.]+)\.\s*([^,\n]+)",
                    ["authors", "year", "title", "journal"],
                ),
                # Author et al. (2020) Title. Journal.
                (
                    r"([^()]+et al\.?)\s*\((\d{4})\)\s*([^.]+)\.\s*([^.\n]+)",
                    ["authors", "year", "title", "journal"],
                ),
                # 番号なしの簡単なパターン
                (
                    r"([A-Z][a-zA-Z\s,]+)\s*\((\d{4})\)[.:]?\s*([^.]+)\.\s*([^.\n]+)",
                    ["authors", "year", "title", "journal"],
                ),
            ]

            extracted_count = 0
            for pattern, fields in citation_patterns:
                matches = re.finditer(
                    pattern, references_section, re.MULTILINE | re.DOTALL
                )
                for match in matches:
                    try:
                        citation_data = {}
                        groups = match.groups()

                        for i, field in enumerate(fields):
                            if i < len(groups) and groups[i]:
                                citation_data[field] = groups[i].strip()

                        # 最低限の情報があるかチェック
                        if "title" in citation_data and "year" in citation_data:
                            authors_str = citation_data.get("authors", "")
                            title = citation_data["title"]
                            year = int(citation_data["year"])
                            journal = citation_data.get("journal", "")

                            # タイトルのクリーンアップ
                            title = re.sub(r'^["\']|["\']$', "", title)  # 引用符除去
                            title = title.strip(".,;:")  # 句読点除去

                            # 短すぎるタイトルをスキップ
                            if len(title) < 5:
                                continue

                            # 著者名を解析
                            authors = self._parse_authors(authors_str)

                            citation = CitationMatch(
                                title=title,
                                authors=authors,
                                year=year,
                                journal=journal,
                                confidence=0.6,  # 正規表現の信頼性を少し上げる
                                source="pdf",
                                raw_text=match.group(0)[:200],  # デバッグ用に一部保存
                            )
                            citations.append(citation)
                            extracted_count += 1

                    except (ValueError, IndexError) as e:
                        print(f"Error parsing citation: {e}")
                        continue

            print(f"Regex extraction found {extracted_count} citations")

            # 重複除去
            unique_citations = self._deduplicate_citations(citations)
            print(f"After deduplication: {len(unique_citations)} citations")

            return unique_citations

        except Exception as e:
            print(f"Error in regex extraction: {e}")
            return []

    def _find_references_section(self, text: str) -> Optional[str]:
        """テキストから参考文献セクションを抽出"""
        # 一般的な参考文献セクションの開始パターン
        patterns = [
            r"(?i)references?\s*\n",
            r"(?i)bibliography\s*\n",
            r"(?i)works\s+cited\s*\n",
            r"(?i)参考文献\s*\n",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # セクション開始位置から末尾まで、または次のセクションまで
                start = match.end()

                # 次のセクション（Appendix、Acknowledgments等）を探す
                end_patterns = [
                    r"(?i)\n\s*(appendix|acknowledgments?|author|affiliation)",
                    r"\n\s*[A-Z][A-Z\s]{10,}\n",  # 大文字のセクションタイトル
                ]

                end_pos = len(text)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, text[start:])
                    if end_match:
                        end_pos = start + end_match.start()
                        break

                return text[start:end_pos]

        return None

    def _parse_authors(self, authors_str: str) -> List[str]:
        """著者文字列を個別の著者リストに分解"""
        # 一般的な著者分割パターン
        authors_str = authors_str.replace(" and ", ", ").replace(" & ", ", ")
        authors = [author.strip() for author in authors_str.split(",")]

        # クリーンアップ
        cleaned_authors = []
        for author in authors:
            author = re.sub(r"\[\d+\]", "", author)  # 番号を除去
            author = author.strip("., ")
            if author and len(author) > 2:
                cleaned_authors.append(author)

        return cleaned_authors[:10]  # 最大10人まで

    def _merge_citation_sources(
        self,
        semantic_citations: List[CitationMatch],
        pdf_citations: List[CitationMatch],
    ) -> List[CitationMatch]:
        """複数ソースからの引用をマージし、重複を除去"""
        merged = []

        # Semantic Scholarの結果を基準とする（より信頼性が高い）
        for semantic_citation in semantic_citations:
            # PDFから似たような引用を探す
            best_match = self._find_best_match(semantic_citation, pdf_citations)

            if best_match and best_match.confidence > 0.6:
                # マージして新しい引用を作成
                merged_citation = self._merge_citations(semantic_citation, best_match)
                merged.append(merged_citation)
                # マッチしたPDF引用を除去
                pdf_citations.remove(best_match)
            else:
                # マッチしなかった場合はSemantic Scholarの結果をそのまま使用
                merged.append(semantic_citation)

        # 残ったPDF引用を追加（新しく発見されたもの）
        for pdf_citation in pdf_citations:
            if pdf_citation.confidence > 0.5:  # 一定の信頼性がある場合のみ
                merged.append(pdf_citation)

        return merged

    def _find_best_match(
        self, target: CitationMatch, candidates: List[CitationMatch]
    ) -> Optional[CitationMatch]:
        """最も似ている引用を探す"""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self._calculate_similarity(target, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match:
            best_match.confidence = best_score

        return best_match

    def _calculate_similarity(
        self, citation1: CitationMatch, citation2: CitationMatch
    ) -> float:
        """2つの引用の類似度を計算"""
        scores = []

        # タイトルの類似度（最重要）
        if citation1.title and citation2.title:
            title_sim = SequenceMatcher(
                None, citation1.title.lower(), citation2.title.lower()
            ).ratio()
            scores.append(title_sim * 0.6)

        # 著者の類似度
        if citation1.authors and citation2.authors:
            author_sim = self._calculate_author_similarity(
                citation1.authors, citation2.authors
            )
            scores.append(author_sim * 0.3)

        # 年の一致
        if citation1.year and citation2.year:
            year_sim = 1.0 if citation1.year == citation2.year else 0.0
            scores.append(year_sim * 0.1)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_author_similarity(
        self, authors1: List[str], authors2: List[str]
    ) -> float:
        """著者リストの類似度を計算"""
        if not authors1 or not authors2:
            return 0.0

        # 最初の著者の姓で比較
        def get_last_name(author_name):
            parts = author_name.strip().split()
            return parts[-1].lower() if parts else ""

        authors1_lastnames = {get_last_name(author) for author in authors1}
        authors2_lastnames = {get_last_name(author) for author in authors2}

        if not authors1_lastnames or not authors2_lastnames:
            return 0.0

        intersection = len(authors1_lastnames.intersection(authors2_lastnames))
        union = len(authors1_lastnames.union(authors2_lastnames))

        return intersection / union if union > 0 else 0.0

    def _merge_citations(
        self, semantic: CitationMatch, pdf: CitationMatch
    ) -> CitationMatch:
        """2つの引用をマージして最良の情報を組み合わせ"""
        return CitationMatch(
            title=semantic.title or pdf.title,  # Semantic Scholarを優先
            authors=semantic.authors or pdf.authors,
            year=semantic.year or pdf.year,
            journal=semantic.journal or pdf.journal,
            doi=semantic.doi or pdf.doi,
            confidence=max(semantic.confidence, pdf.confidence),
            source="merged",
        )

    def _deduplicate_citations(
        self, citations: List[CitationMatch]
    ) -> List[CitationMatch]:
        """引用リストから重複を除去"""
        unique_citations = []

        for citation in citations:
            is_duplicate = False
            for unique_citation in unique_citations:
                if self._calculate_similarity(citation, unique_citation) > 0.8:
                    is_duplicate = True
                    # より高い信頼性の引用で置き換え
                    if citation.confidence > unique_citation.confidence:
                        unique_citations.remove(unique_citation)
                        unique_citations.append(citation)
                    break

            if not is_duplicate:
                unique_citations.append(citation)

        return unique_citations

    async def _empty_extraction(self) -> List[CitationMatch]:
        """空の抽出結果"""
        return []


async def extract_citations_enhanced(
    paper_title: str, paper_doi: Optional[str] = None, pdf_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    強化された引用抽出のメイン関数
    """
    async with EnhancedCitationExtractor() as extractor:
        citations = await extractor.extract_citations_comprehensive(
            paper_title, paper_doi, pdf_path
        )

        # CitationMatchをdict形式に変換
        result = []
        for citation in citations:
            result.append(
                {
                    "title": citation.title,
                    "authors": citation.authors,
                    "year": citation.year,
                    "journal": citation.journal,
                    "doi": citation.doi,
                    "confidence": citation.confidence,
                    "source": citation.source,
                }
            )

        return result
