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
from ..schemas.citation import ExtractionSource


@dataclass
class CitationMatch:
    """引用のマッチング結果"""

    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    confidence: float = 0.0
    source: ExtractionSource = "unknown"
    raw_text: Optional[str] = None


class EnhancedCitationExtractor:
    """強化された引用抽出器"""

    def __init__(self):
        self.semantic_scholar = None

    async def __aenter__(self):
        # Note: SemanticScholarService not available, using None for now
        self.semantic_scholar = None
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
            # Semantic Scholar service not available
            if not self.semantic_scholar:
                print("Semantic Scholar service not available")
                return []

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
                        source="pdf_extraction",
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

            # 大幅に強化された引用パターン（多言語・多形式対応）
            citation_patterns = [
                # IEEE/ACM スタイル: [1] Author, "Title," Journal, vol. X, no. Y, pp. Z-W, Year.
                (
                    r"\[(\d+)\]\s*([^,""]+),\s*[""\"']([^""\"']+)[""\"'],\s*([^,]+),(?:[^,]*,)*\s*(\d{4})",
                    ["number", "authors", "title", "journal", "year"],
                ),
                
                # より柔軟な番号付き形式: [1] Authors. Title. Journal (Year)
                (
                    r"\[(\d+)\]\s*([^.]+?)\.\s*([^.]+?)\.\s*([^.(\n]+?)(?:\s*\((\d{4})\)|(\d{4}))",
                    ["number", "authors", "title", "journal", "year1", "year2"],
                ),
                
                # 番号付き形式（年末尾）: [1] Authors. Title. Journal. Year.
                (
                    r"\[(\d+)\]\s*([^.]+?)\.\s*([^.]+?)\.\s*([^.]+?)\.\s*(\d{4})",
                    ["number", "authors", "title", "journal", "year"],
                ),
                
                # APA スタイル: Author, A. (Year). Title. Journal, Volume(Issue), pages.
                (
                    r"([^()]+?)\s*\((\d{4})\)\.\s*([^.]+?)\.\s*([^,.\n]+?)(?:,\s*\d+(?:\(\d+\))?(?:,\s*\d+[-–]\d+)?)?\\.?",
                    ["authors", "year", "title", "journal"],
                ),
                
                # Vancouver スタイル: 1. Author A. Title. Journal Year;Volume:pages.
                (
                    r"(\d+)\.\s*([^.]+?)\.\s*([^.]+?)\.\s*([^.\n;]+?)\s+(\d{4})",
                    ["number", "authors", "title", "journal", "year"],
                ),
                
                # MLA スタイル: Author, First. "Title." Journal, vol. X, no. Y, Year, pp. Z-W.
                (
                    r"([^,]+),\s*[^.]*\.\s*[""\"']([^""\"']+)[""\"']\.\s*([^,]+),(?:[^,]*,)*\s*(\d{4})",
                    ["authors", "title", "journal", "year"],
                ),
                
                # 日本語論文形式: 著者: "タイトル", 雑誌名, Vol.X, No.Y, pp.Z-W (年)
                (
                    r"([^:\uff1a]+)[\uff1a:]\s*[""\"']([^""\"']+)[""\"'],\s*([^,\uff0c]+),[^,(\uff08]*\((\d{4})\)",
                    ["authors", "title", "journal", "year"],
                ),
                
                # シンプルな括弧年形式: Author et al. (Year) Title. Journal.
                (
                    r"([^()]+?)\s*\((\d{4})\)\s*([^.]+?)\.\s*([^.\n]+?)\\.?",
                    ["authors", "year", "title", "journal"],
                ),
                
                # 番号付き簡易形式: [X] Author, Title, Journal, Year
                (
                    r"\[(\d+)\]\s*([^,]+),\s*([^,]+),\s*([^,\n]+),\s*(\d{4})",
                    ["number", "authors", "title", "journal", "year"],
                ),
                
                # DOI付き形式: Author (Year) Title. Journal. doi:...
                (
                    r"([^()]+?)\s*\((\d{4})\)\s*([^.]+?)\.\s*([^.\n]+?)\.[^\n]*doi[:\s]*([^\s\n]+)",
                    ["authors", "year", "title", "journal", "doi"],
                ),
                
                # URL付き形式
                (
                    r"([^()]+?)\s*\((\d{4})\)\s*([^.]+?)\.\s*([^.\n]+?)\.[^\n]*(?:https?://[^\s\n]+|www\.[^\s\n]+)",
                    ["authors", "year", "title", "journal"],
                ),
                
                # 緩い形式（最後のフォールバック）: First Author et al., Title, Year
                (
                    r"([A-Z][a-z]+(?:\s+et\s+al\.?|\s+[A-Z]\.[A-Z]?\\.?)*),\s*([^,]{10,}),\s*(?:[^,]*,)*\s*(\d{4})",
                    ["authors", "title", "year"],
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

                        # 最低限の情報があるかチェック（より柔軟に）
                        if "title" in citation_data and ("year" in citation_data or "year1" in citation_data or "year2" in citation_data or "authors" in citation_data):
                            authors_str = citation_data.get("authors", "")
                            title = citation_data["title"]
                            year = None
                            
                            # 年の情報を複数のフィールドから取得
                            year_candidates = [
                                citation_data.get("year"),
                                citation_data.get("year1"), 
                                citation_data.get("year2")
                            ]
                            
                            for year_candidate in year_candidates:
                                if year_candidate:
                                    try:
                                        year_int = int(year_candidate)
                                        # 年の妥当性チェック
                                        if 1900 <= year_int <= 2030:
                                            year = year_int
                                            break
                                    except ValueError:
                                        continue
                            
                            journal = citation_data.get("journal", "")
                            doi = citation_data.get("doi", "")

                            # タイトルの詳細クリーンアップ
                            title = self._clean_title(title)
                            
                            # 短すぎる、または無効なタイトルをスキップ
                            if len(title) < 8 or self._is_invalid_title(title):
                                continue

                            # 著者名を解析
                            authors = self._parse_authors(authors_str)
                            
                            # ジャーナル名をクリーンアップ
                            journal = self._clean_journal_name(journal)

                            # 信頼性スコアを動的に計算
                            confidence = self._calculate_extraction_confidence(
                                title, authors, year, journal, doi, match.group(0)
                            )
                            
                            citation = CitationMatch(
                                title=title,
                                authors=authors,
                                year=year,
                                journal=journal,
                                doi=doi,
                                confidence=confidence,
                                source="pdf_extraction",
                                raw_text=match.group(0)[:300],  # デバッグ用
                            )
                            citations.append(citation)
                            extracted_count += 1

                    except (ValueError, IndexError) as e:
                        print(f"Error parsing citation: {e}")
                        continue

            print(f"Regex extraction found {extracted_count} citations from {len(references_section) if references_section else 0} chars")
            
            # 抽出率が低い場合の警告
            if references_section and len(references_section) > 1000 and extracted_count < 5:
                print("Warning: Low extraction rate. The reference section might have unusual formatting.")

            # 重複除去
            unique_citations = self._deduplicate_citations(citations)
            print(f"After deduplication: {len(unique_citations)} citations")
            
            # 信頼性でソート
            unique_citations.sort(key=lambda x: x.confidence, reverse=True)

            return unique_citations

        except Exception as e:
            print(f"Error in regex extraction: {e}")
            return []

    def _find_references_section(self, text: str) -> Optional[str]:
        """テキストから参考文献セクションを抽出（改良版 - 後半を優先）"""
        print("Searching for references section...")
        
        # 参考文献セクションの開始パターン（見出し形式考慮）
        patterns = [
            # 標準形式
            r"(?i)(?:^|\n)\s*references?\s*\n",
            r"(?i)(?:^|\n)\s*bibliography\s*\n", 
            r"(?i)(?:^|\n)\s*works\s+cited\s*\n",
            
            # 番号付き見出し
            r"(?i)(?:^|\n)\s*\d+\.?\s*references?\s*\n",
            r"(?i)(?:^|\n)\s*\d+\.\d+\.?\s*references?\s*\n",  # 2.1 References
            
            # 大文字見出し形式
            r"(?:^|\n)\s*REFERENCES?\s*\n",
            r"(?:^|\n)\s*BIBLIOGRAPHY\s*\n",
            r"(?:^|\n)\s*WORKS\s+CITED\s*\n",
            
            # 装飾文字（アスタリスクや等号など）
            r"(?i)(?:^|\n)\s*[*=\-_]{2,}\s*references?\s*[*=\-_]{2,}\s*\n",
            r"(?i)(?:^|\n)\s*references?\s*[*=\-_]{2,}\s*\n",
            r"(?i)(?:^|\n)\s*[*=\-_]{2,}\s*references?\s*\n",
            
            # 角括弧や丸括弧で囲まれた形式
            r"(?i)(?:^|\n)\s*\[?\s*references?\s*\]?\s*\n",
            r"(?i)(?:^|\n)\s*\(\s*references?\s*\)\s*\n",
            
            # 余分な空白や記号が入った形式
            r"(?i)(?:^|\n)\s*r\s*e\s*f\s*e\s*r\s*e\s*n\s*c\s*e\s*s?\s*\n",  # 文字間にスペース
            r"(?i)(?:^|\n)\s*references?\s*[:\.]\s*\n",  # コロンやピリオド付き
            
            # センタリングされた見出し（前後に空白）
            r"(?i)(?:^|\n)\s{3,}references?\s{3,}\n",
            r"(?i)(?:^|\n)\s{3,}bibliography\s{3,}\n",
            
            # 日本語形式
            r"(?:^|\n)\s*参考文献\s*\n",
            r"(?:^|\n)\s*引用文献\s*\n",
            r"(?:^|\n)\s*文\s*献\s*\n",  # 文字間スペース
            r"(?:^|\n)\s*【参考文献】\s*\n",  # 角括弧
            r"(?:^|\n)\s*（参考文献）\s*\n",  # 丸括弧
            r"(?:^|\n)\s*\d+\.?\s*参考文献\s*\n",
            
            # その他の言語
            r"(?i)(?:^|\n)\s*références\s*\n",      # フランス語
            r"(?i)(?:^|\n)\s*literatur\s*\n",       # ドイツ語  
            r"(?i)(?:^|\n)\s*bibliografia\s*\n",    # スペイン語・イタリア語
            r"(?i)(?:^|\n)\s*литература\s*\n",      # ロシア語
        ]

        # 全てのマッチを見つける
        all_matches = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                all_matches.append((match, pattern))

        if not all_matches:
            print("No references section found, trying citation-dense fallback")
            return self._find_citation_dense_section(text)

        # 文書の後半75%の範囲内で最も早く現れるマッチを選択
        text_length = len(text)
        threshold = text_length * 0.25  # 最初の25%は無視
        
        # 後半のマッチを優先
        valid_matches = [(match, pattern) for match, pattern in all_matches 
                        if match.start() > threshold]
        
        if not valid_matches:
            # 後半になければ全体で最後のマッチを使用
            print("No references in latter part, using last occurrence")
            best_match, best_pattern = all_matches[-1]
        else:
            # 後半で最も早く現れるマッチ
            best_match, best_pattern = min(valid_matches, key=lambda x: x[0].start())
        
        start = best_match.end()
        position_percent = start / text_length * 100
        print(f"Found references at position {start} ({position_percent:.1f}% through document)")
        
        # セクション終了位置を探す
        end_patterns = [
            r"(?i)(?:^|\n)\s*(?:appendix|appendices)\s*(?:\n|$)",
            r"(?i)(?:^|\n)\s*(?:acknowledgments?|acknowledgements?)\s*(?:\n|$)",
            r"(?i)(?:^|\n)\s*(?:author\s+information|funding|data\s+availability)\s*(?:\n|$)",
            r"(?:^|\n)\s*(?:付録|謝辞|著者情報)\s*(?:\n|$)",
        ]

        end_pos = len(text)
        for end_pattern in end_patterns:
            end_match = re.search(end_pattern, text[start:])
            if end_match:
                potential_end = start + end_match.start()
                if potential_end - start > 500:  # 最低500文字
                    end_pos = potential_end
                    print(f"Found end section, references length: {end_pos - start}")
                    break

        references_section = text[start:end_pos]
        
        # 引用密度をチェック（品質確認）
        citation_indicators = len(re.findall(r'\[\d+\]|\(\d{4}\)|et al\.', references_section))
        word_count = len(references_section.split())
        density = citation_indicators / max(word_count, 1)
        
        print(f"References section: {len(references_section)} chars, density: {density:.3f}")
        
        # 密度が非常に低い場合はフォールバック
        if density < 0.005 and len(references_section) > 1000:
            print("Low citation density, trying fallback method")
            fallback = self._find_citation_dense_section(text)
            if fallback:
                return fallback
        
        return references_section if len(references_section) > 100 else None

    def _parse_authors(self, authors_str: str) -> List[str]:
        """著者文字列を個別の著者リストに分解（多言語対応）"""
        if not authors_str or authors_str.strip() == "":
            return []
        
        # 一般的な区切り文字を統一
        authors_str = re.sub(r'\s+and\s+|\s*&\s*|\s*；\s*|\s*;\s*', ', ', authors_str, flags=re.IGNORECASE)
        authors_str = re.sub(r'\s*、\s*', ', ', authors_str)  # 日本語の読点
        
        # カンマで分割
        authors = [author.strip() for author in authors_str.split(",") if author.strip()]
        
        # 各著者名をクリーンアップ
        cleaned_authors = []
        for author in authors:
            # 番号や括弧内情報を除去
            author = re.sub(r'\[\d+\]|\(\d+\)', '', author)
            # 余分な記号を除去
            author = re.sub(r'^[.,:;"\']+|[.,:;"\']+$', '', author)
            # 余分な空白を整理
            author = re.sub(r'\s+', ' ', author).strip()
            
            # 妥当性チェック
            if (len(author) > 2 and 
                not author.lower() in ['et al', 'et al.', 'others', 'など'] and
                not re.match(r'^\d+$', author)):
                
                # 名前の形式を正規化
                author = self._normalize_author_name(author)
                if author:
                    cleaned_authors.append(author)
        
        return cleaned_authors[:15]  # 最大15人まで
    
    def _normalize_author_name(self, name: str) -> Optional[str]:
        """著者名を正規化"""
        # 既に正規化されている場合
        if len(name.split()) <= 4 and not re.search(r'[0-9]{3,}', name):
            return name
        
        # 長すぎる場合は無効とみなす
        if len(name) > 50:
            return None
            
        # 特殊文字が多すぎる場合は無効
        special_char_ratio = len(re.findall(r'[^a-zA-Z\s.-]', name)) / max(len(name), 1)
        if special_char_ratio > 0.3:
            return None
            
        return name
    
    def _clean_title(self, title: str) -> str:
        """タイトルをクリーンアップ"""
        # 引用符を除去
        title = re.sub(r'^["""\'''][\s]*|[\s]*["""\''']$', '', title)
        # 末尾の句読点を整理
        title = re.sub(r'[.,:;]+$', '', title)
        # 複数の空白を単一に
        title = re.sub(r'\s+', ' ', title)
        # 先頭・末尾の空白除去
        title = title.strip()
        
        return title
    
    def _clean_journal_name(self, journal: str) -> str:
        """ジャーナル名をクリーンアップ"""
        if not journal:
            return ""
            
        # 巻号情報を除去
        journal = re.sub(r',?\s*(?:vol\.?|volume)\s*\d+.*$', '', journal, flags=re.IGNORECASE)
        journal = re.sub(r',?\s*\d+\s*\(\d+\).*$', '', journal)
        # 末尾の句読点を除去
        journal = re.sub(r'[.,:;]+$', '', journal)
        # 空白整理
        journal = re.sub(r'\s+', ' ', journal).strip()
        
        return journal
    
    def _is_invalid_title(self, title: str) -> bool:
        """無効なタイトルかどうかチェック"""
        # 数字だけ
        if re.match(r'^\d+$', title):
            return True
        # URLっぽい
        if 'http' in title.lower() or 'www.' in title.lower():
            return True
        # DOIっぽい
        if title.lower().startswith('doi:') or title.startswith('10.'):
            return True
        # ページ番号っぽい
        if re.match(r'^pp?\.?\s*\d', title.lower()):
            return True
        # 巻号情報っぽい
        if re.match(r'^vol\.?\s*\d|^\d+\s*\(\d+\)', title.lower()):
            return True
        
        return False
    
    def _calculate_extraction_confidence(self, title: str, authors: List[str], 
                                       year: Optional[int], journal: str, 
                                       doi: str, raw_text: str) -> float:
        """抽出の信頼性スコアを計算"""
        confidence = 0.3  # ベーススコア
        
        # タイトルの質
        if len(title) > 15:
            confidence += 0.2
        if len(title) > 30:
            confidence += 0.1
        
        # 著者情報
        if authors:
            confidence += 0.15
            if len(authors) > 1:
                confidence += 0.05
        
        # 年の有無
        if year:
            confidence += 0.15
        
        # ジャーナル情報
        if journal and len(journal) > 5:
            confidence += 0.1
        
        # DOIの有無
        if doi:
            confidence += 0.1
        
        # raw_textの構造的特徴
        if '[' in raw_text and ']' in raw_text:
            confidence += 0.05  # 番号付き引用
        if '(' in raw_text and ')' in raw_text:
            confidence += 0.05  # 括弧付き年
        
        return min(confidence, 0.9)  # 最大0.9

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
