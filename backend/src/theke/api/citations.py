from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import citation as citation_crud
from ..schemas import citation as citation_schema
from ..services.citation_formatter import CITATION_STYLES, format_citation
from ..services.llm_service import extract_citations_from_paper

router = APIRouter()


@router.get("/", response_model=List[citation_schema.CitationPublic])
def get_citations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all citations"""
    citations = citation_crud.get_citations(db=db, skip=skip, limit=limit)
    return citations


@router.post("/", response_model=citation_schema.Citation)
def create_citation(
    citation: citation_schema.CitationCreate, db: Session = Depends(get_db)
):
    """Create a new citation"""
    return citation_crud.create_citation(db=db, citation=citation)


@router.get("/network")
def get_citation_network_legacy(db: Session = Depends(get_db)):
    """Get citation network data for graph visualization (legacy)"""
    return citation_crud.get_citation_network(db=db)


@router.get("/format/{style}")
def format_citation_endpoint(style: str, paper_id: int, db: Session = Depends(get_db)):
    """Generate formatted citation for a paper"""
    if style not in CITATION_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported citation style. Available: {list(CITATION_STYLES.keys())}",
        )

    from ..crud.paper import get_paper

    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        formatted_citation = format_citation(paper, style)
        return {"citation": formatted_citation, "style": style}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/{paper_id}", response_model=List[citation_schema.CitationPublic])
async def extract_citations(
    paper_id: int,
    direction: str = "both",  # "references", "citations", "both"
    method: str = "comprehensive",  # "comprehensive", "openalex", "crossref", "semantic_scholar", "pdf_only"
    db: Session = Depends(get_db),
):
    """引用抽出 - 双方向サポート"""
    from ..crud.paper import get_paper
    from ..services.bidirectional_citation_service import BidirectionalCitationService

    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        saved_citations = []

        async with BidirectionalCitationService() as service:
            # 双方向の引用関係を抽出
            relations = await service.extract_comprehensive_relations(
                paper_id=paper_id,
                paper_title=paper.title,
                paper_doi=paper.doi,
                pdf_path=paper.pdf_path,
                direction=direction,
            )

            # 既存の引用データをクリア
            citation_crud.delete_citations_by_paper(db=db, paper_id=paper_id)

            # 参照文献（この論文が引用している論文）- 信頼度フィルタリングなし（純粋なunion）
            if direction in ["both", "references"]:
                for relation in relations.get("references", []):
                    citation_create = citation_schema.CitationCreate(
                        citing_paper_id=paper_id,
                        cited_title=relation.related_paper_title,
                        cited_authors=relation.related_paper_authors,
                        cited_year=relation.related_paper_year,
                        cited_journal=relation.related_paper_journal,
                        cited_doi=relation.related_paper_doi,
                        extraction_source=relation.source,
                        confidence_score=relation.confidence,
                        status="verified",  # すべてを検証済みとして扱う
                    )
                    saved_citation = citation_crud.create_citation(
                        db=db, citation=citation_create
                    )
                    saved_citations.append(saved_citation)

            # 引用元文献（この論文を引用している論文）- 別途保存ロジックが必要
            citing_papers_count = len(relations.get("citing_papers", []))

            # 論文の引用統計を更新
            paper.citation_count = citing_papers_count
            paper.reference_count = len(relations.get("references", []))
            db.commit()

        print(
            f"Successfully extracted {len(saved_citations)} citations with direction: {direction}"
        )
        return saved_citations

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract citations: {str(e)}"
        )


@router.get("/network/{paper_id}")
async def get_citation_network_enhanced(
    paper_id: int,
    depth: int = 2,  # 引用関係の深度
    direction: str = "both",  # "references", "citations", "both"
    confidence_threshold: float = 0.6,
    db: Session = Depends(get_db),
):
    """引用ネットワーク可視化データ"""
    from ..crud.paper import get_paper
    from ..services.bidirectional_citation_service import BidirectionalCitationService

    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        async with BidirectionalCitationService() as service:
            relations = await service.extract_comprehensive_relations(
                paper_id=paper_id,
                paper_title=paper.title,
                paper_doi=paper.doi,
                direction=direction,
            )

            # 信頼性でフィルタリング
            filtered_relations = {}
            for rel_type, rel_list in relations.items():
                filtered_relations[rel_type] = [
                    rel for rel in rel_list if rel.confidence >= confidence_threshold
                ]

            # ネットワークグラフデータを構築
            network_data = service.build_citation_network(filtered_relations)

            # 中心ノードに論文の詳細情報を追加
            if network_data.get("nodes"):
                for node in network_data["nodes"]:
                    if node.get("type") == "center":
                        node.update(
                            {
                                "label": (
                                    paper.title[:50] + "..."
                                    if len(paper.title) > 50
                                    else paper.title
                                ),
                                "authors": paper.authors,
                                "year": paper.year,
                                "doi": paper.doi,
                            }
                        )
                        break

            return {
                "network": network_data,
                "paper": {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "doi": paper.doi,
                },
                "settings": {
                    "depth": depth,
                    "direction": direction,
                    "confidence_threshold": confidence_threshold,
                },
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to build citation network: {str(e)}"
        )


# 既存のエンドポイントを更新
@router.post(
    "/extract/{paper_id}/legacy", response_model=List[citation_schema.CitationPublic]
)
async def extract_citations_legacy(
    paper_id: int,
    method: str = "comprehensive",  # "comprehensive", "openalex", "crossref", "semantic_scholar", "pdf_only"
    source: str = "openalex",  # preferred external source for comprehensive method
    db: Session = Depends(get_db),
):
    """Extract citations from a paper using enhanced extraction methods"""
    from ..crud.paper import get_paper
    from ..services.enhanced_citation_extractor import EnhancedCitationExtractor

    paper = get_paper(db=db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        extracted_citations = []

        if method == "comprehensive":
            # 新しい強化された抽出方法を使用（優先ソース指定可能）
            async with EnhancedCitationExtractor() as extractor:
                citations = await extractor.extract_citations_comprehensive(
                    paper_title=paper.title,
                    paper_doi=paper.doi,
                    pdf_path=paper.pdf_path,
                    preferred_source=source,
                )
                extracted_citations = [
                    {
                        "title": c.title,
                        "authors": c.authors,
                        "year": c.year,
                        "journal": c.journal,
                        "doi": c.doi,
                        "confidence": c.confidence,
                        "source": c.source,
                    }
                    for c in citations
                ]
        elif method == "openalex":
            # OpenAlex専用抽出
            from ..services.openalex_service import extract_citations_from_openalex

            extracted_citations = await extract_citations_from_openalex(
                paper_title=paper.title, paper_doi=paper.doi
            )
        elif method == "crossref":
            # Crossref専用抽出
            from ..services.crossref_service import extract_citations_from_crossref

            extracted_citations = await extract_citations_from_crossref(
                paper_title=paper.title, paper_doi=paper.doi
            )
        elif method == "semantic_scholar":
            # 新しい強化されたSemantic Scholar抽出
            from ..services.enhanced_citation_extractor import (
                EnhancedCitationExtractor as NewExtractor,
            )

            async with NewExtractor() as extractor:
                citations = await extractor._extract_from_semantic_scholar(
                    paper.doi, paper.title
                )
                extracted_citations = [
                    {
                        "title": c.title,
                        "authors": c.authors,
                        "year": c.year,
                        "journal": c.journal,
                        "doi": c.doi,
                        "confidence": c.confidence,
                        "source": c.source,
                    }
                    for c in citations
                ]
        elif method == "pdf_only":
            # PDF本文からのみ抽出
            if paper.pdf_path:
                from ..services.enhanced_citation_extractor import (
                    EnhancedCitationExtractor,
                )

                async with EnhancedCitationExtractor() as extractor:
                    citations = await extractor._extract_from_pdf(paper.pdf_path)
                    extracted_citations = [
                        {
                            "title": c.title,
                            "authors": c.authors,
                            "year": c.year,
                            "journal": c.journal,
                            "doi": c.doi,
                            "confidence": c.confidence,
                            "source": c.source,
                        }
                        for c in citations
                    ]
            else:
                raise HTTPException(
                    status_code=400, detail="PDF file not available for this paper"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid extraction method. Use: comprehensive, openalex, crossref, semantic_scholar, or pdf_only",
            )

        if not extracted_citations:
            raise HTTPException(
                status_code=404, detail="No citations found with the selected method"
            )

        # Clear existing citations for this paper
        citation_crud.delete_citations_by_paper(db=db, paper_id=paper_id)

        # Save extracted citations to database
        saved_citations = []
        for citation_data in extracted_citations:
            # 信頼性スコアに基づいてステータスを決定
            confidence = getattr(citation_data, 'confidence', citation_data.get('confidence', 0.0)) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else 0.0
            status = "verified" if confidence > 0.8 else "pending"

            citation_create = citation_schema.CitationCreate(
                citing_paper_id=paper_id,
                cited_title=getattr(citation_data, 'title', citation_data.get('title')) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else None,
                cited_authors=getattr(citation_data, 'authors', citation_data.get('authors', [])) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else [],
                cited_year=getattr(citation_data, 'year', citation_data.get('year')) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else None,
                cited_journal=getattr(citation_data, 'journal', citation_data.get('journal')) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else None,
                cited_doi=getattr(citation_data, 'doi', citation_data.get('doi')) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else None,
                extraction_source=getattr(citation_data, 'source', citation_data.get('source', 'unknown')) if hasattr(citation_data, '__dict__') or isinstance(citation_data, dict) else 'unknown',
                confidence_score=confidence,
                status=status,
            )
            saved_citation = citation_crud.create_citation(
                db=db, citation=citation_create
            )
            saved_citations.append(saved_citation)

        print(
            f"Successfully extracted {len(saved_citations)} citations using method: {method}"
        )
        return saved_citations

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract citations: {str(e)}"
        )


@router.get("/{citation_id}", response_model=citation_schema.CitationPublic)
def get_citation(citation_id: int, db: Session = Depends(get_db)):
    """Get a specific citation by ID"""
    citation = citation_crud.get_citation(db=db, citation_id=citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation


@router.put("/{citation_id}", response_model=citation_schema.CitationPublic)
def update_citation(
    citation_id: int,
    citation_update: citation_schema.CitationUpdate,
    db: Session = Depends(get_db),
):
    """Update a citation"""
    citation = citation_crud.update_citation(
        db=db, citation_id=citation_id, citation_update=citation_update
    )
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation


@router.delete("/{citation_id}")
def delete_citation(citation_id: int, db: Session = Depends(get_db)):
    """Delete a citation"""
    success = citation_crud.delete_citation(db=db, citation_id=citation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Citation not found")
    return {"message": "Citation deleted successfully"}


@router.post("/{citation_id}/resolve")
def resolve_citation(
    citation_id: int, cited_paper_id: int, db: Session = Depends(get_db)
):
    """Resolve an unresolved citation by linking it to an existing paper"""
    citation = citation_crud.resolve_citation(
        db=db, citation_id=citation_id, cited_paper_id=cited_paper_id
    )
    if not citation:
        raise HTTPException(
            status_code=404, detail="Citation or target paper not found"
        )
    return citation


@router.get("/paper/{paper_id}", response_model=List[citation_schema.CitationPublic])
def get_paper_citations(paper_id: int, db: Session = Depends(get_db)):
    """Get all citations for a specific paper"""
    citations = citation_crud.get_citations_by_paper(db=db, paper_id=paper_id)
    return citations
