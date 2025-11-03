#!/usr/bin/env python3
"""
Test citation pattern matching directly
"""

import sys
import re
sys.path.append('src')

from theke.services.citation_extractor import EnhancedCitationExtractor, CitationMatch

def test_citation_patterns():
    """Test citation pattern matching with real reference text"""
    print("🔍 Testing Citation Pattern Matching\n")
    
    extractor = EnhancedCitationExtractor()
    
    # Sample reference sections with various citation formats
    reference_sections = [
        # IEEE/ACM style
        """
[1] J. Smith, "Deep Learning Fundamentals," Journal of AI Research, vol. 45, no. 2, pp. 123-145, 2020.
[2] M. Johnson and K. Brown, "Neural Networks in Practice," Proceedings of ICML, pp. 234-245, 2019.
[3] P. Davis, R. Wilson, and S. Clark, "Advanced Machine Learning," IEEE Trans. Pattern Analysis, vol. 42, no. 8, pp. 1890-1905, 2021.
""",
        
        # APA style
        """
Anderson, P. (2019). Machine Learning Paradigms. Computer Science Review, 23, 45-67.
Brown, L., & Davis, M. (2020). Deep Neural Networks for Classification. International Conference on Learning Representations.
Clark, S., Evans, K., & Thompson, A. (2021). Advances in Reinforcement Learning. Nature, 589(7842), 234-238.
""",
        
        # Japanese academic style
        """
[1] 田中太郎: "深層学習の基礎", 人工知能学会誌, Vol.35, No.2, pp.123-145 (2020)
[2] 山田花子, 佐藤次郎: "ニューラルネットワークの応用", 情報処理学会論文誌, Vol.61, No.3, pp.456-467 (2019)
[3] 鈴木一郎ほか: 機械学習アルゴリズム入門, 朝倉書店 (2021)
""",
        
        # Mixed with DOI
        """
1. Wilson, R. (2018). Statistical Learning Theory. Nature Machine Intelligence, 2(3), 89-102. doi:10.1038/s42256-018-0001-4
2. Garcia, A. et al. (2020) "Transformer Networks for Language Understanding," arXiv preprint arXiv:2005.14165.
3. Lee, S. M., Kim, J. H. (2019). Computer Vision Applications. Springer, Berlin.
"""
    ]
    
    # Enhanced citation patterns from the updated code
    citation_patterns = [
        # IEEE/ACM style
        (
            r"\[(\d+)\]\s*([^,""]+),\s*[""\"']([^""\"']+)[""\"'],\s*([^,]+),(?:[^,]*,)*\s*(\d{4})",
            ["number", "authors", "title", "journal", "year"],
        ),
        
        # APA style
        (
            r"([^()]+?)\s*\((\d{4})\)\.\s*([^.]+?)\.\s*([^,.\n]+?)(?:,\s*\d+(?:\(\d+\))?(?:,\s*\d+[-–]\d+)?)?\\.?",
            ["authors", "year", "title", "journal"],
        ),
        
        # Japanese style
        (
            r"([^:\uff1a]+)[\uff1a:]\s*[""\"']([^""\"']+)[""\"'],\s*([^,\uff0c]+),[^,(\uff08]*\((\d{4})\)",
            ["authors", "title", "journal", "year"],
        ),
        
        # Simple numbered format
        (
            r"\[(\d+)\]\s*([^,]+),\s*([^,]+),\s*([^,\n]+),\s*(\d{4})",
            ["number", "authors", "title", "journal", "year"],
        ),
        
        # DOI format
        (
            r"([^()]+?)\s*\((\d{4})\)\s*([^.]+?)\.\s*([^.\n]+?)\.[^\n]*doi[:\s]*([^\s\n]+)",
            ["authors", "year", "title", "journal", "doi"],
        ),
    ]
    
    for i, refs in enumerate(reference_sections, 1):
        print(f"--- Reference Section {i} ---")
        print(f"Testing with {len(refs.strip().split(chr(10)))} citation lines\n")
        
        citations = []
        total_matches = 0
        
        for pattern, fields in citation_patterns:
            pattern_matches = 0
            matches = re.finditer(pattern, refs, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                try:
                    citation_data = {}
                    groups = match.groups()
                    
                    for j, field in enumerate(fields):
                        if j < len(groups) and groups[j]:
                            citation_data[field] = groups[j].strip()
                    
                    # Apply the enhanced validation
                    if "title" in citation_data and ("year" in citation_data or "authors" in citation_data):
                        authors_str = citation_data.get("authors", "")
                        title = citation_data["title"]
                        year = None
                        
                        if "year" in citation_data:
                            try:
                                year = int(citation_data["year"])
                                if year < 1900 or year > 2030:
                                    year = None
                            except ValueError:
                                year = None
                        
                        journal = citation_data.get("journal", "")
                        doi = citation_data.get("doi", "")
                        
                        # Clean and validate
                        title = extractor._clean_title(title)
                        
                        if len(title) >= 8 and not extractor._is_invalid_title(title):
                            authors = extractor._parse_authors(authors_str)
                            journal = extractor._clean_journal_name(journal)
                            
                            confidence = extractor._calculate_extraction_confidence(
                                title, authors, year, journal, doi, match.group(0)
                            )
                            
                            citation = CitationMatch(
                                title=title,
                                authors=authors,
                                year=year,
                                journal=journal,
                                doi=doi,
                                confidence=confidence,
                                source="pdf",
                                raw_text=match.group(0)
                            )
                            
                            citations.append(citation)
                            pattern_matches += 1
                            
                except Exception as e:
                    print(f"Error processing match: {e}")
            
            if pattern_matches > 0:
                total_matches += pattern_matches
                print(f"  Pattern matched {pattern_matches} citations")
        
        print(f"\nTotal citations extracted: {total_matches}")
        
        # Display extracted citations
        if citations:
            print("\nExtracted Citations:")
            for j, citation in enumerate(citations[:3], 1):  # Show first 3
                print(f"  {j}. Title: '{citation.title}'")
                print(f"     Authors: {citation.authors}")
                print(f"     Year: {citation.year}")
                print(f"     Journal: '{citation.journal}'")
                print(f"     Confidence: {citation.confidence:.2f}")
                print()
        else:
            print("\n❌ No citations extracted")
        
        print("-" * 60)
        print()

if __name__ == "__main__":
    test_citation_patterns()