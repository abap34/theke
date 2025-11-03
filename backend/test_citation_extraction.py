#!/usr/bin/env python3
"""
Test script for improved citation extraction functionality
"""

import sys
sys.path.append('src')

from theke.services.citation_extractor import EnhancedCitationExtractor

# Sample text with different reference section formats
sample_texts = [
    # English academic paper with numbered references
    """
Abstract

This paper presents a novel approach to machine learning...

1. Introduction

Machine learning has shown great promise in recent years...

References

[1] Smith, J. A. (2020). Deep Learning Fundamentals. Journal of AI Research, 45(2), 123-145.

[2] Johnson, M. & Brown, K. (2019). "Neural Networks in Practice," Proceedings of ICML, pp. 234-245.

[3] Davis, P. et al. (2021). Advanced Machine Learning Techniques. MIT Press, Cambridge.

[4] Wilson, R. (2018). Statistical Learning Theory. Nature Machine Intelligence, 2(3), 89-102.

Appendix A

Additional experimental results...
""",

    # Japanese academic paper
    """
概要

本研究では、機械学習における新しいアプローチを提案する...

1. はじめに

近年、機械学習は大きな発展を遂げている...

参考文献

[1] 田中太郎: "深層学習の基礎", 人工知能学会誌, Vol.35, No.2, pp.123-145 (2020)

[2] 山田花子, 佐藤次郎: "ニューラルネットワークの応用", 情報処理学会論文誌, Vol.61, No.3, pp.456-467 (2019)

[3] 鈴木一郎ほか: 機械学習アルゴリズム入門, 朝倉書店 (2021)

謝辞

本研究にご協力いただいた関係者の皆様に感謝いたします...
""",

    # Mixed format with different citation styles
    """
4. Conclusion

Our results demonstrate significant improvements...

5. REFERENCES

1. Anderson, P. (2019). Machine Learning Paradigms. Computer Science Review, 23, 45-67.

2. Brown, L., Davis, M. (2020) "Deep Neural Networks for Classification," International Conference on Learning Representations.

3. Clark, S. et al. (2021). Advances in Reinforcement Learning. Nature, 589(7842), 234-238. doi:10.1038/s41586-021-03068-1

4. Evans, K. (2018). Statistical Methods in AI. Available at: https://arxiv.org/abs/1801.12345

Author Information

Corresponding author: researcher@university.edu
""",
]

async def test_reference_section_detection():
    """Test the improved reference section detection"""
    print("🔍 Testing Reference Section Detection\n")
    
    extractor = EnhancedCitationExtractor()
    
    for i, text in enumerate(sample_texts, 1):
        print(f"--- Test Case {i} ---")
        
        # Test reference section detection
        references_section = extractor._find_references_section(text)
        
        if references_section:
            print(f"✅ References section found ({len(references_section)} chars)")
            print("First 200 characters:")
            print(f"'{references_section[:200].strip()}...'")
            
            # Test citation extraction from the section
            print("\n🔍 Testing citation extraction...")
            test_extractor = EnhancedCitationExtractor()
            citations = await test_extractor._extract_with_regex("dummy.pdf")  # We'll mock this
            
        else:
            print("❌ No references section found")
            
        print()

def test_citation_parsing():
    """Test individual citation parsing functions"""
    print("🔍 Testing Citation Parsing Functions\n")
    
    extractor = EnhancedCitationExtractor()
    
    # Test title cleaning
    test_titles = [
        '"Deep Learning Methods for Natural Language Processing"',
        "Machine Learning: A Probabilistic Perspective.,",
        " 'Advances in Neural Networks'  ",
        "10.1038/nature12345",  # Should be invalid
        "pp. 123-145",  # Should be invalid
        "Vol. 23, No. 4",  # Should be invalid
    ]
    
    print("--- Title Cleaning ---")
    for title in test_titles:
        cleaned = extractor._clean_title(title)
        is_invalid = extractor._is_invalid_title(cleaned)
        status = "❌ Invalid" if is_invalid else "✅ Valid"
        print(f"{status}: '{title}' → '{cleaned}'")
    print()
    
    # Test author parsing
    test_authors = [
        "Smith, J. A.",
        "Johnson, M. & Brown, K.",
        "Davis, P. et al.",
        "田中太郎, 山田花子",
        "Anderson, P., Brown, L., Clark, S.",
        "Wilson, R. [1], Thompson, A. [2]",  # With reference numbers
    ]
    
    print("--- Author Parsing ---")
    for author_str in test_authors:
        parsed = extractor._parse_authors(author_str)
        print(f"'{author_str}' → {parsed}")
    print()
    
    # Test confidence calculation
    print("--- Confidence Calculation ---")
    test_cases = [
        ("Deep Learning for Computer Vision", ["Smith, J.", "Brown, K."], 2020, "Nature", "10.1038/s41586-020-12345-6"),
        ("Short", [], None, "", ""),
        ("A Comprehensive Study of Machine Learning Applications in Healthcare", ["Johnson, M.", "Davis, P.", "Wilson, R."], 2021, "Journal of Medical AI", ""),
    ]
    
    for title, authors, year, journal, doi in test_cases:
        confidence = extractor._calculate_extraction_confidence(title, authors, year, journal, doi, f"[1] {title}")
        print(f"Title: '{title[:50]}{'...' if len(title) > 50 else ''}'")
        print(f"Authors: {len(authors)}, Year: {year}, Journal: '{journal}', DOI: {'Yes' if doi else 'No'}")
        print(f"Confidence: {confidence:.2f}")
        print()

if __name__ == "__main__":
    import asyncio
    
    print("🚀 Testing Improved Citation Extraction\n")
    
    # Run synchronous tests
    test_citation_parsing()
    
    # Run async tests
    asyncio.run(test_reference_section_detection())
    
    print("✅ All tests completed!")