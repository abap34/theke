#!/usr/bin/env python3
"""
Simple test for citation extraction
"""

import sys
import asyncio
import tempfile
import os
sys.path.append('src')

from theke.services.citation_extractor import EnhancedCitationExtractor

async def test_simple_extraction():
    """Test citation extraction with a simple example"""
    print("🚀 Testing Simple Citation Extraction\n")
    
    # Create a temporary text file with sample references
    sample_text = """
Abstract

This paper presents a new approach to machine learning...

1. Introduction

Machine learning has evolved rapidly...

References

[1] Smith, J. A. (2020). Deep Learning Fundamentals. Journal of AI Research, 45(2), 123-145.

[2] Johnson, M. & Brown, K. (2019). "Neural Networks in Practice," Proceedings of ICML, pp. 234-245.

[3] Davis, P. et al. (2021). Advanced Machine Learning Techniques. MIT Press.

[4] Wilson, R. (2018). Statistical Learning Theory. Nature Machine Intelligence, 2(3), 89-102.

Appendix
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_text)
        temp_file = f.name
    
    try:
        extractor = EnhancedCitationExtractor()
        
        # Test reference section detection
        print("1. Testing reference section detection...")
        ref_section = extractor._find_references_section(sample_text)
        
        if ref_section:
            print(f"✅ Found reference section ({len(ref_section)} chars)")
            print("First 200 characters:")
            print(f"'{ref_section[:200]}...'")
            print()
        else:
            print("❌ No reference section found")
            return
        
        # Test citation-dense section fallback
        print("2. Testing citation-dense section detection...")
        fallback_section = extractor._find_citation_dense_section(sample_text)
        if fallback_section:
            print(f"✅ Found citation-dense section ({len(fallback_section)} chars)")
        else:
            print("ℹ️ No citation-dense section found (fallback not needed)")
        print()
        
        # Test individual parsing functions
        print("3. Testing individual parsing functions...")
        
        test_citations = [
            "[1] Smith, J. A. (2020). Deep Learning Fundamentals. Journal of AI Research, 45(2), 123-145.",
            "Johnson, M. & Brown, K. (2019). Neural Networks in Practice. Proceedings of ICML, pp. 234-245.",
            "Davis, P. et al. (2021). Advanced Machine Learning Techniques. MIT Press.",
        ]
        
        for citation_text in test_citations:
            print(f"Testing: '{citation_text[:60]}...'")
            
            # Test title extraction (simple approach)
            if ". " in citation_text:
                parts = citation_text.split(". ")
                if len(parts) >= 2:
                    potential_title = parts[1] if parts[1] else parts[0]
                    cleaned_title = extractor._clean_title(potential_title)
                    is_valid = not extractor._is_invalid_title(cleaned_title)
                    print(f"  Title: '{cleaned_title}' (Valid: {is_valid})")
            print()
        
        # Test complete extraction
        print("4. Testing complete citation extraction from text...")
        
        # Instead of using PDF extraction, we'll create a mock version
        print("Simulating PDF text extraction...")
        
        # Extract from the reference section
        import re
        citations = []
        
        # Use one of the citation patterns directly
        pattern = r"\[(\d+)\]\s*([^()]+)\s*\((\d{4})\)\.\s*([^.]+)\.\s*([^.\n]+)"
        matches = re.finditer(pattern, ref_section, re.MULTILINE)
        
        for match in matches:
            try:
                groups = match.groups()
                if len(groups) >= 5:
                    number, authors, year, title, journal = groups[:5]
                    
                    # Clean and validate
                    title = extractor._clean_title(title)
                    if not extractor._is_invalid_title(title):
                        parsed_authors = extractor._parse_authors(authors)
                        cleaned_journal = extractor._clean_journal_name(journal)
                        
                        confidence = extractor._calculate_extraction_confidence(
                            title, parsed_authors, int(year), cleaned_journal, "", match.group(0)
                        )
                        
                        citations.append({
                            'title': title,
                            'authors': parsed_authors,
                            'year': int(year),
                            'journal': cleaned_journal,
                            'confidence': confidence
                        })
                        
            except Exception as e:
                print(f"Error processing citation: {e}")
        
        print(f"✅ Extracted {len(citations)} citations:")
        for i, citation in enumerate(citations, 1):
            print(f"  {i}. Title: '{citation['title']}'")
            print(f"     Authors: {citation['authors']}")
            print(f"     Year: {citation['year']}")
            print(f"     Journal: '{citation['journal']}'")
            print(f"     Confidence: {citation['confidence']:.2f}")
            print()
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_simple_extraction())