"""
Inline Citation Extractor
Extracts inline citations from the main text and links them to the reference list.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum

from .citation_extractor import EnhancedCitationExtractor


class CitationType(Enum):
    """Types of citation usage in context"""
    REFERENCE = "reference"        # General reference
    EVIDENCE = "evidence"          # Supporting evidence
    ATTRIBUTION = "attribution"    # Attribution of idea/quote
    COMPARISON = "comparison"      # Similarity comparison
    CONTRAST = "contrast"          # Difference/opposition
    METHOD = "method"             # Methodology reference
    DEFINITION = "definition"      # Definition source


@dataclass
class InlineCitation:
    """Represents an inline citation found in the main text"""
    citation_numbers: List[int]    # [1, 2, 3] for [1,2,3]
    raw_text: str                 # "[1,2,3]"
    context_before: str           # 100 chars before
    context_after: str            # 100 chars after
    position: int                 # Character position in text
    citation_type: CitationType   # Type of usage
    sentence: str                 # Full sentence containing citation
    

@dataclass
class CitationLink:
    """Links inline citation to reference entry"""
    inline_citation: InlineCitation
    reference_entry: Optional[Dict]  # Matched reference from bibliography
    confidence: float               # Confidence in the link


class InlineCitationExtractor:
    """Extracts and analyzes inline citations from academic papers"""
    
    def __init__(self):
        self.enhanced_extractor = EnhancedCitationExtractor()
    
    def extract_inline_citations(self, text: str) -> Tuple[List[InlineCitation], List[Dict]]:
        """
        Extract inline citations from main text and references from bibliography
        
        Returns:
            Tuple of (inline_citations, reference_entries)
        """
        # Split text into main content and references
        ref_section = self.enhanced_extractor._find_references_section(text)
        
        if ref_section:
            ref_start = text.find(ref_section[:100])
            main_text = text[:ref_start] if ref_start > 0 else text
        else:
            main_text = text
            ref_section = ""
        
        print(f"Extracting from main text: {len(main_text)} chars")
        print(f"References section: {len(ref_section)} chars")
        
        # Extract inline citations from main text
        inline_citations = self._extract_inline_citations_from_text(main_text)
        
        # Extract reference entries from bibliography
        reference_entries = self._extract_reference_entries(ref_section) if ref_section else []
        
        return inline_citations, reference_entries
    
    def _extract_inline_citations_from_text(self, text: str) -> List[InlineCitation]:
        """Extract inline citations from the main text"""
        inline_citations = []
        
        # Patterns for different citation formats (including spacing variations)
        patterns = [
            # Single citation with various spacing
            (r'\[\s*(\d+)\s*\]', 'single'),                         # [1], [ 1], [1 ], [ 1 ]
            
            # Double citation
            (r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', 'double'),            # [1, 2], [ 1 , 2 ]
            
            # Range citations with different dashes
            (r'\[\s*(\d+)\s*-\s*(\d+)\s*\]', 'range'),             # [1-5], [ 1 - 5 ]
            (r'\[\s*(\d+)\s*–\s*(\d+)\s*\]', 'range'),             # [1–5] em dash
            (r'\[\s*(\d+)\s*—\s*(\d+)\s*\]', 'range'),             # [1—5] em dash
            
            # Multiple citations (catch-all)
            (r'\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]', 'multiple'),       # [1, 2, 3, ...]
            
            # Alternative patterns that might be used
            (r'\(\s*(\d+)\s*\)', 'single_paren'),                  # (1)
            (r'\(\s*(\d+)\s*,\s*(\d+)\s*\)', 'double_paren'),      # (1, 2)
        ]
        
        for pattern, pattern_type in patterns:
            for match in re.finditer(pattern, text):
                try:
                    # Extract citation numbers
                    if pattern_type == 'single':
                        numbers = [int(match.group(1))]
                    elif pattern_type == 'double':
                        numbers = [int(match.group(1)), int(match.group(2))]
                    elif pattern_type == 'range':
                        start, end = int(match.group(1)), int(match.group(2))
                        numbers = list(range(start, end + 1))
                    elif pattern_type == 'multiple':
                        numbers_str = match.group(1)
                        numbers = [int(n.strip()) for n in numbers_str.split(',')]
                    else:
                        continue
                    
                    # Extract context
                    start_pos = max(0, match.start() - 150)
                    end_pos = min(len(text), match.end() + 150)
                    
                    context_before = text[start_pos:match.start()]
                    context_after = text[match.end():end_pos]
                    
                    # Extract full sentence
                    sentence = self._extract_sentence(text, match.start(), match.end())
                    
                    # Determine citation type
                    citation_type = self._classify_citation_type(context_before, context_after, sentence)
                    
                    inline_citation = InlineCitation(
                        citation_numbers=numbers,
                        raw_text=match.group(0),
                        context_before=context_before.strip(),
                        context_after=context_after.strip(),
                        position=match.start(),
                        citation_type=citation_type,
                        sentence=sentence.strip()
                    )
                    
                    inline_citations.append(inline_citation)
                    
                except (ValueError, IndexError) as e:
                    print(f"Error processing citation match: {e}")
                    continue
        
        # Remove duplicates (same position)
        seen_positions = set()
        unique_citations = []
        for citation in inline_citations:
            if citation.position not in seen_positions:
                unique_citations.append(citation)
                seen_positions.add(citation.position)
        
        # Sort by position
        unique_citations.sort(key=lambda x: x.position)
        
        print(f"Extracted {len(unique_citations)} unique inline citations")
        return unique_citations
    
    def _extract_sentence(self, text: str, cite_start: int, cite_end: int) -> str:
        """Extract the full sentence containing the citation"""
        # Look for sentence boundaries
        sentence_start = cite_start
        sentence_end = cite_end
        
        # Find sentence start (look backwards for ., !, ?)
        for i in range(cite_start - 1, max(0, cite_start - 500), -1):
            if text[i] in '.!?':
                # Check if it's not an abbreviation
                if i + 1 < len(text) and text[i + 1].isspace():
                    sentence_start = i + 1
                    break
        
        # Find sentence end (look forwards for ., !, ?)
        for i in range(cite_end, min(len(text), cite_end + 500)):
            if text[i] in '.!?':
                # Check if next char is space or end of text
                if i + 1 >= len(text) or text[i + 1].isspace():
                    sentence_end = i + 1
                    break
        
        sentence = text[sentence_start:sentence_end].strip()
        return sentence
    
    def _classify_citation_type(self, before: str, after: str, sentence: str) -> CitationType:
        """Classify the type of citation based on context"""
        full_context = (before + " " + after + " " + sentence).lower()
        
        # Evidence patterns
        if any(pattern in full_context for pattern in [
            'as shown', 'demonstrates', 'proves', 'evidence', 'confirms', 'validates'
        ]):
            return CitationType.EVIDENCE
        
        # Attribution patterns
        if any(pattern in full_context for pattern in [
            'according to', 'states', 'argues', 'claims', 'proposes', 'suggests',
            'reported', 'found', 'observed'
        ]):
            return CitationType.ATTRIBUTION
        
        # Comparison patterns
        if any(pattern in full_context for pattern in [
            'similar to', 'like', 'follows', 'builds on', 'extends', 'based on'
        ]):
            return CitationType.COMPARISON
        
        # Contrast patterns
        if any(pattern in full_context for pattern in [
            'unlike', 'different', 'contrast', 'however', 'alternatively', 'instead'
        ]):
            return CitationType.CONTRAST
        
        # Method patterns
        if any(pattern in full_context for pattern in [
            'method', 'algorithm', 'approach', 'technique', 'procedure', 'protocol'
        ]):
            return CitationType.METHOD
        
        # Definition patterns
        if any(pattern in full_context for pattern in [
            'defined', 'definition', 'terminology', 'concept', 'term', 'notation'
        ]):
            return CitationType.DEFINITION
        
        # Default
        return CitationType.REFERENCE
    
    def _extract_reference_entries(self, ref_section: str) -> List[Dict]:
        """Extract structured reference entries from bibliography"""
        reference_entries = []
        
        # Pattern to match numbered references
        ref_pattern = r'\[(\d+)\]\s*(.+?)(?=\n\[|\n\s*$|$)'
        
        matches = re.finditer(ref_pattern, ref_section, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            try:
                ref_number = int(match.group(1))
                ref_text = match.group(2).strip()
                
                # Basic parsing of reference components
                entry = {
                    'number': ref_number,
                    'raw_text': ref_text,
                    'authors': self._extract_authors_from_ref(ref_text),
                    'title': self._extract_title_from_ref(ref_text),
                    'year': self._extract_year_from_ref(ref_text),
                    'venue': self._extract_venue_from_ref(ref_text),
                    'doi': self._extract_doi_from_ref(ref_text),
                    'url': self._extract_url_from_ref(ref_text),
                }
                
                reference_entries.append(entry)
                
            except (ValueError, IndexError) as e:
                print(f"Error processing reference entry: {e}")
                continue
        
        print(f"Extracted {len(reference_entries)} reference entries")
        return reference_entries
    
    def _extract_authors_from_ref(self, ref_text: str) -> List[str]:
        """Extract authors from reference text"""
        # Look for patterns before year or title
        # This is a simplified version - could be enhanced
        parts = ref_text.split('.')
        if parts:
            potential_authors = parts[0].strip()
            # Simple heuristic: if it contains typical name patterns
            if re.search(r'[A-Z][a-z]+(,|\s+and\s+)', potential_authors):
                return [name.strip() for name in re.split(r',\s*and\s+|,\s*', potential_authors)]
        return []
    
    def _extract_title_from_ref(self, ref_text: str) -> Optional[str]:
        """Extract title from reference text"""
        # Look for text in quotes or after authors and year
        quoted_match = re.search(r'[""]([^""]+)[""]', ref_text)
        if quoted_match:
            return quoted_match.group(1).strip()
        
        # Alternative: look for pattern after authors and before venue
        # This is simplified - real implementation would be more sophisticated
        return None
    
    def _extract_year_from_ref(self, ref_text: str) -> Optional[int]:
        """Extract publication year from reference text"""
        year_match = re.search(r'\b(19|20)\d{2}\b', ref_text)
        if year_match:
            return int(year_match.group(0))
        return None
    
    def _extract_venue_from_ref(self, ref_text: str) -> Optional[str]:
        """Extract publication venue from reference text"""
        # Look for common venue indicators
        venue_patterns = [
            r'In\s+([^,]+(?:Conference|Workshop|Symposium|Proceedings)[^,\.]*)',
            r'([^,]+(?:Journal|Review|Magazine|Transactions)[^,\.]*)',
        ]
        
        for pattern in venue_patterns:
            match = re.search(pattern, ref_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_doi_from_ref(self, ref_text: str) -> Optional[str]:
        """Extract DOI from reference text"""
        doi_match = re.search(r'doi[:\s]*([^\s\n]+)', ref_text, re.IGNORECASE)
        if doi_match:
            return doi_match.group(1).strip()
        return None
    
    def _extract_url_from_ref(self, ref_text: str) -> Optional[str]:
        """Extract URL from reference text"""
        url_match = re.search(r'https?://[^\s\n]+', ref_text)
        if url_match:
            return url_match.group(0).strip()
        return None
    
    def link_citations_to_references(
        self, 
        inline_citations: List[InlineCitation], 
        reference_entries: List[Dict]
    ) -> List[CitationLink]:
        """Link inline citations to their corresponding reference entries"""
        citation_links = []
        
        # Create lookup dictionary for references
        ref_lookup = {entry['number']: entry for entry in reference_entries}
        
        for inline_citation in inline_citations:
            for cite_num in inline_citation.citation_numbers:
                reference_entry = ref_lookup.get(cite_num)
                confidence = 1.0 if reference_entry else 0.0
                
                link = CitationLink(
                    inline_citation=inline_citation,
                    reference_entry=reference_entry,
                    confidence=confidence
                )
                
                citation_links.append(link)
        
        return citation_links
    
    def analyze_citation_patterns(
        self, 
        inline_citations: List[InlineCitation]
    ) -> Dict[str, any]:
        """Analyze patterns in citation usage"""
        if not inline_citations:
            return {}
        
        # Type distribution
        type_counts = {}
        for citation in inline_citations:
            type_name = citation.citation_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Position distribution
        positions = [c.position for c in inline_citations]
        
        # Most cited numbers
        all_numbers = []
        for citation in inline_citations:
            all_numbers.extend(citation.citation_numbers)
        
        number_counts = {}
        for num in all_numbers:
            number_counts[num] = number_counts.get(num, 0) + 1
        
        most_cited = sorted(number_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_citations': len(inline_citations),
            'unique_numbers': len(set(all_numbers)),
            'citation_range': f"{min(all_numbers)} - {max(all_numbers)}" if all_numbers else "None",
            'type_distribution': type_counts,
            'most_cited': most_cited[:10],  # Top 10
            'position_stats': {
                'first_position': min(positions),
                'last_position': max(positions),
                'average_position': sum(positions) / len(positions)
            }
        }