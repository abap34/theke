#!/usr/bin/env python3
"""
Test citation extraction on real PDF file
"""

import sys
import asyncio
import os
sys.path.append('src')

from theke.services.citation_extractor import EnhancedCitationExtractor

async def test_pdf_citation_extraction():
    """Test citation extraction on the provided test.pdf"""
    print("🚀 Testing Citation Extraction on test.pdf\n")
    
    pdf_path = "test.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"📄 Testing with PDF: {pdf_path}")
    print(f"📊 File size: {os.path.getsize(pdf_path)} bytes\n")
    
    async with EnhancedCitationExtractor() as extractor:
        try:
            # Test PDF-based extraction
            print("1. Testing PDF text extraction and reference detection...")
            citations = await extractor._extract_from_pdf(pdf_path)
            
            print(f"✅ Extracted {len(citations)} citations from PDF\n")
            
            if citations:
                print("📋 Extracted Citations:")
                for i, citation in enumerate(citations[:10], 1):  # Show first 10
                    print(f"  {i}. Title: '{citation.title}'")
                    print(f"     Authors: {citation.authors}")
                    print(f"     Year: {citation.year}")
                    print(f"     Journal: '{citation.journal}'")
                    if citation.doi:
                        print(f"     DOI: {citation.doi}")
                    print(f"     Confidence: {citation.confidence:.2f}")
                    print(f"     Source: {citation.source}")
                    if citation.raw_text:
                        print(f"     Raw: {citation.raw_text[:100]}...")
                    print()
                
                if len(citations) > 10:
                    print(f"... and {len(citations) - 10} more citations")
                    print()
                
                # Show confidence distribution
                confidences = [c.confidence for c in citations]
                avg_confidence = sum(confidences) / len(confidences)
                high_conf = len([c for c in confidences if c >= 0.7])
                med_conf = len([c for c in confidences if 0.5 <= c < 0.7])
                low_conf = len([c for c in confidences if c < 0.5])
                
                print(f"📊 Confidence Distribution:")
                print(f"   High (≥0.7): {high_conf} citations")
                print(f"   Medium (0.5-0.7): {med_conf} citations")
                print(f"   Low (<0.5): {low_conf} citations")
                print(f"   Average: {avg_confidence:.2f}")
                print()
            else:
                print("❌ No citations extracted")
                print("Let's debug step by step...")
                
                # Debug: Extract text and check reference section
                from theke.services.pdf_processor import extract_text_from_pdf_file
                
                print("2. Debugging: Extracting raw text...")
                text = await extract_text_from_pdf_file(pdf_path)
                print(f"   📄 Extracted {len(text)} characters of text")
                
                if text:
                    print("   First 500 characters:")
                    print(f"   '{text[:500]}...'")
                    print()
                    
                    print("3. Debugging: Looking for reference section...")
                    ref_section = extractor._find_references_section(text)
                    
                    if ref_section:
                        print(f"   ✅ Found reference section ({len(ref_section)} chars)")
                        print("   First 500 characters:")
                        print(f"   '{ref_section[:500]}...'")
                        print()
                        
                        # Try fallback method
                        print("4. Debugging: Trying citation-dense section...")
                        dense_section = extractor._find_citation_dense_section(text)
                        if dense_section:
                            print(f"   ✅ Found citation-dense section ({len(dense_section)} chars)")
                        else:
                            print("   ❌ No citation-dense section found")
                        print()
                        
                    else:
                        print("   ❌ No reference section found")
                        
                        # Show last part of text (where references usually are)
                        print("   Last 1000 characters of document:")
                        print(f"   '{text[-1000:]}...'")
                        print()
                else:
                    print("   ❌ No text extracted from PDF")
        
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()

async def test_comprehensive_extraction():
    """Test the comprehensive citation extraction (with external APIs disabled for this test)"""
    print("🔍 Testing Comprehensive Citation Extraction\n")
    
    pdf_path = "test.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    try:
        async with EnhancedCitationExtractor() as extractor:
            # Test without external APIs (just PDF extraction)
            print("Testing comprehensive extraction (PDF only)...")
            
            citations = await extractor.extract_citations_comprehensive(
                paper_title="Test Document",
                paper_doi=None,
                pdf_path=pdf_path,
                preferred_source="none"  # This should fallback to PDF only
            )
            
            print(f"✅ Comprehensive extraction found {len(citations)} citations")
            
            if citations:
                # Group by source
                sources = {}
                for citation in citations:
                    source = citation.source
                    if source not in sources:
                        sources[source] = []
                    sources[source].append(citation)
                
                for source, source_citations in sources.items():
                    print(f"   {source}: {len(source_citations)} citations")
                print()
                
                # Show top 5 citations
                top_citations = sorted(citations, key=lambda x: x.confidence, reverse=True)[:5]
                print("🏆 Top 5 citations by confidence:")
                for i, citation in enumerate(top_citations, 1):
                    print(f"  {i}. {citation.title} ({citation.confidence:.2f})")
                print()
                
    except Exception as e:
        print(f"❌ Error in comprehensive extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pdf_citation_extraction())
    print("-" * 60)
    asyncio.run(test_comprehensive_extraction())