#!/usr/bin/env python3
"""
Test the inline citation extractor
"""

import sys
import asyncio
sys.path.append('src')

from theke.services.pdf_processor import extract_text_from_pdf_file
from theke.services.inline_citation_extractor import InlineCitationExtractor

async def test_inline_extractor():
    """Test the inline citation extractor"""
    pdf_path = "uploads/1_053f105e8cc34a3c8b415961b9a41f6a.pdf"
    
    print("🔗 Testing Inline Citation Extractor\n")
    
    try:
        # Extract text
        text = await extract_text_from_pdf_file(pdf_path)
        
        # Initialize extractor
        extractor = InlineCitationExtractor()
        
        # Extract inline citations and references
        print("📖 Extracting inline citations and references...")
        inline_citations, reference_entries = extractor.extract_inline_citations(text)
        
        print(f"✅ Found {len(inline_citations)} inline citations")
        print(f"✅ Found {len(reference_entries)} reference entries")
        print()
        
        # Show sample inline citations
        print("=== Sample Inline Citations ===")
        for i, citation in enumerate(inline_citations[:10], 1):
            print(f"{i}. {citation.raw_text} (Numbers: {citation.citation_numbers})")
            print(f"   Type: {citation.citation_type.value}")
            print(f"   Position: {citation.position/len(text)*100:.1f}% through document")
            print(f"   Context: ...{citation.context_before[-50:]} {citation.raw_text} {citation.context_after[:50]}...")
            print(f"   Sentence: {citation.sentence[:100]}{'...' if len(citation.sentence) > 100 else ''}")
            print()
        
        # Show sample references
        print("=== Sample Reference Entries ===")
        for i, ref in enumerate(reference_entries[:10], 1):
            print(f"{i}. [{ref['number']}] {ref.get('title', 'No title')}")
            if ref.get('authors'):
                print(f"   Authors: {', '.join(ref['authors'][:3])}{'...' if len(ref['authors']) > 3 else ''}")
            if ref.get('year'):
                print(f"   Year: {ref['year']}")
            if ref.get('venue'):
                print(f"   Venue: {ref['venue']}")
            print(f"   Raw: {ref['raw_text'][:100]}...")
            print()
        
        # Link citations to references
        print("=== Linking Citations to References ===")
        citation_links = extractor.link_citations_to_references(inline_citations, reference_entries)
        
        successful_links = [link for link in citation_links if link.reference_entry is not None]
        print(f"✅ Successfully linked: {len(successful_links)}/{len(citation_links)} citations")
        
        # Show some successful links
        print("\nSample Citation Links:")
        for i, link in enumerate(successful_links[:5], 1):
            inline = link.inline_citation
            ref = link.reference_entry
            
            print(f"{i}. {inline.raw_text} → [{ref['number']}]")
            print(f"   Context: {inline.citation_type.value}")
            print(f"   Reference: {ref.get('title', 'No title')}")
            if ref.get('authors'):
                print(f"   Authors: {', '.join(ref['authors'][:2])}")
            print()
        
        # Analyze patterns
        print("=== Citation Pattern Analysis ===")
        patterns = extractor.analyze_citation_patterns(inline_citations)
        
        print(f"Total citations: {patterns.get('total_citations', 0)}")
        print(f"Unique numbers: {patterns.get('unique_numbers', 0)}")
        print(f"Citation range: {patterns.get('citation_range', 'None')}")
        
        print("\nType distribution:")
        for cite_type, count in patterns.get('type_distribution', {}).items():
            print(f"  {cite_type}: {count}")
        
        print("\nMost cited references:")
        for num, count in patterns.get('most_cited', [])[:5]:
            ref = next((r for r in reference_entries if r['number'] == num), None)
            title = ref.get('title') if ref else None
            title_str = title[:50] if title else 'No title'
            print(f"  [{num}]: {count} times - {title_str}{'...' if title and len(title) > 50 else ''}")
        
        # Show coverage analysis
        print("\n=== Coverage Analysis ===")
        cited_numbers = set()
        for citation in inline_citations:
            cited_numbers.update(citation.citation_numbers)
        
        available_refs = set(ref['number'] for ref in reference_entries)
        
        uncited_refs = available_refs - cited_numbers
        missing_refs = cited_numbers - available_refs
        
        print(f"References cited in text: {len(cited_numbers)}")
        print(f"Available references: {len(available_refs)}")
        print(f"Uncited references: {len(uncited_refs)}")
        if uncited_refs:
            print(f"  Examples: {sorted(list(uncited_refs))[:10]}")
        
        if missing_refs:
            print(f"Citations without references: {sorted(list(missing_refs))}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_inline_extractor())