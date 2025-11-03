import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Search, 
  Plus, 
  ExternalLink, 
  Calendar,
  Users,
  BookOpen,
  CheckCircle,
  Clock,
  Filter
} from 'lucide-react'
import { externalApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'
import { useDebounce } from '@/hooks/useDebounce'
import { ExternalPaper } from '@/types'

export default function PaperSearch() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSources, setSelectedSources] = useState(['arxiv', 'crossref', 'semantic_scholar'])
  const [addedPapers, setAddedPapers] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  // Debounce search query to avoid excessive API calls
  const debouncedSearchQuery = useDebounce(searchQuery, 500)

  const { data: searchResults = [], isLoading, error } = useQuery({
    queryKey: ['external-search', debouncedSearchQuery, selectedSources],
    queryFn: () => externalApi.searchAll(debouncedSearchQuery, 20, selectedSources),
    enabled: debouncedSearchQuery.length > 2,
  })

  const addPaperMutation = useMutation({
    mutationFn: (paper: ExternalPaper) => externalApi.addFromExternal(paper),
    onSuccess: (addedPaper, originalPaper) => {
      toast.success('論文追加完了', `「${addedPaper.title}」をライブラリに追加しました`)
      setAddedPapers(prev => new Set([...prev, originalPaper.external_id || originalPaper.title]))
      queryClient.invalidateQueries({ queryKey: ['papers'] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || '論文の追加に失敗しました'
      toast.error('追加エラー', errorMessage)
    }
  })

  const handleAddPaper = (paper: ExternalPaper) => {
    if (addedPapers.has(paper.external_id || paper.title)) {
      toast.info('既に追加済み', 'この論文は既にライブラリに追加されています')
      return
    }
    addPaperMutation.mutate(paper)
  }

  const toggleSource = (source: string) => {
    setSelectedSources(prev => 
      prev.includes(source) 
        ? prev.filter(s => s !== source)
        : [...prev, source]
    )
  }

  const sourceLabels = {
    arxiv: 'arXiv',
    crossref: 'Crossref', 
    semantic_scholar: 'Semantic Scholar',
    pubmed: 'PubMed'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">論文検索</h1>
        <p className="text-gray-600 dark:text-gray-300">外部データベースから論文を検索してライブラリに追加</p>
      </div>

      {/* Search Controls */}
      <div className="space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="論文タイトル、著者名、キーワードで検索..."
            className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Source Filters */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 self-center">
            <Filter className="w-4 h-4 inline mr-1" />
            検索対象:
          </span>
          {Object.entries(sourceLabels).map(([key, label]) => (
            <button
              key={key}
              onClick={() => toggleSource(key)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                selectedSources.includes(key)
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 border border-primary-200 dark:border-primary-600'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      <div>
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        )}

        {error && (
          <div className="text-center py-12">
            <p className="text-red-600 dark:text-red-400">検索中にエラーが発生しました</p>
          </div>
        )}

        {debouncedSearchQuery.length > 2 && !isLoading && searchResults.length === 0 && (
          <div className="text-center py-12">
            <Search className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">検索結果がありません</h3>
            <p className="text-gray-600 dark:text-gray-300">別のキーワードで検索してみてください</p>
          </div>
        )}

        {debouncedSearchQuery.length <= 2 && (
          <div className="text-center py-12">
            <Search className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">論文を検索</h3>
            <p className="text-gray-600 dark:text-gray-300">3文字以上入力して検索を開始してください</p>
          </div>
        )}

        {searchResults.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              検索結果 ({searchResults.length}件)
            </h3>
            <div className="grid gap-4">
              {searchResults.map((paper, index) => (
                <SearchResultCard 
                  key={paper.external_id || `${paper.title}-${index}`}
                  paper={paper}
                  onAddPaper={handleAddPaper}
                  isAdded={addedPapers.has(paper.external_id || paper.title)}
                  isAdding={addPaperMutation.isPending}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface SearchResultCardProps {
  paper: ExternalPaper
  onAddPaper: (paper: ExternalPaper) => void
  isAdded: boolean
  isAdding: boolean
}

function SearchResultCard({ paper, onAddPaper, isAdded, isAdding }: SearchResultCardProps) {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h4 className="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2 mb-2">
            {paper.title}
          </h4>
          
          {paper.authors && paper.authors.length > 0 && (
            <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 mb-2">
              <Users className="w-4 h-4 mr-1" />
              {paper.authors.slice(0, 3).join(', ')}
              {paper.authors.length > 3 && ` +${paper.authors.length - 3}人`}
            </div>
          )}

          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-3">
            {paper.year && (
              <div className="flex items-center">
                <Calendar className="w-4 h-4 mr-1" />
                {paper.year}
              </div>
            )}
            {paper.journal && (
              <div className="flex items-center">
                <BookOpen className="w-4 h-4 mr-1" />
                {paper.journal}
              </div>
            )}
            <div className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
              {paper.source}
            </div>
          </div>

          {paper.abstract && (
            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
              {paper.abstract}
            </p>
          )}

          <div className="flex items-center gap-2 mt-3">
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 text-sm flex items-center"
              >
                <ExternalLink className="w-3 h-3 mr-1" />
                元論文
              </a>
            )}
          </div>
        </div>

        <div className="ml-4 flex-shrink-0">
          {isAdded ? (
            <div className="flex items-center text-green-600 dark:text-green-400 text-sm font-medium">
              <CheckCircle className="w-4 h-4 mr-1" />
              追加済み
            </div>
          ) : (
            <button
              onClick={() => onAddPaper(paper)}
              disabled={isAdding}
              className="btn btn-primary btn-sm"
            >
              {isAdding ? (
                <>
                  <Clock className="w-4 h-4 mr-1 animate-spin" />
                  追加中...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-1" />
                  ライブラリに追加
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}