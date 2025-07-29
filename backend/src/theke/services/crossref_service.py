"""
Crossref API サービス - 公式メタデータベースからの引用抽出
"""
import asyncio
import re
from typing import Any, Dict, List, Optional
import aiohttp
from urllib.parse import quote


class CrossrefService:
    """Crossref API service for academic citation extraction"""

    BASE_URL = "https://api.crossref.org"
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize Crossref service
        
        Args:
            email: Contact email for better rate limits (recommended)
        """
        self.session = None
        self.email = email
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        headers = {
            "User-Agent": "theke-backend/1.0 (https://github.com/theke/backend; mailto:theke@example.com)"
        }
        if self.email:
            headers["User-Agent"] = f"theke-backend/1.0 (https://github.com/theke/backend; mailto:{self.email})"
            
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_work_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        タイトルで論文を検索
        
        Args:
            title: 論文タイトル
            
        Returns:
            論文情報または None
        """
        try:
            url = f"{self.BASE_URL}/works"
            params = {
                "query.title": title,
                "rows": 5
            }
            
            if self.email:
                params["mailto"] = self.email
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    
                    # 最も似ているタイトルを探す
                    best_match = self._find_best_title_match(title, items)
                    return best_match
                else:
                    print(f"Crossref search failed: {response.status}")
                    return None
                    
        except Exception as e:
            print(f"Error searching Crossref: {e}")
            return None

    async def get_work_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        DOIで論文情報を取得
        
        Args:
            doi: DOI
            
        Returns:
            論文情報または None
        """
        try:
            # DOIの正規化
            clean_doi = doi.strip()
            if clean_doi.startswith("http"):
                # HTTPSのDOI URLから DOI部分を抽出
                clean_doi = clean_doi.split("/")[-2] + "/" + clean_doi.split("/")[-1]
            elif clean_doi.startswith("doi:"):
                # doi: プレフィックスを削除
                clean_doi = clean_doi[4:]
            
            # DOI形式の検証
            if not clean_doi.startswith("10."):
                print(f"Invalid DOI format: {clean_doi}")
                return None
            
            url = f"{self.BASE_URL}/works/{clean_doi}"
            params = {}
            
            if self.email:
                params["mailto"] = self.email
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message")
                else:
                    print(f"Crossref DOI lookup failed: {response.status}")
                    # デバッグ用にレスポンス内容を表示
                    text = await response.text()
                    print(f"Response: {text[:200]}")
                    return None
                    
        except Exception as e:
            print(f"Error getting work by DOI: {e}")
            return None

    async def get_work_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        論文の参考文献を取得
        
        Args:
            doi: 論文のDOI
            
        Returns:
            参考文献のリスト
        """
        try:
            work = await self.get_work_by_doi(doi)
            if not work:
                return []
            
            references = work.get("reference", [])
            
            # 参考文献をフォーマット
            formatted_references = []
            for ref in references:
                formatted_ref = self._format_reference(ref)
                if formatted_ref:
                    formatted_references.append(formatted_ref)
            
            return formatted_references
            
        except Exception as e:
            print(f"Error getting references from Crossref: {e}")
            return []

    async def search_reference_by_text(self, reference_text: str) -> Optional[Dict[str, Any]]:
        """
        参考文献のテキストで論文を検索（参考文献マッチング）
        
        Args:
            reference_text: 参考文献の全文
            
        Returns:
            マッチした論文情報または None
        """
        try:
            url = f"{self.BASE_URL}/works"
            params = {
                "query.bibliographic": reference_text,
                "rows": 2  # 最初の2件で十分
            }
            
            if self.email:
                params["mailto"] = self.email
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    
                    # スコアが十分高い場合のみ返す
                    if items and items[0].get("score", 0) > 0.8:
                        return items[0]
                    
                return None
                    
        except Exception as e:
            print(f"Error in reference matching: {e}")
            return None

    def _find_best_title_match(self, target_title: str, works: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """タイトルの類似度で最適なマッチを探す"""
        if not works:
            return None
            
        best_match = None
        best_score = 0.0
        
        target_words = set(self._normalize_title(target_title).lower().split())
        
        for work in works:
            work_titles = work.get("title", [])
            if not work_titles:
                continue
                
            work_title = work_titles[0] if isinstance(work_titles, list) else str(work_titles)
            work_words = set(self._normalize_title(work_title).lower().split())
            
            # Jaccard類似度を計算
            if target_words and work_words:
                intersection = len(target_words.intersection(work_words))
                union = len(target_words.union(work_words))
                score = intersection / union if union > 0 else 0.0
                
                if score > best_score:
                    best_score = score
                    best_match = work
        
        # 類似度が70%以上の場合のみ返す
        return best_match if best_score >= 0.7 else None

    def _normalize_title(self, title: str) -> str:
        """タイトルを検索用に正規化"""
        normalized = re.sub(r'[^\w\s]', ' ', title)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _format_reference(self, reference: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """参考文献をフォーマット"""
        try:
            # 基本情報を抽出
            title = None
            if "article-title" in reference:
                title = reference["article-title"]
            elif "volume-title" in reference:
                title = reference["volume-title"]
            
            # 著者情報を抽出
            authors = []
            if "author" in reference:
                for author in reference["author"]:
                    if "family" in author:
                        name_parts = []
                        if "given" in author:
                            name_parts.append(author["given"])
                        name_parts.append(author["family"])
                        authors.append(" ".join(name_parts))
            
            # 年を抽出
            year = None
            if "year" in reference:
                year = int(reference["year"])
            
            # ジャーナル名を抽出
            journal = None
            if "journal-title" in reference:
                journal = reference["journal-title"]
            elif "volume-title" in reference:
                journal = reference["volume-title"]
            
            # DOIを抽出
            doi = reference.get("DOI")
            
            # タイトルが必須
            if not title:
                return None
            
            return {
                "title": title,
                "authors": authors,
                "year": year,
                "journal": journal,
                "doi": doi,
                "raw_reference": reference.get("unstructured", "")
            }
            
        except Exception as e:
            print(f"Error formatting reference: {e}")
            return None

    def _format_authors(self, authors: List[Dict[str, Any]]) -> List[str]:
        """著者情報をフォーマット"""
        formatted_authors = []
        for author in authors:
            name_parts = []
            if "given" in author:
                name_parts.append(author["given"])
            if "family" in author:
                name_parts.append(author["family"])
            if name_parts:
                formatted_authors.append(" ".join(name_parts))
        return formatted_authors

    def _extract_publication_year(self, work: Dict[str, Any]) -> Optional[int]:
        """出版年を抽出"""
        # published-print または published-online から年を取得
        for date_type in ["published-print", "published-online"]:
            if date_type in work:
                date_parts = work[date_type].get("date-parts")
                if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                    try:
                        return int(date_parts[0][0])
                    except (ValueError, IndexError):
                        continue
        return None


async def extract_citations_from_crossref(
    paper_title: str, 
    paper_doi: Optional[str] = None,
    email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Crossref APIを使って論文の引用を抽出
    
    Args:
        paper_title: 論文タイトル
        paper_doi: 論文のDOI（オプション）
        email: 連絡先メール（Rate Limit向上のため推奨）
        
    Returns:
        引用情報のリスト
    """
    async with CrossrefService(email=email) as service:
        # 論文を検索
        work = None
        
        # DOIがある場合はDOIで検索
        if paper_doi:
            work = await service.get_work_by_doi(paper_doi)
            
        # DOIで見つからない場合はタイトルで検索
        if not work and paper_title:
            work = await service.search_work_by_title(paper_title)
            
        if not work:
            print(f"Could not find work in Crossref: {paper_title}")
            return []
            
        work_doi = work.get("DOI")
        if not work_doi:
            print("Work found but no DOI available")
            return []
            
        print(f"Found work in Crossref: {work.get('title', [''])[0]} (DOI: {work_doi})")
        
        # 参考文献を取得
        references = await service.get_work_references(work_doi)
        
        print(f"Found {len(references)} references in Crossref")
        
        # 引用形式に変換
        citations = []
        for ref in references:
            citation = {
                "title": ref.get("title"),
                "authors": ref.get("authors", []),
                "year": ref.get("year"),
                "journal": ref.get("journal"),
                "doi": ref.get("doi"),
                "raw_reference": ref.get("raw_reference", "")
            }
            citations.append(citation)
        
        return citations