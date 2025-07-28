import PyPDF2
from typing import Dict, Any, Optional
import re
from pathlib import Path
from .llm_service import get_llm_provider
from .semantic_scholar_service import SemanticScholarService


async def extract_metadata_from_pdf(file, use_llm: bool = False) -> Dict[str, Any]:
    """Extract metadata and text from uploaded PDF file"""
    try:
        # Read PDF content
        content = await file.read()
        
        # Reset file pointer for potential reuse
        file.file.seek(0)
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(file.file)
        
        # Extract text from first few pages
        text_content = ""
        max_pages = min(5 if use_llm else 3, len(pdf_reader.pages))
        
        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n"
        
        if use_llm and text_content.strip():
            # Use LLM to extract metadata
            metadata = await _extract_metadata_with_llm(text_content)
        else:
            # Use traditional rule-based extraction
            metadata = {}
            if pdf_reader.metadata:
                metadata.update({
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'authors': _parse_authors(pdf_reader.metadata.get('/Author', '')),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'creator': pdf_reader.metadata.get('/Creator', ''),
                })
            
            # Try to extract title and abstract from text if not in metadata
            if not metadata.get('title'):
                title = _extract_title_from_text(text_content)
                if title:
                    metadata['title'] = title
            
            if not metadata.get('authors'):
                authors = _extract_authors_from_text(text_content)
                if authors:
                    metadata['authors'] = authors
            
            abstract = _extract_abstract_from_text(text_content)
            if abstract:
                metadata['abstract'] = abstract
            
            year = _extract_year_from_text(text_content)
            if year:
                metadata['year'] = year

            doi = _extract_doi_from_text(text_content)
            if doi:
                metadata['doi'] = doi
            elif metadata.get('title') and metadata.get('authors'):
                async with SemanticScholarService() as service:
                    doi_from_api = await service.find_doi_by_title_and_authors(
                        metadata['title'], metadata['authors']
                    )
                    if doi_from_api:
                        metadata['doi'] = doi_from_api
        
        # Ensure we have at least a title
        if not metadata.get('title'):
            metadata['title'] = Path(file.filename).stem
        
        if not metadata.get('authors'):
            metadata['authors'] = []
        
        return metadata
        
    except Exception as e:
        # Fallback to filename-based metadata
        return {
            'title': Path(file.filename).stem,
            'authors': [],
            'abstract': f"Error extracting PDF metadata: {str(e)}"
        }


async def _extract_metadata_with_llm(text_content: str) -> Dict[str, Any]:
    """Extract metadata using LLM"""
    try:
        provider = get_llm_provider()
        
        prompt = """
        以下の学術論文のテキストから、以下の情報をJSON形式で抽出してください。見つからない場合はnullを返してください。

        必要な情報:
        - title: 論文のタイトル（文字列）
        - authors: 著者のリスト（文字列の配列）
        - year: 発行年（数値）
        - journal: ジャーナル名または学会名（文字列）
        - abstract: アブストラクト（文字列）
        - doi: DOI（文字列）
        - keywords: キーワード（文字列の配列）

        JSONのみを返してください。他のテキストは含めないでください。

        論文テキスト:
        """
        
        # Use the provider's generate_summary method with custom prompt
        if hasattr(provider, 'client'):
            # For OpenAI
            if 'openai' in str(type(provider)):
                response = await provider.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text_content[:8000]}  # Limit text length
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
                result = response.choices[0].message.content.strip()
            # For Anthropic
            else:
                message = await provider.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": f"{prompt}\n\n{text_content[:100000]}"}
                    ]
                )
                result = message.content[0].text.strip()
            
            # Parse JSON result
            import json
            try:
                # Remove any markdown code blocks
                if result.startswith('```'):
                    result = result.split('```')[1]
                    if result.startswith('json'):
                        result = result[4:]
                
                metadata = json.loads(result)
                
                # Clean up the metadata
                cleaned_metadata = {}
                if metadata.get('title') and metadata['title'] != 'null':
                    cleaned_metadata['title'] = metadata['title']
                if metadata.get('authors') and isinstance(metadata['authors'], list):
                    cleaned_metadata['authors'] = [author for author in metadata['authors'] if author and author != 'null']
                if metadata.get('year') and isinstance(metadata['year'], int):
                    cleaned_metadata['year'] = metadata['year']
                if metadata.get('journal') and metadata['journal'] != 'null':
                    cleaned_metadata['journal'] = metadata['journal']
                if metadata.get('abstract') and metadata['abstract'] != 'null':
                    cleaned_metadata['abstract'] = metadata['abstract']
                if metadata.get('doi') and metadata['doi'] != 'null':
                    cleaned_metadata['doi'] = metadata['doi']
                if metadata.get('keywords') and isinstance(metadata['keywords'], list):
                    cleaned_metadata['keywords'] = [kw for kw in metadata['keywords'] if kw and kw != 'null']
                
                return cleaned_metadata
                
            except json.JSONDecodeError:
                # Fallback to empty metadata if JSON parsing fails
                return {}
        
        return {}
        
    except Exception as e:
        print(f"LLM metadata extraction error: {str(e)}")
        return {}


def _parse_authors(author_string: str) -> list[str]:
    """Parse author string into list of authors"""
    if not author_string:
        return []
    
    # Common separators for authors
    separators = [';', ',', ' and ', ' & ']
    authors = [author_string]
    
    for sep in separators:
        new_authors = []
        for author in authors:
            new_authors.extend([a.strip() for a in author.split(sep)])
        authors = new_authors
    
    return [a for a in authors if a]


def _extract_title_from_text(text: str) -> Optional[str]:
    """Extract title from PDF text"""
    lines = text.split('\n')
    
    # Look for title in first few lines
    for i, line in enumerate(lines[:10]):
        line = line.strip()
        if len(line) > 10 and len(line) < 200:  # Reasonable title length
            # Check if it looks like a title (not abstract, introduction, etc.)
            if not re.match(r'^(abstract|introduction|keywords)', line.lower()):
                return line
    
    return None


def _extract_authors_from_text(text: str) -> list[str]:
    """Extract authors from PDF text"""
    lines = text.split('\n')
    
    # Look for author patterns in first few lines
    for line in lines[:15]:
        line = line.strip()
        # Look for patterns like "Author1, Author2 and Author3"
        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', line):
            # Check if it contains email or affiliation markers
            if '@' in line or 'university' in line.lower() or 'department' in line.lower():
                continue
            
            # Extract potential authors
            authors = _parse_authors(line)
            if authors and len(authors) <= 10:  # Reasonable number of authors
                return authors
    
    return []


def _extract_abstract_from_text(text: str) -> Optional[str]:
    """Extract abstract from PDF text"""
    # Look for abstract section
    abstract_match = re.search(
        r'abstract[:\s]+(.*?)(?=\n\n|\nintroduction|\nkeywords|\n1\.|\n\d+\.)',
        text.lower(),
        re.DOTALL | re.IGNORECASE
    )
    
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        # Clean up the abstract
        abstract = re.sub(r'\s+', ' ', abstract)  # Normalize whitespace
        if len(abstract) > 50 and len(abstract) < 2000:  # Reasonable abstract length
            return abstract
    
    return None


def _extract_year_from_text(text: str) -> Optional[int]:
    """Extract publication year from PDF text"""
    # Look for 4-digit years (1900-2030)
    year_matches = re.findall(r'\b(19\d{2}|20[0-3]\d)\b', text)
    
    if year_matches:
        # Return the most recent reasonable year found
        years = [int(year) for year in year_matches]
        current_year = 2024
        valid_years = [year for year in years if 1950 <= year <= current_year + 1]
        
        if valid_years:
            return max(valid_years)
    
    return None


def _extract_doi_from_text(text: str) -> Optional[str]:
    """Extract DOI from PDF text."""
    # A common regex for DOIs.
    doi_regex = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
    
    match = re.search(doi_regex, text, re.IGNORECASE)
    
    if match:
        return match.group(0).strip('.,')
        
    return None


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


async def extract_text_from_pdf_file(pdf_path: str) -> str:
    """Async version of extract_text_from_pdf"""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None, extract_text_from_pdf, pdf_path
    )


def get_pdf_page_count(pdf_path: str) -> int:
    """Get number of pages in PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception:
        return 0