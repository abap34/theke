import { toast } from '@/components/ui/Toaster'
import { citationsApi, papersApi } from '@/services/api'
import { Paper } from '@/types'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import {
  ArrowLeft,
  ArrowRight,
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileText,
  Filter,
  Grid3X3,
  List,
  Plus,
  Search,
  Star,
  Trash2,
  Users
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    yearFrom: '',
    yearTo: '',
    author: '',
    hasSummary: null as boolean | null,
    hasPdf: null as boolean | null
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)
  const [showPdfPanel, setShowPdfPanel] = useState(true)

  // Debounce search query to avoid excessive API calls
  const debouncedSearchQuery = useDebounce(searchQuery, 300)

  const { data: papersResponse, isLoading, error } = useQuery({
    queryKey: ['papers', {
      search: debouncedSearchQuery,
      tag_id: selectedTag,
      sort_by: sortBy,
      sort_order: sortOrder,
      ...filters,
      skip: (currentPage - 1) * pageSize,
      limit: pageSize
    }],
    queryFn: () => papersApi.getAll({
      search: debouncedSearchQuery || undefined,
      tag_id: selectedTag || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      year_from: filters.yearFrom ? parseInt(filters.yearFrom) : undefined,
      year_to: filters.yearTo ? parseInt(filters.yearTo) : undefined,
      author: filters.author || undefined,
      has_summary: filters.hasSummary ?? undefined,
      has_pdf: filters.hasPdf ?? undefined,
      skip: (currentPage - 1) * pageSize,
      limit: pageSize
    }),
  })

  const papers = papersResponse?.papers || []
  const totalPapers = papersResponse?.total || 0
  const totalPages = Math.ceil(totalPapers / pageSize)

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [debouncedSearchQuery, selectedTag, sortBy, sortOrder, filters])

  if (error) {
    toast.error('エラー', '論文の取得に失敗しました')
  }

  return (
    <div className="p-2">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-300">{totalPapers}件の論文が登録されています</p>
        </div>

        <Link
          to="/papers/new"
          className="btn btn-primary btn-md"
        >
          <Plus className="w-4 h-4 mr-2" />
          論文追加
        </Link>
      </div>

      {/* Search and Controls */}
      <div className="space-y-4 mb-8">
        {/* Main Search Bar */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
            <input
              type="text"
              placeholder="タイトル、著者、内容、要約、メモで検索..."
              className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Sort */}
            <select
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('_')
                setSortBy(field)
                setSortOrder(order as 'asc' | 'desc')
              }}
              className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="updated_at_desc">更新日（新しい順）</option>
              <option value="updated_at_asc">更新日（古い順）</option>
              <option value="created_at_desc">作成日（新しい順）</option>
              <option value="created_at_asc">作成日（古い順）</option>
              <option value="title_asc">タイトル（A-Z）</option>
              <option value="title_desc">タイトル（Z-A）</option>
              <option value="year_desc">年（新しい順）</option>
              <option value="year_asc">年（古い順）</option>
            </select>

            {/* Filter Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${showFilters
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 border border-primary-200 dark:border-primary-600'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
            >
              <Filter className="w-4 h-4 mr-2 inline" />
              フィルター
            </button>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white dark:bg-gray-800 text-primary-600 dark:text-primary-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md transition-colors ${viewMode === 'list' ? 'bg-white text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Year Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">年</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="開始年"
                    className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    value={filters.yearFrom}
                    onChange={(e) => setFilters(prev => ({ ...prev, yearFrom: e.target.value }))}
                  />
                  <span className="self-center text-gray-500 dark:text-gray-400">-</span>
                  <input
                    type="number"
                    placeholder="終了年"
                    className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    value={filters.yearTo}
                    onChange={(e) => setFilters(prev => ({ ...prev, yearTo: e.target.value }))}
                  />
                </div>
              </div>

              {/* Author */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">著者</label>
                <input
                  type="text"
                  placeholder="著者名で検索"
                  className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  value={filters.author}
                  onChange={(e) => setFilters(prev => ({ ...prev, author: e.target.value }))}
                />
              </div>

              {/* Has Summary */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">要約</label>
                <select
                  className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  value={filters.hasSummary === null ? '' : filters.hasSummary.toString()}
                  onChange={(e) => {
                    const value = e.target.value === '' ? null : e.target.value === 'true'
                    setFilters(prev => ({ ...prev, hasSummary: value }))
                  }}
                >
                  <option value="">すべて</option>
                  <option value="true">要約あり</option>
                  <option value="false">要約なし</option>
                </select>
              </div>

              {/* Has PDF */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">PDF</label>
                <select
                  className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  value={filters.hasPdf === null ? '' : filters.hasPdf.toString()}
                  onChange={(e) => {
                    const value = e.target.value === '' ? null : e.target.value === 'true'
                    setFilters(prev => ({ ...prev, hasPdf: value }))
                  }}
                >
                  <option value="">すべて</option>
                  <option value="true">PDFあり</option>
                  <option value="false">PDFなし</option>
                </select>
              </div>
            </div>

            {/* Clear Filters */}
            <div className="flex justify-end">
              <button
                onClick={() => {
                  setFilters({
                    yearFrom: '',
                    yearTo: '',
                    author: '',
                    hasSummary: null,
                    hasPdf: null
                  })
                  setSearchQuery('')
                  setSelectedTag(null)
                }}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
              >
                フィルターをクリア
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && papers.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">論文がありません</h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            {debouncedSearchQuery ? '検索条件に一致する論文が見つかりませんでした' : '最初の論文を追加してみましょう'}
          </p>
          <Link to="/papers/new" className="btn btn-primary btn-md">
            <Plus className="w-4 h-4 mr-2" />
            論文を追加
          </Link>
        </div>
      )}

      {/* Papers Grid/List */}
      {!isLoading && papers.length > 0 && (
        <>
          <div className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4'
              : 'space-y-3'
          }>
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} viewMode={viewMode} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-8">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, totalPapers)} 件目 / {totalPapers} 件中
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  前へ
                </button>

                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`px-3 py-2 text-sm font-medium rounded-md ${currentPage === pageNum
                          ? 'bg-primary-600 text-white'
                          : 'text-gray-500 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}
                </div>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  次へ
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

interface PaperCardProps {
  paper: Paper
  viewMode: 'grid' | 'list'
}

// Hook to fetch citation data for a paper
function usePaperCitations(paperId: number) {
  return useQuery({
    queryKey: ['paper-citations', paperId],
    queryFn: async () => {
      const allCitations = await citationsApi.getAll()

      // References: papers this paper cites
      const references = allCitations.filter(c => c.citing_paper_id === paperId)

      // Citations: papers that cite this paper
      const citations = allCitations.filter(c => c.cited_paper_id === paperId)

      return { references, citations }
    },
    enabled: !!paperId
  })
}

function PaperCard({ paper, viewMode }: PaperCardProps) {
  const queryClient = useQueryClient()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const deletePaperMutation = useMutation({
    mutationFn: () => papersApi.delete(paper.id),
    onSuccess: () => {
      toast.success('削除完了', '論文を削除しました')
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      setShowDeleteConfirm(false)
    },
    onError: () => {
      toast.error('エラー', '論文の削除に失敗しました')
    }
  })

  const handleDelete = () => {
    if (showDeleteConfirm) {
      deletePaperMutation.mutate()
    } else {
      setShowDeleteConfirm(true)
      setTimeout(() => setShowDeleteConfirm(false), 3000) // Auto-hide after 3 seconds
    }
  }
  if (viewMode === 'list') {
    return (
      <div className="card card-hover p-5">
        <div className="flex items-start space-x-4">
          {/* PDF Thumbnail */}
          <div className="w-16 h-20 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
            {paper.pdf_path ? (
              <img
                src={`http://localhost:8000/api/papers/${paper.id}/thumbnail`}
                alt={`${paper.title} thumbnail`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  const target = e.target as HTMLImageElement
                  target.style.display = 'none'
                  const parent = target.parentElement
                  if (parent) {
                    parent.innerHTML = '<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>'
                  }
                }}
              />
            ) : (
              <FileText className="w-6 h-6 text-gray-400" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <Link
                  to={`/papers/${paper.id}`}
                  className="text-lg font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2"
                >
                  {paper.title}
                </Link>

                <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 mt-1">
                  <Users className="w-4 h-4 mr-1" />
                  {paper.authors?.slice(0, 3).join(', ') || '著者不明'}
                  {paper.authors && paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                </div>

                {paper.year && (
                  <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 mt-1">
                    <Calendar className="w-4 h-4 mr-1" />
                    {paper.year}
                  </div>
                )}

                {paper.abstract && (
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 line-clamp-2">
                    {paper.abstract}
                  </p>
                )}

                {/* Citation Information */}
                <CitationInfo paperId={paper.id} viewMode="list" />
              </div>

              <div className="flex items-center space-x-2 ml-4">
                {paper.summary && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                    要約済み
                  </span>
                )}
                <button className="text-gray-400 hover:text-yellow-500">
                  <Star className="w-4 h-4" />
                </button>
                <button
                  onClick={handleDelete}
                  className={`text-sm px-2 py-1 rounded transition-colors ${showDeleteConfirm
                    ? 'bg-red-100 text-red-800 hover:bg-red-200'
                    : 'text-gray-400 hover:text-red-500'
                    }`}
                  disabled={deletePaperMutation.isPending}
                >
                  {showDeleteConfirm ? (
                    deletePaperMutation.isPending ? '削除中...' : '確認'
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Tags */}
            {paper.tags && paper.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {paper.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs"
                    style={{
                      backgroundColor: tag.color + '20',
                      color: tag.color
                    }}
                  >
                    {tag.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card card-hover overflow-hidden">
      {/* PDF Thumbnail */}
      <div className="aspect-[3/4] bg-gray-100 flex items-center justify-center overflow-hidden rounded-t-lg">
        {paper.pdf_path ? (
          <img
            src={`http://localhost:8000/api/papers/${paper.id}/thumbnail`}
            alt={`${paper.title} thumbnail`}
            className="w-full h-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              target.style.display = 'none'
              const parent = target.parentElement
              if (parent) {
                parent.innerHTML = '<svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>'
              }
            }}
          />
        ) : (
          <FileText className="w-12 h-12 text-gray-400" />
        )}
      </div>

      <div className="p-3">
        <Link
          to={`/papers/${paper.id}`}
          className="block text-xs font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2 mb-2"
        >
          {paper.title}
        </Link>

        <div className="text-xs text-gray-600 dark:text-gray-300 mb-1">
          {paper.authors?.slice(0, 1).join(', ') || '著者不明'}
          {paper.authors && paper.authors.length > 1 && ` +${paper.authors.length - 1}`}
        </div>

        {paper.year && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">{paper.year}</div>
        )}

        {/* Citation Information */}
        <CitationInfo paperId={paper.id} viewMode="grid" />

        {/* Tags */}
        {paper.tags && paper.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {paper.tags.slice(0, 1).map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs"
                style={{
                  backgroundColor: tag.color + '20',
                  color: tag.color
                }}
              >
                {tag.name}
              </span>
            ))}
            {paper.tags.length > 1 && (
              <span className="text-xs text-gray-500">+{paper.tags.length - 1}</span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {paper.summary && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs bg-green-100 text-green-800">
                要約
              </span>
            )}
          </div>

          <div className="flex items-center space-x-1">
            <button className="text-gray-400 hover:text-yellow-500">
              <Star className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              className={`text-xs px-2 py-1 rounded transition-colors ${showDeleteConfirm
                ? 'bg-red-100 text-red-800 hover:bg-red-200'
                : 'text-gray-400 hover:text-red-500'
                }`}
              disabled={deletePaperMutation.isPending}
            >
              {showDeleteConfirm ? (
                deletePaperMutation.isPending ? '削除中' : '確認'
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Citation Information Component
interface CitationInfoProps {
  paperId: number
  viewMode: 'grid' | 'list'
}

function CitationInfo({ paperId, viewMode }: CitationInfoProps) {
  const { data: citationData, isLoading } = usePaperCitations(paperId)

  if (isLoading || !citationData) {
    return null
  }

  const { references, citations } = citationData
  const hasReferences = references && references.length > 0
  const hasCitations = citations && citations.length > 0

  if (!hasReferences && !hasCitations) {
    return null
  }

  if (viewMode === 'list') {
    return (
      <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
        {hasReferences && (
          <div className="flex items-center gap-1">
            <ArrowRight className="w-3 h-3" />
            <span>引用: {references.length}件</span>
          </div>
        )}
        {hasCitations && (
          <div className="flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" />
            <span>被引用: {citations.length}件</span>
          </div>
        )}
      </div>
    )
  }

  // Grid view
  return (
    <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
      {hasReferences && (
        <div className="flex items-center gap-1">
          <ArrowRight className="w-3 h-3" />
          <span>{references.length}</span>
        </div>
      )}
      {hasCitations && (
        <div className="flex items-center gap-1">
          <ArrowLeft className="w-3 h-3" />
          <span>{citations.length}</span>
        </div>
      )}
    </div>
  )
}