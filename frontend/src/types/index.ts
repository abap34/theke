export interface Paper {
  id: number
  title: string
  authors: string[]
  year?: number
  doi?: string
  journal?: string
  abstract?: string
  pdf_path?: string
  summary?: string
  notes?: string
  external_id?: string
  created_at: string
  updated_at?: string
  tags: Tag[]
}

export interface PaperCreate {
  title: string
  authors: string[]
  year?: number
  doi?: string
  journal?: string
  abstract?: string
  summary?: string
  notes?: string
  external_id?: string
}

export interface PaperUpdate {
  title?: string
  authors?: string[]
  year?: number
  doi?: string
  journal?: string
  abstract?: string
  summary?: string
  notes?: string
  external_id?: string
}

export interface Tag {
  id: number
  name: string
  color: string
  created_at: string
  updated_at?: string
}

export interface TagCreate {
  name: string
  color?: string
}

export interface TagUpdate {
  name?: string
  color?: string
}

export interface Citation {
  id: number
  citing_paper_id: number
  cited_paper_id?: number
  cited_title?: string
  cited_authors?: string[]
  cited_year?: number
  cited_doi?: string
  cited_journal?: string
  context?: string
  status: 'resolved' | 'unresolved' | 'suggested'
  external_id?: string
  created_at: string
  updated_at?: string
}

export interface CitationCreate {
  citing_paper_id: number
  cited_paper_id?: number
  cited_title?: string
  cited_authors?: string[]
  cited_year?: number
  cited_doi?: string
  cited_journal?: string
  context?: string
  status?: string
  external_id?: string
}

export interface NetworkNode {
  id: string
  label: string
  type: 'paper' | 'citation'
  resolved: boolean
  data: Paper | Citation
}

export interface NetworkEdge {
  id: string
  source: string
  target: string
  type: 'citation'
}

export interface ExternalPaper {
  title: string
  authors: string[]
  year?: number
  doi?: string
  journal?: string
  abstract?: string
  external_id?: string
  source: 'arxiv' | 'pubmed' | 'crossref' | 'semantic_scholar'
}

export interface SearchFilters {
  tags?: number[]
  year_from?: number
  year_to?: number
  authors?: string[]
  has_summary?: boolean
  has_pdf?: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}