import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ArrowLeft, 
  Edit, 
  Trash2, 
  Download, 
  Star, 
  Calendar,
  Users,
  BookOpen,
  FileText,
  Sparkles,
  Quote,
  Share,
  ExternalLink,
  Save
} from 'lucide-react'
import { papersApi, citationsApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'
import { MarkdownRenderer, MarkdownEditor } from '@/components/ui/MarkdownRenderer'

export default function PaperDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const paperId = parseInt(id!, 10)

  const [activeTab, setActiveTab] = useState<'overview' | 'notes' | 'citations' | 'related'>('overview')
  const [isEditingNotes, setIsEditingNotes] = useState(false)
  const [notesValue, setNotesValue] = useState('')

  const { data: paper, isLoading } = useQuery({
    queryKey: ['paper', paperId],
    queryFn: () => papersApi.getById(paperId),
    enabled: !isNaN(paperId),
  })

  const { data: citations = [] } = useQuery({
    queryKey: ['paper-citations', paperId],
    queryFn: () => citationsApi.getAll().then(citations => 
      citations.filter(citation => citation.citing_paper_id === paperId)
    ),
    enabled: !isNaN(paperId),
  })

  const extractCitationsMutation = useMutation({
    mutationFn: () => citationsApi.extractFromPaper(paperId),
    onSuccess: (extractedCitations) => {
      toast.success('引用抽出完了', `${extractedCitations.length}件の引用を抽出しました`)
      queryClient.invalidateQueries({ queryKey: ['paper-citations', paperId] })
      queryClient.invalidateQueries({ queryKey: ['citations'] })
    },
    onError: (error: any) => {
      let errorMessage = '引用抽出に失敗しました'
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail.includes('not found on Semantic Scholar')) {
          errorMessage = 'Semantic Scholarでこの論文が見つかりませんでした。タイトルやDOIを確認してください。'
        } else if (detail.includes('no references available')) {
          errorMessage = 'この論文の参考文献が見つかりませんでした。'
        } else {
          errorMessage = detail
        }
      }
      
      toast.error('引用抽出エラー', errorMessage)
    }
  })

  const generateSummaryMutation = useMutation({
    mutationFn: () => papersApi.generateSummary(paperId),
    onSuccess: () => {
      toast.success('要約生成完了', '論文の要約を生成しました')
      queryClient.invalidateQueries({ queryKey: ['paper', paperId] })
    },
    onError: (error: any) => {
      let errorMessage = '要約の生成に失敗しました'
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail.includes('API key')) {
          errorMessage = 'LLM APIキーが設定されていません'
        } else if (detail.includes('rate limit')) {
          errorMessage = 'API利用制限に達しました。しばらくしてから再試行してください'
        } else if (detail.includes('quota')) {
          errorMessage = 'API利用クォータを超過しました'
        } else if (detail.includes('configured')) {
          errorMessage = 'LLM設定に問題があります。APIキーを確認してください'
        } else {
          errorMessage = detail
        }
      }
      
      toast.error('要約生成エラー', errorMessage)
    }
  })

  const deletePaperMutation = useMutation({
    mutationFn: () => papersApi.delete(paperId),
    onSuccess: () => {
      toast.success('削除完了', '論文を削除しました')
      navigate('/')
    },
    onError: () => {
      toast.error('エラー', '論文の削除に失敗しました')
    }
  })

  const updateNotesMutation = useMutation({
    mutationFn: (notes: string) => papersApi.update(paperId, { notes }),
    onSuccess: () => {
      toast.success('保存完了', 'メモを保存しました')
      queryClient.invalidateQueries({ queryKey: ['paper', paperId] })
      setIsEditingNotes(false)
    },
    onError: () => {
      toast.error('エラー', 'メモの保存に失敗しました')
    }
  })

  // Initialize notes value when paper data loads
  React.useEffect(() => {
    if (paper && !isEditingNotes) {
      setNotesValue(paper.notes || '')
    }
  }, [paper, isEditingNotes])

  const handleSaveNotes = () => {
    updateNotesMutation.mutate(notesValue)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!paper) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">論文が見つかりません</h3>
          <Link to="/" className="text-primary-600 hover:text-primary-700">
            ダッシュボードに戻る
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Link 
            to="/"
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 line-clamp-2">
              {paper.title}
            </h1>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600">
              <div className="flex items-center">
                <Users className="w-4 h-4 mr-1" />
                {paper.authors.join(', ')}
              </div>
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
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button className="btn btn-outline btn-sm">
            <Star className="w-4 h-4 mr-2" />
            お気に入り
          </button>
          <Link 
            to={`/papers/${paper.id}/edit`}
            className="btn btn-outline btn-sm"
          >
            <Edit className="w-4 h-4 mr-2" />
            編集
          </Link>
          <button 
            onClick={() => deletePaperMutation.mutate()}
            className="btn btn-outline btn-sm text-red-600 hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            削除
          </button>
        </div>
      </div>

      {/* Tags */}
      {paper.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {paper.tags.map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm"
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PDF Viewer */}
        <div className="lg:col-span-2">
          <div className="card p-6">
            {paper.pdf_path ? (
              <div className="aspect-[3/4] bg-gray-100 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <FileText className="mx-auto h-16 w-16 text-gray-400 mb-4" />
                  <p className="text-gray-600 mb-4">PDF ビューワー</p>
                  <a 
                    href={`http://localhost:8000/${paper.pdf_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary btn-sm"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    PDFをダウンロード
                  </a>
                </div>
              </div>
            ) : (
              <div className="aspect-[3/4] bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <FileText className="mx-auto h-16 w-16 text-gray-400 mb-4" />
                  <p className="text-gray-600">PDFファイルが見つかりません</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Tab Navigation */}
          <div className="card">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6 py-4">
                {[
                  { id: 'overview', label: '概要', icon: FileText },
                  { id: 'notes', label: 'メモ', icon: Edit },
                  { id: 'citations', label: '引用', icon: Quote },
                  { id: 'related', label: '関連', icon: Share },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center space-x-2 text-sm font-medium pb-2 border-b-2 ${
                      activeTab === tab.id
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  {/* Abstract */}
                  {paper.abstract && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-2">アブストラクト</h3>
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {paper.abstract}
                      </p>
                    </div>
                  )}

                  {/* Summary */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900">AI要約</h3>
                      <button
                        onClick={() => generateSummaryMutation.mutate()}
                        disabled={generateSummaryMutation.isPending}
                        className="btn btn-outline btn-sm"
                      >
                        <Sparkles className="w-4 h-4 mr-1" />
                        {generateSummaryMutation.isPending ? '生成中...' : (paper.summary ? '再生成' : '生成')}
                      </button>
                    </div>
                    {paper.summary ? (
                      <div className="text-sm">
                        <MarkdownRenderer>{paper.summary}</MarkdownRenderer>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">
                        要約はまだ生成されていません
                      </p>
                    )}
                  </div>

                  {/* DOI */}
                  {paper.doi && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-2">DOI</h3>
                      <a 
                        href={`https://doi.org/${paper.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary-600 hover:text-primary-700 flex items-center"
                      >
                        {paper.doi}
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'notes' && (
                <div>
                  {isEditingNotes ? (
                    <div className="space-y-4">
                      <MarkdownEditor
                        value={notesValue}
                        onChange={setNotesValue}
                        placeholder="この論文についてのメモを追加..."
                        rows={12}
                      />
                      <div className="flex space-x-2">
                        <button 
                          onClick={handleSaveNotes}
                          disabled={updateNotesMutation.isPending}
                          className="btn btn-primary btn-sm"
                        >
                          <Save className="w-4 h-4 mr-1" />
                          {updateNotesMutation.isPending ? '保存中...' : '保存'}
                        </button>
                        <button 
                          onClick={() => {
                            setIsEditingNotes(false)
                            setNotesValue(paper.notes || '')
                          }}
                          className="btn btn-outline btn-sm"
                        >
                          キャンセル
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      {paper.notes ? (
                        <div className="space-y-3">
                          <div className="bg-gray-50 rounded-md p-4">
                            <MarkdownRenderer>{paper.notes}</MarkdownRenderer>
                          </div>
                          <button 
                            onClick={() => setIsEditingNotes(true)}
                            className="btn btn-outline btn-sm"
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            編集
                          </button>
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <p className="text-gray-500 mb-4">メモはまだ追加されていません</p>
                          <button 
                            onClick={() => setIsEditingNotes(true)}
                            className="btn btn-primary btn-sm"
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            メモを追加
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'citations' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-gray-900">引用情報</h3>
                    <button 
                      onClick={() => extractCitationsMutation.mutate()}
                      disabled={extractCitationsMutation.isPending}
                      className="btn btn-outline btn-sm"
                    >
                      {extractCitationsMutation.isPending ? (
                        <>
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600 mr-2"></div>
                          抽出中...
                        </>
                      ) : (
                        '引用を抽出'
                      )}
                    </button>
                  </div>
                  
                  {citations.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      この論文の引用情報はまだ抽出されていません
                    </p>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-700">
                        {citations.length}件の引用が見つかりました
                      </p>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {citations.slice(0, 10).map((citation, index) => (
                          <div key={citation.id || index} className="p-2 bg-gray-50 rounded text-xs">
                            <div className="font-medium">{citation.cited_title}</div>
                            {citation.cited_authors && citation.cited_authors.length > 0 && (
                              <div className="text-gray-600">
                                {citation.cited_authors.join(', ')}
                              </div>
                            )}
                            {citation.cited_year && (
                              <div className="text-gray-500">{citation.cited_year}</div>
                            )}
                          </div>
                        ))}
                        {citations.length > 10 && (
                          <p className="text-xs text-gray-500">他 {citations.length - 10}件...</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'related' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-gray-900">関連論文</h3>
                  <p className="text-sm text-gray-500">
                    関連論文はまだ見つかりません
                  </p>
                  <Link 
                    to={`/network?focus=${paper.id}`}
                    className="btn btn-outline btn-sm"
                  >
                    ネットワークで確認
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}