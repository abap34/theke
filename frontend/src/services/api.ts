import axios from 'axios'
import type {
  Paper,
  PaperCreate,
  PaperUpdate,
  Tag,
  TagCreate,
  TagUpdate,
  SearchFilters,
  PaginatedResponse
} from '@/types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000, // Default timeout: 30 seconds
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
    sort_by?: string
    sort_order?: string
    year_from?: number
    year_to?: number
    has_summary?: boolean
    has_pdf?: boolean
    author?: string
  }): Promise<{
    papers: Paper[]
    total: number
    skip: number
    limit: number
    has_more: boolean
  }> => {
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

  generateSummary: async (id: number, customPrompt?: string): Promise<{job_id: string, status: string, message: string}> => {
    const response = await api.post(`/api/papers/${id}/summary`, {
      custom_prompt: customPrompt || null
    })
    return response.data
  },

  getJobStatus: async (jobId: string): Promise<{
    id: string
    type: string
    paper_id: number
    status: string
    progress: number
    progress_message?: string
    result?: any
    error_message?: string
    created_at: string
    started_at?: string
    completed_at?: string
  }> => {
    const response = await api.get(`/api/papers/jobs/${jobId}`)
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

// Settings API
export const settingsApi = {
  getSummaryPrompt: async (): Promise<{prompt: string}> => {
    const response = await api.get('/api/settings/summary-prompt')
    return response.data
  },

  updateSummaryPrompt: async (prompt: string): Promise<void> => {
    await api.put('/api/settings/summary-prompt', { prompt })
  },

  getModelSetting: async (): Promise<{model: string}> => {
    const response = await api.get('/api/settings/model')
    return response.data
  },

  updateModelSetting: async (model: string): Promise<void> => {
    await api.put('/api/settings/model', { model })
  }
}

export default api