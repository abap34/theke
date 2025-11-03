import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Eye, 
  EyeOff, 
  Plus, 
  Trash2, 
  Users, 
  Tag, 
  BookOpen,
  Bell,
  Search,
  Calendar
} from 'lucide-react'
import { toast } from '@/components/ui/Toaster'

interface WatchItem {
  id: number
  type: 'author' | 'keyword' | 'journal'
  value: string
  active: boolean
  created_at: string
  last_check?: string
  new_papers_count?: number
}

interface NewPaper {
  id: number
  title: string
  authors: string[]
  year?: number
  journal?: string
  matched_type: 'author' | 'keyword' | 'journal'
  matched_value: string
  found_at: string
}

// Mock API functions (replace with actual API calls)
const watchApi = {
  getWatchList: async (): Promise<WatchItem[]> => {
    // Mock data
    return [
      {
        id: 1,
        type: 'author',
        value: 'Geoffrey Hinton',
        active: true,
        created_at: '2024-01-15',
        last_check: '2024-01-20',
        new_papers_count: 3
      },
      {
        id: 2,
        type: 'keyword',
        value: 'transformer architecture',
        active: true,
        created_at: '2024-01-10',
        last_check: '2024-01-20',
        new_papers_count: 8
      },
      {
        id: 3,
        type: 'journal',
        value: 'Nature',
        active: false,
        created_at: '2024-01-05',
        last_check: '2024-01-18',
        new_papers_count: 0
      }
    ]
  },

  addWatch: async (type: string, value: string): Promise<WatchItem> => {
    // Mock response
    return {
      id: Date.now(),
      type: type as 'author' | 'keyword' | 'journal',
      value,
      active: true,
      created_at: new Date().toISOString().split('T')[0]
    }
  },

  toggleWatch: async (id: number): Promise<void> => {
    // Mock toggle
  },

  deleteWatch: async (id: number): Promise<void> => {
    // Mock delete
  },

  getNewPapers: async (watchId: number): Promise<NewPaper[]> => {
    // Mock new papers
    return []
  }
}

export default function WatchList() {
  const [activeTab, setActiveTab] = useState<'list' | 'new'>('list')
  const [showAddForm, setShowAddForm] = useState(false)
  const [newWatchType, setNewWatchType] = useState<'author' | 'keyword' | 'journal'>('author')
  const [newWatchValue, setNewWatchValue] = useState('')
  const queryClient = useQueryClient()

  const { data: watchItems = [], isLoading } = useQuery({
    queryKey: ['watch-list'],
    queryFn: watchApi.getWatchList
  })

  const { data: newPapers = [] } = useQuery({
    queryKey: ['watch-new-papers'],
    queryFn: () => {
      // Get new papers for all active watches
      return Promise.all(
        watchItems
          .filter(item => item.active)
          .map(item => watchApi.getNewPapers(item.id))
      ).then(results => results.flat())
    },
    enabled: watchItems.length > 0
  })

  const addWatchMutation = useMutation({
    mutationFn: ({ type, value }: { type: string, value: string }) => 
      watchApi.addWatch(type, value),
    onSuccess: () => {
      toast.success('ウォッチ追加', 'ウォッチアイテムを追加しました')
      setShowAddForm(false)
      setNewWatchValue('')
      queryClient.invalidateQueries({ queryKey: ['watch-list'] })
    },
    onError: () => {
      toast.error('エラー', 'ウォッチアイテムの追加に失敗しました')
    }
  })

  const toggleWatchMutation = useMutation({
    mutationFn: watchApi.toggleWatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watch-list'] })
    }
  })

  const deleteWatchMutation = useMutation({
    mutationFn: watchApi.deleteWatch,
    onSuccess: () => {
      toast.success('削除完了', 'ウォッチアイテムを削除しました')
      queryClient.invalidateQueries({ queryKey: ['watch-list'] })
    }
  })

  const handleAddWatch = () => {
    if (!newWatchValue.trim()) {
      toast.error('入力エラー', 'ウォッチする項目を入力してください')
      return
    }
    addWatchMutation.mutate({ type: newWatchType, value: newWatchValue.trim() })
  }

  const getTypeIcon = (type: WatchItem['type']) => {
    switch (type) {
      case 'author': return <Users className="w-4 h-4" />
      case 'keyword': return <Tag className="w-4 h-4" />
      case 'journal': return <BookOpen className="w-4 h-4" />
    }
  }

  const getTypeLabel = (type: WatchItem['type']) => {
    switch (type) {
      case 'author': return '著者'
      case 'keyword': return 'キーワード'
      case 'journal': return 'ジャーナル'
    }
  }

  const totalNewPapers = watchItems.reduce((sum, item) => sum + (item.new_papers_count || 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ウォッチリスト</h1>
          <p className="text-gray-600 dark:text-gray-300">
            著者、キーワード、ジャーナルの新着論文を追跡
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="btn btn-primary btn-md"
        >
          <Plus className="w-4 h-4 mr-2" />
          ウォッチ追加
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('list')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'list'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            ウォッチリスト ({watchItems.length})
          </button>
          <button
            onClick={() => setActiveTab('new')}
            className={`py-2 px-1 border-b-2 font-medium text-sm relative ${
              activeTab === 'new'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            新着論文 ({totalNewPapers})
            {totalNewPapers > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                {totalNewPapers > 9 ? '9+' : totalNewPapers}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Add Watch Form */}
      {showAddForm && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              新しいウォッチを追加
            </h3>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  ウォッチタイプ
                </label>
                <div className="flex gap-2">
                  {(['author', 'keyword', 'journal'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setNewWatchType(type)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        newWatchType === type
                          ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 border border-primary-200 dark:border-primary-600'
                          : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      {getTypeIcon(type)}
                      <span className="ml-2">{getTypeLabel(type)}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {getTypeLabel(newWatchType)}名
                </label>
                <input
                  type="text"
                  value={newWatchValue}
                  onChange={(e) => setNewWatchValue(e.target.value)}
                  placeholder={
                    newWatchType === 'author' ? 'Geoffrey Hinton' :
                    newWatchType === 'keyword' ? 'transformer architecture' :
                    'Nature'
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddWatch()}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowAddForm(false)
                  setNewWatchValue('')
                }}
                className="btn btn-outline btn-sm"
              >
                キャンセル
              </button>
              <button
                onClick={handleAddWatch}
                disabled={addWatchMutation.isPending}
                className="btn btn-primary btn-sm"
              >
                {addWatchMutation.isPending ? '追加中...' : 'ウォッチ追加'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {activeTab === 'list' && (
        <div>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : watchItems.length === 0 ? (
            <div className="text-center py-12">
              <Eye className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                ウォッチリストが空です
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                著者、キーワード、ジャーナルを追加して新着論文を追跡しましょう
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {watchItems.map((item) => (
                <div key={item.id} className="card p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${
                        item.type === 'author' ? 'bg-blue-100 dark:bg-blue-900/30' :
                        item.type === 'keyword' ? 'bg-green-100 dark:bg-green-900/30' :
                        'bg-purple-100 dark:bg-purple-900/30'
                      }`}>
                        {getTypeIcon(item.type)}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          {item.value}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {getTypeLabel(item.type)} • 
                          作成: {new Date(item.created_at).toLocaleDateString()}
                          {item.last_check && (
                            <> • 最終確認: {new Date(item.last_check).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {item.new_papers_count && item.new_papers_count > 0 && (
                        <span className="bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 px-2 py-1 rounded-full text-xs font-medium">
                          {item.new_papers_count}件の新着
                        </span>
                      )}
                      
                      <button
                        onClick={() => toggleWatchMutation.mutate(item.id)}
                        className={`p-2 rounded-lg transition-colors ${
                          item.active 
                            ? 'text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30' 
                            : 'text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                        title={item.active ? 'ウォッチを無効化' : 'ウォッチを有効化'}
                      >
                        {item.active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                      </button>

                      <button
                        onClick={() => deleteWatchMutation.mutate(item.id)}
                        className="p-2 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                        title="ウォッチを削除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'new' && (
        <div>
          {newPapers.length === 0 ? (
            <div className="text-center py-12">
              <Bell className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                新着論文はありません
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                ウォッチリストに追加した項目に一致する新しい論文が見つかると、ここに表示されます
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {newPapers.map((paper) => (
                <div key={paper.id} className="card p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900 dark:text-white line-clamp-2 mb-2">
                        {paper.title}
                      </h3>
                      
                      <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 space-x-4 mb-2">
                        <div className="flex items-center">
                          <Users className="w-4 h-4 mr-1" />
                          {paper.authors.slice(0, 3).join(', ')}
                          {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                        </div>
                        {paper.year && (
                          <div className="flex items-center">
                            <Calendar className="w-4 h-4 mr-1" />
                            {paper.year}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          paper.matched_type === 'author' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                          paper.matched_type === 'keyword' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                          'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300'
                        }`}>
                          {getTypeLabel(paper.matched_type)}: {paper.matched_value}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(paper.found_at).toLocaleDateString()}に発見
                        </span>
                      </div>
                    </div>

                    <button className="btn btn-outline btn-sm ml-4">
                      <Plus className="w-4 h-4 mr-1" />
                      追加
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}