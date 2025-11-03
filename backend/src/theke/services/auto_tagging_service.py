"""
Automatic tagging service for papers.
Analyzes paper titles, abstracts, and keywords to suggest appropriate tags.
Particularly focused on CS and PL research areas.
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

@dataclass
class TagSuggestion:
    """Represents a tag suggestion with confidence score."""
    tag_name: str
    confidence: float
    reasons: List[str]  # Why this tag was suggested
    category: str  # e.g., "pl", "ml", "systems", "theory"

class AutoTaggingService:
    """Service for automatically suggesting tags for papers."""
    
    # Programming Languages keywords and patterns
    PL_KEYWORDS = {
        "type-systems": {
            "keywords": ["type system", "type theory", "typing", "static typing", "dynamic typing", 
                        "type inference", "type checking", "polymorphism", "generics", "dependent types",
                        "linear types", "affine types", "session types", "gradual typing"],
            "confidence_boost": 0.3
        },
        "compilers": {
            "keywords": ["compiler", "compilation", "transpiler", "code generation", "optimization",
                        "llvm", "gcc", "clang", "bytecode", "assembly", "intermediate representation",
                        "parsing", "lexical analysis", "syntax analysis", "semantic analysis"],
            "confidence_boost": 0.3
        },
        "functional-programming": {
            "keywords": ["functional programming", "lambda calculus", "higher-order functions", "currying",
                        "monads", "functors", "applicatives", "immutability", "referential transparency",
                        "haskell", "ocaml", "f#", "scala", "clojure", "lisp", "scheme"],
            "confidence_boost": 0.25
        },
        "static-analysis": {
            "keywords": ["static analysis", "program analysis", "data flow", "control flow", 
                        "abstract interpretation", "symbolic execution", "model checking",
                        "verification", "bug detection", "security analysis", "taint analysis"],
            "confidence_boost": 0.3
        },
        "runtime-systems": {
            "keywords": ["runtime system", "virtual machine", "interpreter", "garbage collection",
                        "memory management", "jvm", "clr", ".net", "gc", "heap", "stack"],
            "confidence_boost": 0.25
        },
        "formal-methods": {
            "keywords": ["formal methods", "formal verification", "theorem proving", "model checking",
                        "specification", "correctness", "proof assistant", "coq", "isabelle", "agda",
                        "lean", "temporal logic", "hoare logic", "separation logic"],
            "confidence_boost": 0.3
        },
        "domain-specific-languages": {
            "keywords": ["domain-specific language", "dsl", "embedded language", "language design",
                        "metaprogramming", "code generation", "template", "macro"],
            "confidence_boost": 0.25
        }
    }
    
    # Machine Learning keywords
    ML_KEYWORDS = {
        "deep-learning": {
            "keywords": ["deep learning", "neural networks", "cnn", "rnn", "lstm", "transformer",
                        "attention", "backpropagation", "gradient descent", "tensorflow", "pytorch"],
            "confidence_boost": 0.3
        },
        "machine-learning": {
            "keywords": ["machine learning", "supervised learning", "unsupervised learning", 
                        "reinforcement learning", "classification", "regression", "clustering"],
            "confidence_boost": 0.25
        },
        "natural-language-processing": {
            "keywords": ["natural language processing", "nlp", "text mining", "sentiment analysis",
                        "language model", "bert", "gpt", "tokenization", "parsing", "generation"],
            "confidence_boost": 0.3
        },
        "computer-vision": {
            "keywords": ["computer vision", "image processing", "object detection", "segmentation",
                        "classification", "recognition", "opencv", "convolution", "feature extraction"],
            "confidence_boost": 0.3
        }
    }
    
    # Systems keywords
    SYSTEMS_KEYWORDS = {
        "distributed-systems": {
            "keywords": ["distributed systems", "consensus", "replication", "consistency", "partition",
                        "microservices", "cloud computing", "scalability", "fault tolerance"],
            "confidence_boost": 0.3
        },
        "operating-systems": {
            "keywords": ["operating system", "kernel", "process", "thread", "scheduling", "memory management",
                        "file system", "device driver", "virtualization", "containers"],
            "confidence_boost": 0.3
        },
        "database": {
            "keywords": ["database", "sql", "nosql", "transaction", "acid", "query optimization",
                        "indexing", "concurrency control", "recovery", "storage"],
            "confidence_boost": 0.25
        },
        "networking": {
            "keywords": ["networking", "protocol", "tcp", "udp", "http", "routing", "switching",
                        "network security", "load balancing", "cdn"],
            "confidence_boost": 0.25
        }
    }
    
    # Theory keywords
    THEORY_KEYWORDS = {
        "algorithms": {
            "keywords": ["algorithm", "complexity", "optimization", "graph algorithms", "sorting",
                        "searching", "dynamic programming", "greedy", "approximation"],
            "confidence_boost": 0.25
        },
        "complexity-theory": {
            "keywords": ["complexity theory", "computational complexity", "p vs np", "time complexity",
                        "space complexity", "polynomial time", "np-complete", "np-hard"],
            "confidence_boost": 0.3
        },
        "cryptography": {
            "keywords": ["cryptography", "encryption", "decryption", "hash function", "digital signature",
                        "public key", "private key", "blockchain", "zero knowledge"],
            "confidence_boost": 0.3
        }
    }
    
    # Human-Computer Interaction keywords  
    HCI_KEYWORDS = {
        "user-interface": {
            "keywords": ["user interface", "ui", "ux", "usability", "interaction design", "visualization",
                        "human factors", "accessibility", "user experience", "interface design"],
            "confidence_boost": 0.25
        },
        "visualization": {
            "keywords": ["visualization", "data visualization", "information visualization", "visual analytics",
                        "charts", "graphs", "interactive visualization", "dashboard"],
            "confidence_boost": 0.25
        }
    }
    
    # Venue-based tag mapping (conferences/journals to tags)
    VENUE_TAGS = {
        "POPL": ["programming-languages", "type-systems", "formal-methods"],
        "PLDI": ["programming-languages", "compilers", "optimization"],
        "ICFP": ["functional-programming", "programming-languages"],
        "OOPSLA": ["object-oriented-programming", "programming-languages"],
        "CC": ["compilers", "optimization"],
        "CGO": ["compilers", "optimization", "performance"],
        "ECOOP": ["object-oriented-programming"],
        "ESOP": ["programming-languages", "formal-methods"],
        "PPDP": ["declarative-programming", "functional-programming"],
        "SLE": ["domain-specific-languages", "language-engineering"],
        "NIPS": ["machine-learning", "deep-learning"],
        "ICML": ["machine-learning", "deep-learning"],
        "ICLR": ["machine-learning", "deep-learning"],
        "ACL": ["natural-language-processing", "machine-learning"],
        "EMNLP": ["natural-language-processing", "machine-learning"],
        "CVPR": ["computer-vision", "machine-learning"],
        "ICCV": ["computer-vision", "machine-learning"],
        "SOSP": ["operating-systems", "systems"],
        "OSDI": ["operating-systems", "distributed-systems"],
        "NSDI": ["networking", "distributed-systems"],
        "SIGMOD": ["database", "systems"],
        "VLDB": ["database", "systems"],
        "STOC": ["theory", "algorithms"],
        "FOCS": ["theory", "algorithms"],
        "ICALP": ["theory", "algorithms"],
        "CHI": ["human-computer-interaction", "user-interface"],
        "UIST": ["user-interface", "interaction-design"]
    }
    
    def __init__(self):
        # Combine all keyword dictionaries
        self.all_keywords = {
            **self.PL_KEYWORDS,
            **self.ML_KEYWORDS, 
            **self.SYSTEMS_KEYWORDS,
            **self.THEORY_KEYWORDS,
            **self.HCI_KEYWORDS
        }
    
    def suggest_tags(self, 
                    title: str, 
                    abstract: Optional[str] = None,
                    authors: Optional[List[str]] = None,
                    venue: Optional[str] = None,
                    existing_keywords: Optional[List[str]] = None) -> List[TagSuggestion]:
        """
        Suggest tags for a paper based on its metadata.
        
        Args:
            title: Paper title
            abstract: Paper abstract
            authors: List of authors
            venue: Conference/journal name
            existing_keywords: Keywords already associated with paper
        
        Returns:
            List of TagSuggestion objects
        """
        suggestions = []
        
        # Combine all text content for analysis
        text_content = title.lower()
        if abstract:
            text_content += " " + abstract.lower()
        if existing_keywords:
            text_content += " " + " ".join(existing_keywords).lower()
        
        # Analyze text content for keyword matches
        keyword_suggestions = self._analyze_keywords(text_content)
        suggestions.extend(keyword_suggestions)
        
        # Analyze venue for automatic tags
        if venue:
            venue_suggestions = self._analyze_venue(venue)
            suggestions.extend(venue_suggestions)
        
        # Analyze authors for research area hints
        if authors:
            author_suggestions = self._analyze_authors(authors)
            suggestions.extend(author_suggestions)
        
        # Merge and deduplicate suggestions
        merged_suggestions = self._merge_suggestions(suggestions)
        
        # Sort by confidence score
        merged_suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        # Return top suggestions
        return merged_suggestions[:10]
    
    def _analyze_keywords(self, text: str) -> List[TagSuggestion]:
        """Analyze text content for keyword matches."""
        suggestions = []
        
        for tag_name, tag_info in self.all_keywords.items():
            confidence = 0.0
            reasons = []
            
            for keyword in tag_info["keywords"]:
                if keyword.lower() in text:
                    confidence += tag_info["confidence_boost"]
                    reasons.append(f"Found keyword: '{keyword}'")
            
            # Normalize confidence (multiple keywords can boost it)
            confidence = min(confidence, 1.0)
            
            if confidence > 0.1:  # Minimum threshold
                category = self._determine_category(tag_name)
                suggestions.append(TagSuggestion(
                    tag_name=tag_name,
                    confidence=confidence,
                    reasons=reasons,
                    category=category
                ))
        
        return suggestions
    
    def _analyze_venue(self, venue: str) -> List[TagSuggestion]:
        """Analyze venue for automatic tag suggestions."""
        suggestions = []
        venue_upper = venue.upper()
        
        # Direct venue mapping
        if venue_upper in self.VENUE_TAGS:
            for tag_name in self.VENUE_TAGS[venue_upper]:
                category = self._determine_category(tag_name)
                suggestions.append(TagSuggestion(
                    tag_name=tag_name,
                    confidence=0.8,  # High confidence for venue-based tags
                    reasons=[f"Published in {venue}"],
                    category=category
                ))
        
        # Pattern matching for venue names
        venue_lower = venue.lower()
        
        if any(pl_word in venue_lower for pl_word in ["programming", "language", "compiler"]):
            suggestions.append(TagSuggestion(
                tag_name="programming-languages",
                confidence=0.6,
                reasons=[f"Venue name contains PL-related terms: {venue}"],
                category="pl"
            ))
        
        if any(ml_word in venue_lower for ml_word in ["machine", "learning", "neural", "ai"]):
            suggestions.append(TagSuggestion(
                tag_name="machine-learning",
                confidence=0.6,
                reasons=[f"Venue name contains ML-related terms: {venue}"],
                category="ml"
            ))
        
        return suggestions
    
    def _analyze_authors(self, authors: List[str]) -> List[TagSuggestion]:
        """Analyze authors for research area hints."""
        suggestions = []
        
        # This could be extended with a database of author research areas
        # For now, we'll use some heuristics based on known researchers
        
        known_pl_researchers = {
            "simon peyton jones", "philip wadler", "martin odersky", "guy steele",
            "robert harper", "frank pfenning", "benjamin pierce", "xavier leroy",
            "matthias felleisen", "shriram krishnamurthi", "dan grossman"
        }
        
        known_ml_researchers = {
            "geoffrey hinton", "yann lecun", "yoshua bengio", "andrew ng",
            "fei-fei li", "christopher manning", "dan klein"
        }
        
        author_names_lower = [author.lower() for author in authors]
        
        for author_name in author_names_lower:
            if any(known in author_name for known in known_pl_researchers):
                suggestions.append(TagSuggestion(
                    tag_name="programming-languages",
                    confidence=0.5,
                    reasons=[f"Known PL researcher: {author_name}"],
                    category="pl"
                ))
            
            if any(known in author_name for known in known_ml_researchers):
                suggestions.append(TagSuggestion(
                    tag_name="machine-learning", 
                    confidence=0.5,
                    reasons=[f"Known ML researcher: {author_name}"],
                    category="ml"
                ))
        
        return suggestions
    
    def _merge_suggestions(self, suggestions: List[TagSuggestion]) -> List[TagSuggestion]:
        """Merge duplicate tag suggestions by combining confidence and reasons."""
        tag_map = defaultdict(lambda: {"confidence": 0.0, "reasons": [], "category": ""})
        
        for suggestion in suggestions:
            tag_name = suggestion.tag_name
            tag_map[tag_name]["confidence"] = max(
                tag_map[tag_name]["confidence"], 
                suggestion.confidence
            )
            tag_map[tag_name]["reasons"].extend(suggestion.reasons)
            tag_map[tag_name]["category"] = suggestion.category
        
        merged = []
        for tag_name, info in tag_map.items():
            merged.append(TagSuggestion(
                tag_name=tag_name,
                confidence=info["confidence"],
                reasons=list(set(info["reasons"])),  # Remove duplicates
                category=info["category"]
            ))
        
        return merged
    
    def _determine_category(self, tag_name: str) -> str:
        """Determine the category of a tag."""
        if tag_name in self.PL_KEYWORDS:
            return "pl"
        elif tag_name in self.ML_KEYWORDS:
            return "ml"
        elif tag_name in self.SYSTEMS_KEYWORDS:
            return "systems"
        elif tag_name in self.THEORY_KEYWORDS:
            return "theory"
        elif tag_name in self.HCI_KEYWORDS:
            return "hci"
        else:
            return "general"
    
    def get_preset_tags(self) -> Dict[str, List[str]]:
        """Get predefined tag categories for UI selection."""
        return {
            "pl": list(self.PL_KEYWORDS.keys()),
            "ml": list(self.ML_KEYWORDS.keys()),
            "systems": list(self.SYSTEMS_KEYWORDS.keys()),
            "theory": list(self.THEORY_KEYWORDS.keys()),
            "hci": list(self.HCI_KEYWORDS.keys())
        }
    
    def suggest_tags_for_existing_papers(self, papers_data: List[Dict]) -> Dict[int, List[TagSuggestion]]:
        """Suggest tags for multiple existing papers."""
        results = {}
        
        for paper_data in papers_data:
            paper_id = paper_data.get("id")
            title = paper_data.get("title", "")
            abstract = paper_data.get("abstract")
            authors = paper_data.get("authors", [])
            venue = paper_data.get("journal") or paper_data.get("venue")
            
            suggestions = self.suggest_tags(
                title=title,
                abstract=abstract,
                authors=authors,
                venue=venue
            )
            
            results[paper_id] = suggestions
        
        return results


# Example usage and testing
async def main():
    """Test auto-tagging service."""
    service = AutoTaggingService()
    
    # Test with a PL paper
    pl_paper = {
        "title": "Type-Safe Higher-Order Modules with Linear Types",
        "abstract": "We present a type system for higher-order modules that supports linear types and ensures memory safety without garbage collection.",
        "authors": ["Andreas Rossberg", "Derek Dreyer"],
        "venue": "POPL"
    }
    
    suggestions = service.suggest_tags(
        title=pl_paper["title"],
        abstract=pl_paper["abstract"],
        authors=pl_paper["authors"],
        venue=pl_paper["venue"]
    )
    
    print(f"Suggestions for PL paper:")
    for suggestion in suggestions[:5]:
        print(f"- {suggestion.tag_name} (confidence: {suggestion.confidence:.2f})")
        print(f"  Reasons: {', '.join(suggestion.reasons)}")
        print(f"  Category: {suggestion.category}")
    
    # Test with ML paper
    ml_paper = {
        "title": "Attention Is All You Need",
        "abstract": "We propose the Transformer, a model architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        "authors": ["Ashish Vaswani", "Noam Shazeer"],
        "venue": "NIPS"
    }
    
    suggestions = service.suggest_tags(
        title=ml_paper["title"],
        abstract=ml_paper["abstract"], 
        authors=ml_paper["authors"],
        venue=ml_paper["venue"]
    )
    
    print(f"\nSuggestions for ML paper:")
    for suggestion in suggestions[:5]:
        print(f"- {suggestion.tag_name} (confidence: {suggestion.confidence:.2f})")
        print(f"  Reasons: {', '.join(suggestion.reasons)}")
        print(f"  Category: {suggestion.category}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())