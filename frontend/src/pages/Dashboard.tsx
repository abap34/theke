import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { 
  Search, 
  Filter, 
  Grid3X3, 
  List, 
  FileText, 
  Calendar,
  Users,
  ExternalLink,
  Star,
  Plus,
  Trash2,
  MoreVertical
} from 'lucide-react'
import { papersApi } from '@/services/api'
import { Paper } from '@/types'
import { toast } from '@/components/ui/Toaster'

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<number | null>(null)

  const { data: papers = [], isLoading, error } = useQuery({
    queryKey: ['papers', { search: searchQuery, tag_id: selectedTag }],
    queryFn: () => papersApi.getAll({ 
      search: searchQuery || undefined,
      tag_id: selectedTag || undefined
    }),
  })

  if (error) {
    toast.error('エラー', '論文の取得に失敗しました')
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">論文ダッシュボード</h1>
          <p className="text-gray-600">{papers.length}件の論文が登録されています</p>
        </div>
        
        <Link 
          to="/papers/new"
          className="btn btn-primary btn-md"
        >
          <Plus className="w-4 h-4 mr-2" />
          論文追加
        </Link>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col lg:flex-row gap-4 mb-8">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="タイトル、著者、内容で検索..."
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
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

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && papers.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">論文がありません</h3>
          <p className="text-gray-600 mb-6">
            {searchQuery ? '検索条件に一致する論文が見つかりませんでした' : '最初の論文を追加してみましょう'}
          </p>
          <Link to="/papers/new" className="btn btn-primary btn-md">
            <Plus className="w-4 h-4 mr-2" />
            論文を追加
          </Link>
        </div>
      )}

      {/* Papers Grid/List */}
      {!isLoading && papers.length > 0 && (
        <div className={
          viewMode === 'grid' 
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
            : 'space-y-4'
        }>
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} viewMode={viewMode} />
          ))}
        </div>
      )}
    </div>
  )
}

interface PaperCardProps {
  paper: Paper
  viewMode: 'grid' | 'list'
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
          {/* PDF Thumbnail placeholder */}
          <div className="w-16 h-20 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="w-6 h-6 text-gray-400" />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <Link 
                  to={`/papers/${paper.id}`}
                  className="text-lg font-semibold text-gray-900 hover:text-primary-600 line-clamp-2"
                >
                  {paper.title}
                </Link>
                
                <div className="flex items-center text-sm text-gray-600 mt-1">
                  <Users className="w-4 h-4 mr-1" />
                  {paper.authors.slice(0, 3).join(', ')}
                  {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                </div>
                
                {paper.year && (
                  <div className="flex items-center text-sm text-gray-600 mt-1">
                    <Calendar className="w-4 h-4 mr-1" />
                    {paper.year}
                  </div>
                )}
                
                {paper.abstract && (
                  <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                    {paper.abstract}
                  </p>
                )}
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
                  className={`text-sm px-2 py-1 rounded transition-colors ${
                    showDeleteConfirm 
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
            {paper.tags.length > 0 && (
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
      <div className="aspect-[3/4] bg-gray-100 flex items-center justify-center">
        <FileText className="w-12 h-12 text-gray-400" />
      </div>
      
      <div className="p-5">
        <Link 
          to={`/papers/${paper.id}`}
          className="block text-sm font-semibold text-gray-900 hover:text-primary-600 line-clamp-2 mb-2"
        >
          {paper.title}
        </Link>
        
        <div className="text-xs text-gray-600 mb-2">
          {paper.authors.slice(0, 2).join(', ')}
          {paper.authors.length > 2 && ` +${paper.authors.length - 2}`}
        </div>
        
        {paper.year && (
          <div className="text-xs text-gray-500 mb-3">{paper.year}</div>
        )}
        
        {/* Tags */}
        {paper.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {paper.tags.slice(0, 2).map((tag) => (
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
            {paper.tags.length > 2 && (
              <span className="text-xs text-gray-500">+{paper.tags.length - 2}</span>
            )}
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {paper.summary && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                要約済み
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-1">
            <button className="text-gray-400 hover:text-yellow-500">
              <Star className="w-4 h-4" />
            </button>
            <button 
              onClick={handleDelete}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                showDeleteConfirm 
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