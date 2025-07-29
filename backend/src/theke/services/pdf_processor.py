import re
from pathlib import Path
from typing import Any, Dict, Optional

import PyPDF2

from .llm_service import get_llm_provider


async def extract_metadata_from_pdf(file, use_llm: bool = False) -> Dict[str, Any]:
    """Extract metadata and text from uploaded PDF file"""
    try:
        # Read PDF content
        content = await file.read()

        # Reset file pointer for potential reuse
        await file.seek(0)

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
                metadata.update(
                    {
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "authors": _parse_authors(
                            pdf_reader.metadata.get("/Author", "")
                        ),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                        "creator": pdf_reader.metadata.get("/Creator", ""),
                    }
                )

            # Try to extract title and abstract from text if not in metadata
            if not metadata.get("title"):
                title = _extract_title_from_text(text_content)
                if title:
                    metadata["title"] = title

            if not metadata.get("authors"):
                # Extract authors while avoiding the title
                extracted_title = metadata.get("title", "")
                authors = _extract_authors_from_text(text_content, excluded_title=extracted_title)
                if authors:
                    metadata["authors"] = authors

            # Abstract extraction disabled - will be generated on demand via LLM
            # abstract = _extract_abstract_from_text(text_content)
            # if abstract:
            #     metadata['abstract'] = abstract

            year = _extract_year_from_text(text_content)
            if year:
                metadata["year"] = year

            doi = _extract_doi_from_text(text_content)
            if doi:
                metadata["doi"] = doi

        # Ensure we have at least a title
        if not metadata.get("title"):
            metadata["title"] = Path(file.filename).stem

        if not metadata.get("authors"):
            metadata["authors"] = []

        return metadata

    except Exception as e:
        # Fallback to filename-based metadata
        return {
            "title": Path(file.filename).stem,
            "authors": [],
            "abstract": "",  # Keep abstract empty by default
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
        - doi: DOI（文字列）
        - keywords: キーワード（文字列の配列）
        
        注意: abstractは含めないでください。

        JSONのみを返してください。他のテキストは含めないでください。

        論文テキスト:
        """

        # Use the provider's generate_summary method with custom prompt
        if hasattr(provider, "client"):
            # For OpenAI
            if "openai" in str(type(provider)):
                response = await provider.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": text_content[:8000],
                        },  # Limit text length
                    ],
                    max_tokens=1000,
                    temperature=0.1,
                )
                result = response.choices[0].message.content.strip()
            # For Anthropic
            else:
                message = await provider.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{prompt}\n\n{text_content[:100000]}",
                        }
                    ],
                )
                result = message.content[0].text.strip()

            # Parse JSON result
            import json

            try:
                # Remove any markdown code blocks
                if result.startswith("```"):
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]

                metadata = json.loads(result)

                # Clean up the metadata
                cleaned_metadata = {}
                if metadata.get("title") and metadata["title"] != "null":
                    cleaned_metadata["title"] = metadata["title"]
                if metadata.get("authors") and isinstance(metadata["authors"], list):
                    cleaned_metadata["authors"] = [
                        author
                        for author in metadata["authors"]
                        if author and author != "null"
                    ]
                if metadata.get("year") and isinstance(metadata["year"], int):
                    cleaned_metadata["year"] = metadata["year"]
                if metadata.get("journal") and metadata["journal"] != "null":
                    cleaned_metadata["journal"] = metadata["journal"]
                # Abstract processing removed - will be generated on demand
                if metadata.get("doi") and metadata["doi"] != "null":
                    cleaned_metadata["doi"] = metadata["doi"]
                if metadata.get("keywords") and isinstance(metadata["keywords"], list):
                    cleaned_metadata["keywords"] = [
                        kw for kw in metadata["keywords"] if kw and kw != "null"
                    ]

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
    separators = [";", ",", " and ", " & "]
    authors = [author_string]

    for sep in separators:
        new_authors = []
        for author in authors:
            new_authors.extend([a.strip() for a in author.split(sep)])
        authors = new_authors

    return [a for a in authors if a]


def _extract_title_from_text(text: str) -> Optional[str]:
    """Extract title from PDF text using improved heuristics"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    if not lines:
        return None
    
    # Skip common header/footer patterns
    skip_patterns = [
        r'^(page\s+\d+|p\.\s*\d+)$',
        r'^\d+$',
        r'^[ivxlc]+$',  # Roman numerals
        r'^(arxiv|doi|issn|isbn)',
        r'^\w+\.(com|org|edu)',
        r'^©.*\d{4}',
        r'^published\s+in',
        r'^proceedings\s+of',
    ]
    
    # Common exclusion patterns for titles
    exclude_patterns = [
        r'^(abstract|introduction|keywords|references|bibliography|contents?|acknowledgments?)',
        r'^(table\s+of\s+contents|list\s+of)',
        r'^(figure|table|equation)\s+\d+',
        r'^(chapter|section)\s+\d+',
        r'^\d+\.\s+',  # Numbered sections
        r'@.*\.(com|org|edu)',  # Email addresses
        r'(university|college|institute|department)',
        r'^(received|accepted|published)',
        r'^\*.*correspondence',
    ]
    
    candidates = []
    
    # Analyze first 20 lines for potential titles
    for i, line in enumerate(lines[:20]):
        line_lower = line.lower()
        
        # Skip lines that match skip patterns
        if any(re.search(pattern, line_lower) for pattern in skip_patterns):
            continue
            
        # Skip lines that match exclusion patterns
        if any(re.search(pattern, line_lower) for pattern in exclude_patterns):
            continue
        
        # Length-based filtering
        if not (10 <= len(line) <= 300):
            continue
            
        # Skip lines with too many numbers or special characters
        if len(re.findall(r'[0-9@#$%^&*()_+={}|<>?/\\]', line)) > len(line) * 0.3:
            continue
            
        # Skip lines that are mostly uppercase (likely headers)
        if len([c for c in line if c.isupper()]) > len(line) * 0.7:
            continue
            
        # Skip single words or very short phrases
        if len(line.split()) < 3:
            continue
            
        # Calculate title score
        score = _calculate_title_score(line, i, lines)
        candidates.append((line, score, i))
    
    if candidates:
        # Sort by score (descending) and return the best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return None


def _calculate_title_score(line: str, position: int, all_lines: list) -> float:
    """Calculate likelihood score for a line being a title"""
    score = 0.0
    
    # Position score (earlier lines more likely to be titles)
    score += max(0, 20 - position * 2)
    
    # Length score (optimal length around 50-100 characters)
    length = len(line)
    if 30 <= length <= 150:
        score += 15
    elif 15 <= length <= 30 or 150 <= length <= 200:
        score += 10
    elif length > 200:
        score -= 10
        
    # Word count score (titles usually have 3-15 words)
    word_count = len(line.split())
    if 3 <= word_count <= 15:
        score += 10
    elif word_count > 20:
        score -= 5
        
    # Capitalization patterns
    words = line.split()
    capitalized_words = sum(1 for word in words if word[0].isupper() and len(word) > 1)
    if capitalized_words >= len(words) * 0.6:  # Most words capitalized (title case)
        score += 15
        
    # Punctuation analysis
    if line.endswith('.') and not line.endswith('...'):
        score -= 5  # Titles usually don't end with periods
    if line.endswith(':'):
        score += 5  # Titles can end with colons
        
    # Common title words
    title_indicators = ['analysis', 'study', 'investigation', 'review', 'survey', 'approach', 
                       'method', 'algorithm', 'system', 'framework', 'model', 'towards', 'using']
    if any(indicator in line.lower() for indicator in title_indicators):
        score += 8
        
    # Check if line stands alone (not part of a paragraph)
    next_line_empty = position + 1 >= len(all_lines) or not all_lines[position + 1].strip()
    if next_line_empty:
        score += 10
        
    # Font size heuristic (if line is significantly shorter/longer than surrounding text)
    nearby_lines = all_lines[max(0, position-2):position+3]
    avg_length = sum(len(l) for l in nearby_lines if l.strip()) / max(1, len([l for l in nearby_lines if l.strip()]))
    if len(line) > avg_length * 0.8:  # Roughly similar or longer than nearby text
        score += 5
        
    return score


def _extract_authors_from_text(text: str, excluded_title: str = "") -> list[str]:
    """Extract authors from PDF text using improved heuristics"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    if not lines:
        return []
    
    # Skip patterns that are unlikely to contain author names
    skip_patterns = [
        r'^(abstract|introduction|keywords|references|bibliography)',
        r'^(page\s+\d+|p\.\s*\d+)$',
        r'^\d+$',
        r'^(arxiv|doi|issn|isbn)',
        r'^©.*\d{4}',
        r'^(received|accepted|published)',
        r'^(table|figure|equation)\s+\d+',
    ]
    
    # Affiliation indicators (these lines might contain authors but need special handling)
    affiliation_indicators = [
        'university', 'college', 'institute', 'school', 'department', 'faculty',
        'laboratory', 'center', 'centre', 'hospital', 'company', 'corporation',
        'foundation', 'academy', 'research', 'technology', 'science'
    ]
    
    candidates = []
    
    # Search in first 25 lines for author patterns
    for i, line in enumerate(lines[:25]):
        line_lower = line.lower()
        
        # Skip lines matching skip patterns
        if any(re.search(pattern, line_lower) for pattern in skip_patterns):
            continue
        
        # Skip very long lines (likely paragraphs)
        if len(line) > 200:
            continue
            
        # Skip lines with too many numbers or special characters
        if len(re.findall(r'[0-9@#$%^&*()_+={}|<>?/\\]', line)) > len(line) * 0.4:
            continue
        
        # CRITICAL: Skip if line matches the extracted title
        if excluded_title and _is_title_match(line, excluded_title):
            continue
            
        # Skip if line looks like a title rather than authors
        if _looks_like_title(line):
            continue
        
        # Calculate author score for this line
        score = _calculate_author_score(line, i, lines)
        
        if score > 10:  # Minimum threshold for considering as author line
            authors = _extract_authors_from_line(line)
            if authors:
                # Additional validation: filter out title-like author names
                filtered_authors = [a for a in authors if not _looks_like_title(a)]
                if filtered_authors:
                    candidates.append((filtered_authors, score, i))
    
    if candidates:
        # Sort by score and return the best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return []


def _calculate_author_score(line: str, position: int, all_lines: list) -> float:
    """Calculate likelihood score for a line containing author names"""
    score = 0.0
    
    # Position score (authors usually appear early in the document)
    if position <= 5:
        score += 20
    elif position <= 10:
        score += 15
    elif position <= 20:
        score += 10
    else:
        score += 5
        
    # Check for name patterns
    # Pattern 1: "Firstname Lastname" (capitalized words)
    name_pattern_1 = len(re.findall(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', line))
    score += name_pattern_1 * 8
    
    # Pattern 2: "F. Lastname" or "Firstname M. Lastname"
    initial_pattern = len(re.findall(r'\b[A-Z]\.\s*[A-Z][a-z]{2,}\b', line))
    score += initial_pattern * 6
    
    # Pattern 3: Multiple authors separated by commas/and
    if ',' in line and name_pattern_1 >= 1:
        score += 10
    if ' and ' in line.lower() and name_pattern_1 >= 1:
        score += 12
    if ' & ' in line and name_pattern_1 >= 1:
        score += 10
        
    # Penalty for lines with common non-author content
    line_lower = line.lower()
    
    # Check for affiliation indicators
    affiliation_count = sum(1 for indicator in ['university', 'college', 'institute', 'department'] 
                          if indicator in line_lower)
    if affiliation_count > 0:
        score -= affiliation_count * 15  # Heavy penalty for affiliation lines
        
    # Check for email addresses (could be author contact but usually separate)
    if '@' in line:
        score -= 10
        
    # Check for numbers (addresses, phone numbers, etc.)
    digit_count = len(re.findall(r'\d', line))
    if digit_count > 3:
        score -= digit_count * 2
        
    # Check for common title/header words
    header_words = ['paper', 'article', 'journal', 'conference', 'proceedings', 'volume', 'issue']
    if any(word in line_lower for word in header_words):
        score -= 15
        
    # Length analysis
    word_count = len(line.split())
    if 2 <= word_count <= 12:  # Optimal range for author lines
        score += 8
    elif word_count > 20:
        score -= 10
        
    # Check if line stands alone (authors often on separate line)
    next_line_empty = position + 1 >= len(all_lines) or not all_lines[position + 1].strip()
    if next_line_empty:
        score += 5
        
    return score


def _extract_authors_from_line(line: str) -> list[str]:
    """Extract individual author names from a line"""
    # Clean the line
    line = line.strip()
    
    # Remove common prefixes/suffixes
    prefixes = ['by', 'authors?:', 'written by', 'authored by']
    for prefix in prefixes:
        line = re.sub(rf'^{prefix}\s*', '', line, flags=re.IGNORECASE)
    
    # Remove superscript numbers and asterisks (affiliation markers)
    line = re.sub(r'[*†‡§¶]|\d+', '', line)
    
    # Split by common separators
    authors = []
    
    # Try different separation patterns
    if ' and ' in line.lower():
        parts = re.split(r'\s+and\s+', line, flags=re.IGNORECASE)
        for part in parts:
            if ',' in part:
                # Handle "Smith, John and Doe, Jane" format
                sub_authors = [author.strip() for author in part.split(',')]
                authors.extend([a for a in sub_authors if a and _is_valid_author_name(a)])
            else:
                if _is_valid_author_name(part.strip()):
                    authors.append(part.strip())
    elif ',' in line:
        # Split by commas
        potential_authors = [author.strip() for author in line.split(',')]
        for author in potential_authors:
            if _is_valid_author_name(author):
                authors.append(author)
    else:
        # Single author or space-separated
        if _is_valid_author_name(line):
            authors.append(line)
    
    # Clean and validate authors
    cleaned_authors = []
    for author in authors:
        # Remove extra whitespace
        author = ' '.join(author.split())
        
        # Skip if too short or too long
        if len(author) < 3 or len(author) > 50:
            continue
            
        # Skip if it's just initials
        if re.match(r'^[A-Z]\.\s*[A-Z]\.$', author):
            continue
            
        cleaned_authors.append(author)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_authors = []
    for author in cleaned_authors:
        if author.lower() not in seen:
            seen.add(author.lower())
            unique_authors.append(author)
    
    return unique_authors[:10]  # Limit to reasonable number


def _is_valid_author_name(name: str) -> bool:
    """Check if a string looks like a valid author name"""
    name = name.strip()
    
    if not name or len(name) < 3:
        return False
        
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', name):
        return False
        
    # Check for valid name patterns
    # Pattern 1: "John Smith", "John A. Smith", "J. Smith"
    if re.match(r'^[A-Z][a-z]*\.?\s+([A-Z]\.?\s+)*[A-Z][a-z]+$', name):
        return True
        
    # Pattern 2: "Smith, John", "Smith, J."
    if re.match(r'^[A-Z][a-z]+,\s+[A-Z][a-z]*\.?$', name):
        return True
        
    # Pattern 3: Just check for reasonable capitalization
    words = name.split()
    if len(words) >= 2:
        # Most words should start with capital letter
        capitalized = sum(1 for word in words if word and word[0].isupper())
        if capitalized / len(words) >= 0.5:
            return True
    
    return False


def _is_title_match(line: str, title: str) -> bool:
    """Check if a line matches an extracted title"""
    if not title or not line:
        return False
    
    # Normalize both strings for comparison
    line_normalized = ' '.join(line.strip().split()).lower()
    title_normalized = ' '.join(title.strip().split()).lower()
    
    # Exact match
    if line_normalized == title_normalized:
        return True
    
    # Check if line contains most of the title words (allowing for slight variations)
    line_words = set(line_normalized.split())
    title_words = set(title_normalized.split())
    
    # Skip very short titles/lines for this check
    if len(title_words) < 3 or len(line_words) < 3:
        return line_normalized == title_normalized
    
    # If 80% or more of title words are in the line, consider it a match
    common_words = line_words.intersection(title_words)
    if len(common_words) >= len(title_words) * 0.8:
        return True
    
    return False


def _looks_like_title(text: str) -> bool:
    """Check if text looks more like a title than author names"""
    if not text or len(text.strip()) < 5:
        return False
    
    text = text.strip()
    words = text.split()
    
    # Very long text is likely a title (>15 words)
    if len(words) > 15:
        return True
    
    # Check for title indicators
    title_indicators = [
        'analysis', 'study', 'investigation', 'review', 'survey', 'approach',
        'method', 'algorithm', 'system', 'framework', 'model', 'towards',
        'using', 'based', 'novel', 'improved', 'enhanced', 'automatic',
        'efficient', 'robust', 'optimal', 'deep', 'machine', 'learning',
        'detection', 'recognition', 'classification', 'prediction',
        'optimization', 'evaluation', 'comparison', 'application'
    ]
    
    text_lower = text.lower()
    if any(indicator in text_lower for indicator in title_indicators):
        return True
    
    # Check for title-like patterns
    # Titles often have prepositions and articles
    title_words = ['of', 'for', 'in', 'on', 'with', 'by', 'from', 'to', 'the', 'a', 'an']
    title_word_count = sum(1 for word in words if word.lower() in title_words)
    if title_word_count >= 2:  # Multiple title words suggest it's a title
        return True
    
    # Check for colons (common in titles, rare in author names)
    if ':' in text:
        return True
    
    # Check if it lacks typical name patterns
    # Names usually have 2-4 words, most capitalized
    if len(words) >= 2:
        capitalized_words = sum(1 for word in words if word and word[0].isupper())
        
        # If most words are capitalized but it's long, likely a title
        if capitalized_words >= len(words) * 0.8 and len(words) > 6:
            return True
        
        # If few words are capitalized, might be a title in sentence case
        if capitalized_words < len(words) * 0.5:
            return True
    
    # Check for academic/technical terms that are common in titles
    academic_terms = [
        'research', 'experimental', 'theoretical', 'computational', 'statistical',
        'mathematical', 'numerical', 'empirical', 'comparative', 'comprehensive',
        'systematic', 'meta', 'multi', 'cross', 'inter', 'trans', 'bio', 'nano',
        'micro', 'macro', 'quantum', 'neural', 'genetic', 'semantic', 'syntactic'
    ]
    
    if any(term in text_lower for term in academic_terms):
        return True
    
    # Check length and word patterns
    # Very short text with few words might be authors
    if len(words) <= 3 and all(len(word) >= 2 for word in words):
        # Check if it follows name patterns
        name_patterns = [
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # "John Smith"
            r'^[A-Z]\.\s*[A-Z][a-z]+$',      # "J. Smith"
            r'^[A-Z][a-z]+,\s*[A-Z][a-z]*\.?$'  # "Smith, J."
        ]
        
        if any(re.match(pattern, text) for pattern in name_patterns):
            return False  # Looks like a name
    
    return False


def _extract_abstract_from_text(text: str) -> Optional[str]:
    """Extract abstract from PDF text"""
    # Look for abstract section
    abstract_match = re.search(
        r"abstract[:\s]+(.*?)(?=\n\n|\nintroduction|\nkeywords|\n1\.|\n\d+\.)",
        text.lower(),
        re.DOTALL | re.IGNORECASE,
    )

    if abstract_match:
        abstract = abstract_match.group(1).strip()
        # Clean up the abstract
        abstract = re.sub(r"\s+", " ", abstract)  # Normalize whitespace
        if len(abstract) > 50 and len(abstract) < 2000:  # Reasonable abstract length
            return abstract

    return None


def _extract_year_from_text(text: str) -> Optional[int]:
    """Extract publication year from PDF text"""
    # Look for 4-digit years (1900-2030)
    year_matches = re.findall(r"\b(19\d{2}|20[0-3]\d)\b", text)

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
    doi_regex = r"10\.\d{4,9}/[-._;()/:A-Z0-9]+"

    match = re.search(doi_regex, text, re.IGNORECASE)

    if match:
        return match.group(0).strip(".,")

    return None


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from PDF file"""
    try:
        with open(pdf_path, "rb") as file:
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
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception:
        return 0
