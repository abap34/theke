import axios from 'axios'
import type {
  Paper,
  PaperCreate,
  PaperUpdate,
  Tag,
  TagCreate,
  TagUpdate,
  Citation,
  CitationCreate,
  ExternalPaper,
  SearchFilters,
  PaginatedResponse
} from '@/types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
})

// Request interceptor for adding auth headers if needed
api.interceptors.request.use((config) => {
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Papers API
export const papersApi = {
  getAll: async (params?: {
    skip?: number
    limit?: number
    tag_id?: number
    search?: string
  }): Promise<Paper[]> => {
    const response = await api.get('/api/papers', { params })
    return response.data
  },

  getById: async (id: number): Promise<Paper> => {
    const response = await api.get(`/api/papers/${id}`)
    return response.data
  },

  create: async (paper: PaperCreate): Promise<Paper> => {
    const response = await api.post('/api/papers', paper)
    return response.data
  },

  update: async (id: number, paper: PaperUpdate): Promise<Paper> => {
    const response = await api.put(`/api/papers/${id}`, paper)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/papers/${id}`)
  },

  extractMetadata: async (file: File, useLlm: boolean = false): Promise<any> => {
    const formData = new FormData()
    formData.append('file', file)
    if (useLlm) formData.append('use_llm', 'true')
    
    const response = await api.post('/api/papers/extract-metadata', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data.metadata
  },

  upload: async (file: File, metadata?: Partial<PaperCreate>, useLlmExtraction?: boolean): Promise<Paper> => {
    const formData = new FormData()
    formData.append('file', file)
    
    if (metadata?.title) formData.append('title', metadata.title)
    if (metadata?.authors) formData.append('authors', JSON.stringify(metadata.authors))
    if (useLlmExtraction) formData.append('use_llm_extraction', 'true')
    
    const response = await api.post('/api/papers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  generateSummary: async (id: number): Promise<Paper> => {
    const response = await api.post(`/api/papers/${id}/summary`)
    return response.data
  },

  addTag: async (paperId: number, tagId: number): Promise<void> => {
    await api.post(`/api/papers/${paperId}/tags/${tagId}`)
  },

  removeTag: async (paperId: number, tagId: number): Promise<void> => {
    await api.delete(`/api/papers/${paperId}/tags/${tagId}`)
  }
}

// Tags API
export const tagsApi = {
  getAll: async (): Promise<Tag[]> => {
    const response = await api.get('/api/tags')
    return response.data
  },

  create: async (tag: TagCreate): Promise<Tag> => {
    const response = await api.post('/api/tags', tag)
    return response.data
  },

  update: async (id: number, tag: TagUpdate): Promise<Tag> => {
    const response = await api.put(`/api/tags/${id}`, tag)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/tags/${id}`)
  }
}

// Citations API
export const citationsApi = {
  getAll: async (): Promise<Citation[]> => {
    const response = await api.get('/api/citations')
    return response.data
  },

  create: async (citation: CitationCreate): Promise<Citation> => {
    const response = await api.post('/api/citations', citation)
    return response.data
  },

  getNetwork: async (): Promise<{ nodes: any[], edges: any[] }> => {
    const response = await api.get('/api/citations/network')
    return response.data
  },

  formatCitation: async (paperId: number, style: string): Promise<string> => {
    const response = await api.get(`/api/citations/format/${style}`, {
      params: { paper_id: paperId }
    })
    return response.data
  },

  extractFromPaper: async (paperId: number): Promise<Citation[]> => {
    const response = await api.post(`/api/citations/extract/${paperId}`)
    return response.data
  }
}

// External search API
export const externalApi = {
  searchArxiv: async (query: string): Promise<ExternalPaper[]> => {
    const response = await api.get('/api/external/arxiv/search', {
      params: { query }
    })
    return response.data
  },

  searchPubmed: async (query: string): Promise<ExternalPaper[]> => {
    const response = await api.get('/api/external/pubmed/search', {
      params: { query }
    })
    return response.data
  },

  searchCrossref: async (query: string): Promise<ExternalPaper[]> => {
    const response = await api.get('/api/external/crossref/search', {
      params: { query }
    })
    return response.data
  },

  searchSemanticScholar: async (query: string): Promise<ExternalPaper[]> => {
    const response = await api.get('/api/external/semantic-scholar/search', {
      params: { query }
    })
    return response.data
  },

  addFromExternal: async (externalPaper: ExternalPaper): Promise<Paper> => {
    const response = await api.post('/api/citations/add-from-external', externalPaper)
    return response.data
  }
}

export default api