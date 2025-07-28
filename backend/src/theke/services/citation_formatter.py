from typing import Dict, Callable
from ..models.paper import Paper


def format_apa(paper: Paper) -> str:
    """Format citation in APA style"""
    authors = paper.authors if paper.authors else ["Unknown"]
    
    # Format authors (Last, F. M.)
    if len(authors) == 1:
        author_str = authors[0]
    elif len(authors) <= 6:
        author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
    else:
        author_str = ", ".join(authors[:6]) + ", ... " + authors[-1]
    
    # Build citation
    citation_parts = [author_str]
    
    if paper.year:
        citation_parts.append(f"({paper.year})")
    
    citation_parts.append(f"{paper.title}.")
    
    if paper.journal:
        citation_parts.append(f"*{paper.journal}*.")
    
    if paper.doi:
        citation_parts.append(f"https://doi.org/{paper.doi}")
    
    return " ".join(citation_parts)


def format_mla(paper: Paper) -> str:
    """Format citation in MLA style"""
    authors = paper.authors if paper.authors else ["Unknown"]
    
    # Format authors (Last, First)
    if len(authors) == 1:
        author_str = authors[0]
    elif len(authors) == 2:
        author_str = f"{authors[0]}, and {authors[1]}"
    else:
        author_str = f"{authors[0]}, et al"
    
    # Build citation
    citation_parts = [f'{author_str}. "{paper.title}."']
    
    if paper.journal:
        citation_parts.append(f"*{paper.journal}*,")
    
    if paper.year:
        citation_parts.append(f"{paper.year},")
    
    if paper.doi:
        citation_parts.append(f"doi:{paper.doi}.")
    
    return " ".join(citation_parts)


def format_ieee(paper: Paper) -> str:
    """Format citation in IEEE style"""
    authors = paper.authors if paper.authors else ["Unknown"]
    
    # Format authors (F. M. Last)
    if len(authors) <= 3:
        author_str = ", ".join(authors)
    else:
        author_str = f"{authors[0]} et al."
    
    # Build citation
    citation_parts = [f'{author_str}, "{paper.title},"']
    
    if paper.journal:
        citation_parts.append(f"*{paper.journal}*,")
    
    if paper.year:
        citation_parts.append(f"{paper.year}.")
    
    return " ".join(citation_parts)


def format_chicago(paper: Paper) -> str:
    """Format citation in Chicago style"""
    authors = paper.authors if paper.authors else ["Unknown"]
    
    # Format authors
    if len(authors) == 1:
        author_str = authors[0]
    elif len(authors) <= 3:
        author_str = ", ".join(authors[:-1]) + f", and {authors[-1]}"
    else:
        author_str = f"{authors[0]} et al."
    
    # Build citation
    citation_parts = [f'{author_str}. "{paper.title}."']
    
    if paper.journal:
        citation_parts.append(f"*{paper.journal}*")
    
    if paper.year:
        citation_parts.append(f"({paper.year}).")
    
    if paper.doi:
        citation_parts.append(f"https://doi.org/{paper.doi}.")
    
    return " ".join(citation_parts)


def format_bibtex(paper: Paper) -> str:
    """Format citation in BibTeX format"""
    # Generate BibTeX key
    first_author = paper.authors[0] if paper.authors else "unknown"
    first_author_last = first_author.split()[-1].lower() if first_author else "unknown"
    year = paper.year or "unknown"
    bibtex_key = f"{first_author_last}{year}"
    
    # Build BibTeX entry
    bibtex_parts = [f"@article{{{bibtex_key},"]
    bibtex_parts.append(f'  title = {{{paper.title}}},')
    
    if paper.authors:
        authors_str = " and ".join(paper.authors)
        bibtex_parts.append(f'  author = {{{authors_str}}},')
    
    if paper.journal:
        bibtex_parts.append(f'  journal = {{{paper.journal}}},')
    
    if paper.year:
        bibtex_parts.append(f'  year = {{{paper.year}}},')
    
    if paper.doi:
        bibtex_parts.append(f'  doi = {{{paper.doi}}},')
    
    bibtex_parts.append("}")
    
    return "\n".join(bibtex_parts)


# Registry of citation formatters
CITATION_STYLES: Dict[str, Callable[[Paper], str]] = {
    "apa": format_apa,
    "mla": format_mla,
    "ieee": format_ieee,
    "chicago": format_chicago,
    "bibtex": format_bibtex,
}


def format_citation(paper: Paper, style: str) -> str:
    """Format a citation in the specified style"""
    if style not in CITATION_STYLES:
        raise ValueError(f"Unsupported citation style: {style}")
    
    formatter = CITATION_STYLES[style]
    return formatter(paper)


def get_available_styles() -> list[str]:
    """Get list of available citation styles"""
    return list(CITATION_STYLES.keys())