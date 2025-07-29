import asyncio
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_summary(self, text: str, custom_prompt: Optional[str] = None, db_session: Optional[object] = None) -> str:
        pass
    
    @abstractmethod
    async def extract_citations(self, text: str) -> list[Dict[str, Any]]:
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self):
        try:
            import openai
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
                raise ValueError("OpenAI API key is not configured")
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    async def generate_summary(self, text: str, custom_prompt: Optional[str] = None, db_session: Optional[object] = None) -> str:
        if custom_prompt:
            prompt = custom_prompt
        elif db_session:
            from ..crud.setting import get_setting_value
            prompt = get_setting_value(db_session, "summary_prompt", default=settings.SUMMARY_PROMPT)
        else:
            prompt = settings.SUMMARY_PROMPT
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"以下の論文を要約してください:\n\n{text[:4000]}"}  # Limit text length
                ],
                max_tokens=1500,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def extract_citations(self, text: str) -> list[Dict[str, Any]]:
        prompt = """Extract all citations from this academic paper text. 
        Return them as a JSON list where each citation has: title, authors (list), year, journal, doi (if available).
        Only return the JSON, no other text."""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Extract citations from:\n\n{text[:6000]}"}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            import json
            result = response.choices[0].message.content.strip()
            # Try to parse as JSON
            try:
                citations = json.loads(result)
                return citations if isinstance(citations, list) else []
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            raise Exception(f"OpenAI citation extraction error: {str(e)}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self):
        try:
            import anthropic
            if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
                raise ValueError("Anthropic API key is not configured")
            self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        except ImportError:
            raise ImportError("Anthropic library not installed. Run: pip install anthropic")
    
    async def generate_summary(self, text: str, custom_prompt: Optional[str] = None, db_session: Optional[object] = None) -> str:
        if custom_prompt:
            prompt = custom_prompt
        elif db_session:
            from ..crud.setting import get_setting_value
            prompt = get_setting_value(db_session, "summary_prompt", default=settings.SUMMARY_PROMPT)
        else:
            prompt = settings.SUMMARY_PROMPT
        
        try:
            message = await self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1500,
                temperature=0.3,
                messages=[
                    {
                        "role": "user", 
                        "content": f"{prompt}\n\n以下の論文を要約してください:\n{text[:100000]}"  # Claude can handle more text
                    }
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def generate_summary_from_pdf(self, pdf_path: str, custom_prompt: Optional[str] = None, db_session: Optional[object] = None) -> str:
        """Generate summary directly from PDF using Anthropic's native PDF support"""
        if custom_prompt:
            prompt = custom_prompt
        elif db_session:
            from ..crud.setting import get_setting_value
            prompt = get_setting_value(db_session, "summary_prompt", default=settings.SUMMARY_PROMPT)
        else:
            prompt = settings.SUMMARY_PROMPT
        
        try:
            import base64
            
            # Read PDF file and encode as base64
            with open(pdf_path, 'rb') as f:
                pdf_data = base64.b64encode(f.read()).decode('utf-8')
            
            message = await self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Anthropic PDF summary generation error: {str(e)}")
    
    async def extract_citations(self, text: str) -> list[Dict[str, Any]]:
        prompt = """Extract all citations from this academic paper text. 
        Return them as a JSON list where each citation has: title, authors (list), year, journal, doi (if available).
        Only return the JSON array, no other text."""
        
        try:
            message = await self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nPaper text:\n{text[:50000]}"
                    }
                ]
            )
            
            import json
            result = message.content[0].text.strip()
            # Try to parse as JSON
            try:
                citations = json.loads(result)
                return citations if isinstance(citations, list) else []
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            raise Exception(f"Anthropic citation extraction error: {str(e)}")
    
    async def extract_citations_from_pdf(self, pdf_path: str) -> list[Dict[str, Any]]:
        """Extract citations directly from PDF using Anthropic's native PDF support"""
        prompt = """この学術論文PDFから、すべての引用文献を抽出してください。

以下のJSON形式で返してください：
```json
[
  {
    "title": "論文タイトル",
    "authors": ["著者1", "著者2"],
    "year": 2023,
    "journal": "ジャーナル名",
    "doi": "10.1000/xyz123"
  }
]
```

- 参考文献セクションから引用を抽出
- 本文中の[1], (Smith, 2020)なども分析
- タイトル、著者、年、ジャーナル、DOI（あれば）を含める
- JSONのみを返し、その他のテキストは含めない"""
        
        try:
            import base64
            
            # Read PDF file and encode as base64
            with open(pdf_path, 'rb') as f:
                pdf_data = base64.b64encode(f.read()).decode('utf-8')
            
            message = await self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=3000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            import json
            result = message.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if result.startswith('```'):
                lines = result.split('\n')
                result = '\n'.join(lines[1:-1])  # Remove first and last line
            if result.startswith('json'):
                result = result[4:].strip()
            
            try:
                citations = json.loads(result)
                return citations if isinstance(citations, list) else []
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw result: {result}")
                return []
                
        except Exception as e:
            raise Exception(f"Anthropic PDF citation extraction error: {str(e)}")


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider"""
    if settings.LLM_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
            raise ValueError("Anthropic API key is not configured. Please set ANTHROPIC_API_KEY in your .env file.")
        return AnthropicProvider()
    elif settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file.")
        return OpenAIProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}. Supported providers: openai, anthropic")


async def generate_summary(paper, custom_prompt: Optional[str] = None, db_session: Optional[object] = None) -> str:
    """Generate a summary for a paper using the configured LLM provider"""
    provider = get_llm_provider()
    
    # If using Anthropic and PDF exists, use direct PDF summarization
    if isinstance(provider, AnthropicProvider) and paper.pdf_path:
        try:
            import os
            if os.path.exists(paper.pdf_path):
                return await provider.generate_summary_from_pdf(paper.pdf_path, custom_prompt=custom_prompt, db_session=db_session)
        except Exception as e:
            print(f"PDF summarization failed, falling back to text summarization: {e}")
    
    # Fallback to text-based summarization
    text_parts = []
    if paper.title:
        text_parts.append(f"Title: {paper.title}")
    if paper.abstract:
        text_parts.append(f"Abstract: {paper.abstract}")
    if paper.authors:
        text_parts.append(f"Authors: {', '.join(paper.authors)}")
    if paper.year:
        text_parts.append(f"Year: {paper.year}")
    if paper.journal:
        text_parts.append(f"Journal: {paper.journal}")
    
    # Add PDF text extraction for non-Anthropic providers
    if paper.pdf_path:
        try:
            from .pdf_processor import extract_text_from_pdf_file
            pdf_text = await extract_text_from_pdf_file(paper.pdf_path)
            if pdf_text.strip():
                text_parts.append(f"Full text:\n{pdf_text}")
        except Exception as e:
            print(f"Warning: Could not extract text from PDF {paper.pdf_path}: {e}")
    
    text = "\n\n".join(text_parts)
    if not text.strip():
        raise ValueError("No text content available for summarization")
    
    return await provider.generate_summary(text, custom_prompt=custom_prompt, db_session=db_session)


async def extract_citations_from_paper(paper) -> list[Dict[str, Any]]:
    """Extract citations from a paper using the configured LLM provider"""
    provider = get_llm_provider()
    
    # If using Anthropic and PDF exists, use direct PDF extraction
    if isinstance(provider, AnthropicProvider) and paper.pdf_path:
        try:
            import os
            if os.path.exists(paper.pdf_path):
                return await provider.extract_citations_from_pdf(paper.pdf_path)
        except Exception as e:
            print(f"PDF extraction failed, falling back to text extraction: {e}")
    
    # Fallback to text-based extraction
    text_parts = []
    
    # Add basic paper information
    if paper.title:
        text_parts.append(f"Title: {paper.title}")
    if paper.abstract:
        text_parts.append(f"Abstract: {paper.abstract}")
    
    # Extract text from PDF if available
    if paper.pdf_path:
        try:
            from .pdf_processor import extract_text_from_pdf_file
            pdf_text = await extract_text_from_pdf_file(paper.pdf_path)
            if pdf_text.strip():
                text_parts.append(f"Full text:\n{pdf_text}")
        except Exception as e:
            print(f"Warning: Could not extract text from PDF {paper.pdf_path}: {e}")
    
    text = "\n\n".join(text_parts)
    if not text.strip():
        raise ValueError("No text content available for citation extraction")
    
    return await provider.extract_citations(text)