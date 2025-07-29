"""
OpenAlex API サービス - Semantic Scholarの代替として高性能な引用抽出を提供
"""
import asyncio
import re
from typing import Any, Dict, List, Optional
import aiohttp
from urllib.parse import quote


class OpenAlexService:
    """OpenAlex API service for academic citation extraction"""

    BASE_URL = "https://api.openalex.org"
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize OpenAlex service
        
        Args:
            email: Contact email for better rate limits (optional but recommended)
        """
        self.session = None
        self.email = email
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        if self.email:
            headers["User-Agent"] = f"theke-backend/1.0 (mailto:{self.email})"
            
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
            # タイトルを正規化
            clean_title = self._normalize_title(title)
            
            url = f"{self.BASE_URL}/works"
            params = {
                "search": clean_title,
                "per-page": 5,
                "select": "id,title,authorships,publication_year,doi,referenced_works,cited_by_count"
            }
            
            await asyncio.sleep(0.1)  # Small delay to be respectful
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    works = data.get("results", [])
                    
                    # 最も似ているタイトルを探す
                    best_match = self._find_best_title_match(title, works)
                    return best_match
                else:
                    print(f"OpenAlex search failed: {response.status}")
                    # デバッグ用にレスポンス内容を表示
                    text = await response.text()
                    print(f"Response: {text[:200]}")
                    return None
                    
        except Exception as e:
            print(f"Error searching OpenAlex: {e}")
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
            clean_doi = doi.strip().lower()
            if not clean_doi.startswith("10."):
                return None
                
            url = f"{self.BASE_URL}/works/doi:{clean_doi}"
            params = {
                "select": "id,title,authorships,publication_year,doi,referenced_works,cited_by_count"
            }
            
            await asyncio.sleep(0.1)  # Small delay to be respectful
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"OpenAlex DOI lookup failed: {response.status}")
                    return None
                    
        except Exception as e:
            print(f"Error getting work by DOI: {e}")
            return None

    async def get_work_references(self, work_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        論文の参考文献を取得
        
        Args:
            work_id: OpenAlex work ID
            limit: 取得する参考文献の最大数
            
        Returns:
            参考文献のリスト
        """
        try:
            # referenced_worksのIDリストを使って詳細情報を取得
            work_url = f"{self.BASE_URL}/works/{work_id}"
            work_params = {"select": "referenced_works"}
            
            referenced_work_ids = []
            async with self.session.get(work_url, params=work_params) as response:
                if response.status == 200:
                    work_data = await response.json()
                    referenced_work_ids = work_data.get("referenced_works", [])[:limit]
                else:
                    print(f"Failed to get referenced works: {response.status}")
                    return []
            
            if not referenced_work_ids:
                return []
            
            # 参考文献の詳細情報を一括取得
            references = []
            batch_size = 50  # OpenAlexの推奨バッチサイズ
            
            for i in range(0, len(referenced_work_ids), batch_size):
                batch_ids = referenced_work_ids[i:i + batch_size]
                batch_references = await self._get_works_batch(batch_ids)
                references.extend(batch_references)
            
            return references
            
        except Exception as e:
            print(f"Error getting work references: {e}")
            return []

    async def _get_works_batch(self, work_ids: List[str]) -> List[Dict[str, Any]]:
        """
        複数の論文情報を一件ずつ取得（バッチリクエストの代替）
        
        Args:
            work_ids: OpenAlex work IDのリスト
            
        Returns:
            論文情報のリスト
        """
        results = []
        
        # バッチサイズを制限してエラーを回避
        for work_id in work_ids[:20]:  # 最大20件まで
            try:
                # フルURLから ID部分を抽出
                if "/" in work_id:
                    clean_id = work_id.split("/")[-1]
                else:
                    clean_id = work_id
                
                url = f"{self.BASE_URL}/works/{clean_id}"
                params = {
                    "select": "id,title,authorships,publication_year,doi,cited_by_count"
                }

                await asyncio.sleep(0.1)  # Small delay to be respectful
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        work_data = await response.json()
                        results.append(work_data)
                    else:
                        print(f"Single work request failed for {clean_id}: {response.status}")
                        continue

            except Exception as e:
                print(f"Error getting single work {work_id}: {e}")
                continue
        
        return results

    def _normalize_title(self, title: str) -> str:
        """タイトルを検索用に正規化"""
        # 特殊文字を除去し、複数の空白を単一の空白に置換
        normalized = re.sub(r'[^\w\s]', ' ', title)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _find_best_title_match(self, target_title: str, works: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """タイトルの類似度で最適なマッチを探す"""
        if not works:
            return None
            
        best_match = None
        best_score = 0.0
        
        target_words = set(self._normalize_title(target_title).lower().split())
        
        for work in works:
            work_title = work.get("title", "")
            if not work_title:
                continue
                
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

    def _format_authors(self, authorships: List[Dict[str, Any]]) -> List[str]:
        """著者情報をフォーマット"""
        authors = []
        for authorship in authorships:
            author = authorship.get("author", {})
            display_name = author.get("display_name")
            if display_name:
                authors.append(display_name)
        return authors

    def _extract_venue_name(self, host_venue: Optional[Dict[str, Any]]) -> Optional[str]:
        """ホストベニュー（ジャーナル）名を抽出"""
        if not host_venue:
            return None
        return host_venue.get("display_name")


async def extract_citations_from_openalex(
    paper_title: str, 
    paper_doi: Optional[str] = None,
    email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    OpenAlex APIを使って論文の引用を抽出
    
    Args:
        paper_title: 論文タイトル
        paper_doi: 論文のDOI（オプション）
        email: 連絡先メール（Rate Limit向上のため推奨）
        
    Returns:
        引用情報のリスト
    """
    async with OpenAlexService(email=email) as service:
        # 論文を検索
        work = None
        
        # DOIがある場合はDOIで検索
        if paper_doi:
            work = await service.get_work_by_doi(paper_doi)
            
        # DOIで見つからない場合はタイトルで検索
        if not work and paper_title:
            work = await service.search_work_by_title(paper_title)
            
        if not work:
            print(f"Could not find work in OpenAlex: {paper_title}")
            return []
            
        print(f"Found work in OpenAlex: {work.get('title')} (ID: {work.get('id')})")
        
        # 参考文献を取得
        work_id = work["id"].split("/")[-1]  # URL形式からIDを抽出
        references = await service.get_work_references(work_id)
        
        print(f"Found {len(references)} references in OpenAlex")
        
        # 引用形式に変換
        citations = []
        for ref in references:
            if ref.get("title"):
                # 著者情報をフォーマット
                authors = service._format_authors(ref.get("authorships", []))
                venue = service._extract_venue_name(ref.get("host_venue"))
                
                citation = {
                    "title": ref["title"],
                    "authors": authors,
                    "year": ref.get("publication_year"),
                    "journal": venue,
                    "doi": ref.get("doi"),
                    "citation_count": ref.get("cited_by_count", 0),
                    "openalex_id": ref.get("id")
                }
                citations.append(citation)
        
        return citations