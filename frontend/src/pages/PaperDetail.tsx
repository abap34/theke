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
  Save,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { papersApi, citationsApi, recommendationApi } from '@/services/api'
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
  const [showPdfPanel, setShowPdfPanel] = useState(true)
  const [summaryJobId, setSummaryJobId] = useState<string | null>(null)
  const [summaryJobStatus, setSummaryJobStatus] = useState<{
    status: string
    progress: number
    progress_message?: string
    error_message?: string
  } | null>(null)

  const { data: paper, isLoading } = useQuery({
    queryKey: ['paper', paperId],
    queryFn: () => papersApi.getById(paperId),
    enabled: !isNaN(paperId),
  })

  // Get citations where this paper cites others (references)
  const { data: references = [] } = useQuery({
    queryKey: ['paper-references', paperId],
    queryFn: () => citationsApi.getAll().then(citations => 
      citations.filter(citation => citation.citing_paper_id === paperId)
    ),
    enabled: !isNaN(paperId),
  })

  // Get citations where this paper is cited by others
  const { data: citations = [] } = useQuery({
    queryKey: ['paper-citations', paperId],
    queryFn: () => citationsApi.getAll().then(citations => 
      citations.filter(citation => citation.cited_paper_id === paperId)
    ),
    enabled: !isNaN(paperId),
  })

  // Get related papers recommendations
  const { data: relatedPapers = [] } = useQuery({
    queryKey: ['related-papers', paperId],
    queryFn: () => recommendationApi.getRelatedPapers(paperId, 5),
    enabled: !isNaN(paperId),
  })

  const { data: authorPapers = [] } = useQuery({
    queryKey: ['author-papers', paperId],
    queryFn: () => recommendationApi.getSimilarByAuthor(paperId, 3),
    enabled: !isNaN(paperId),
  })

  const { data: tagPapers = [] } = useQuery({
    queryKey: ['tag-papers', paperId],
    queryFn: () => recommendationApi.getSimilarByTags(paperId, 3),
    enabled: !isNaN(paperId),
  })

  const extractCitationsMutation = useMutation({
    mutationFn: () => citationsApi.extractFromPaper(paperId),
    onSuccess: (extractedCitations) => {
      console.log('Extracted citations:', extractedCitations);
      
      toast.success(
        '引用抽出完了', 
        `${extractedCitations.length}件の引用を抽出しました`
      );
      
      queryClient.invalidateQueries({ queryKey: ['paper-references', paperId] })
      queryClient.invalidateQueries({ queryKey: ['paper-citations', paperId] })
      queryClient.invalidateQueries({ queryKey: ['citations'] })
    },
    onError: (error: any) => {
      console.error('Citation extraction error:', error);
      const errorMessage = error.message || '引用抽出に失敗しました'
      toast.error('引用抽出エラー', errorMessage)
    }
  })

  const generateSummaryMutation = useMutation({
    mutationFn: () => papersApi.generateSummary(paperId),
    onSuccess: (response) => {
      toast.success('要約生成開始', response.message)
      setSummaryJobId(response.job_id)
      setSummaryJobStatus({
        status: response.status,
        progress: 0,
        progress_message: "要約生成を開始中..."
      })
      // Start polling for job status
      startJobPolling(response.job_id)
    },
    onError: (error: any) => {
      let errorMessage = '要約の生成開始に失敗しました'
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail.includes('API key')) {
          errorMessage = 'LLM APIキーが設定されていません'
        } else if (detail.includes('rate limit')) {
          errorMessage = 'API利用制限に達しました。しばらくしてから再試行してください'
        } else {
          errorMessage = detail
        }
      }
      
      toast.error('要約生成エラー', errorMessage)
      setSummaryJobId(null)
      setSummaryJobStatus(null)
    }
  })

  // Job polling functionality
  const startJobPolling = React.useCallback((jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const jobStatus = await papersApi.getJobStatus(jobId)
        setSummaryJobStatus({
          status: jobStatus.status,
          progress: jobStatus.progress,
          progress_message: jobStatus.progress_message,
          error_message: jobStatus.error_message
        })
        
        if (jobStatus.status === 'completed') {
          clearInterval(pollInterval)
          setSummaryJobId(null)
          setSummaryJobStatus(null)
          toast.success('要約生成完了', '論文の要約を生成しました')
          queryClient.invalidateQueries({ queryKey: ['paper', paperId] })
        } else if (jobStatus.status === 'failed') {
          clearInterval(pollInterval)
          setSummaryJobId(null)
          setSummaryJobStatus(null)
          toast.error('要約生成エラー', jobStatus.error_message || '要約の生成に失敗しました')
        }
      } catch (error) {
        console.error('Job polling error:', error)
      }
    }, 2000) // Poll every 2 seconds
    
    // Cleanup after 10 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
      if (summaryJobId === jobId) {
        setSummaryJobId(null)
        setSummaryJobStatus(null)
        toast.error('要約生成タイムアウト', '要約生成が完了しませんでした')
      }
    }, 600000) // 10 minutes
  }, [summaryJobId, queryClient, paperId])

  // Clean up polling on unmount
  React.useEffect(() => {
    return () => {
      setSummaryJobId(null)
      setSummaryJobStatus(null)
    }
  }, [])

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
          <FileText className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">論文が見つかりません</h3>
          <Link to="/" className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
            ダッシュボードに戻る
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen">
      {/* PDF Panel - Left side, much larger */}
      {showPdfPanel && (
        <div className="w-[60%] h-screen bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shadow-lg flex flex-col">
          <div className="flex-1">
            {paper.pdf_path ? (
              <div className="space-y-4 h-full p-6">
                <div className="h-full bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
                  <iframe
                    src={`http://localhost:8000/${paper.pdf_path}`}
                    className="w-full h-full border-0"
                    title="PDF Viewer"
                  />
                </div>
                <div className="text-center">
                  <a 
                    href={`http://localhost:8000/${paper.pdf_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline btn-sm"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    PDFをダウンロード
                  </a>
                </div>
              </div>
            ) : (
              <div className="h-full bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center justify-center m-6">
                <div className="text-center">
                  <FileText className="mx-auto h-16 w-16 text-gray-400 dark:text-gray-500 mb-4" />
                  <p className="text-gray-600 dark:text-gray-300">PDFファイルが見つかりません</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content - Right side */}
      <div className="flex-1 flex flex-col">
        <div className="p-6 mx-4 flex-1 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between mb-6 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <Link 
                to="/"
                className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white line-clamp-2">
                  {paper.title}
                </h1>
                <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600 dark:text-gray-300">
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
              <button
                onClick={() => setShowPdfPanel(!showPdfPanel)}
                className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                title={showPdfPanel ? "PDFを隠す" : "PDFを表示"}
              >
                {showPdfPanel ? (
                  <ChevronLeft className="w-5 h-5" />
                ) : (
                  <ChevronRight className="w-5 h-5" />
                )}
              </button>
              <Link 
                to={`/papers/${paper.id}/edit`}
                className="btn btn-outline btn-sm"
              >
                <Edit className="w-4 h-4 mr-2" />
              </Link>
              <button 
                onClick={() => deletePaperMutation.mutate()}
                className="btn btn-outline btn-sm text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
              </button>
            </div>
          </div>

          {/* Tags */}
          {paper.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6 flex-shrink-0">
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

          {/* Main Content Area with Scroll */}
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-6">
              {/* Tab Navigation */}
              <div className="card">
                <div className="border-b border-gray-200 dark:border-gray-700">
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
                            ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
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
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">アブストラクト</h3>
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                        {paper.abstract}
                      </p>
                    </div>
                  )}

                  {/* Summary */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">AI要約</h3>
                      <button
                        onClick={() => generateSummaryMutation.mutate()}
                        disabled={generateSummaryMutation.isPending || !!summaryJobId}
                        className="btn btn-outline btn-sm"
                      >
                        {generateSummaryMutation.isPending || summaryJobId ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 mr-1"></div>
                            生成中...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-1" />
                            {paper.summary ? '再生成' : '生成'}
                          </>
                        )}
                      </button>
                    </div>
                    
                    {summaryJobStatus && (
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
                        <div className="flex items-center mb-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                          <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                            {summaryJobStatus.progress_message || '要約を生成しています...'}
                          </span>
                        </div>
                        <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2 mb-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${summaryJobStatus.progress || 0}%` }}
                          ></div>
                        </div>
                        <div className="flex justify-between text-xs text-blue-600 dark:text-blue-400">
                          <span>進行状況: {summaryJobStatus.progress || 0}%</span>
                          <span>ステータス: {summaryJobStatus.status}</span>
                        </div>
                        {summaryJobStatus.error_message && (
                          <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                            エラー: {summaryJobStatus.error_message}
                          </p>
                        )}
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                          論文の長さやLLMサービスの応答時間により、数分かかる場合があります。ページを閉じても処理は継続されます。
                        </p>
                      </div>
                    )}
                    
                    {!summaryJobStatus && (
                      paper.summary ? (
                        <div className="text-sm">
                          <MarkdownRenderer>{paper.summary}</MarkdownRenderer>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                          要約はまだ生成されていません
                        </p>
                      )
                    )}
                  </div>

                  {/* DOI */}
                  {paper.doi && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">DOI</h3>
                      <a 
                        href={`https://doi.org/${paper.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 flex items-center"
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
                          <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-4">
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
                          <p className="text-gray-500 dark:text-gray-400 mb-4">メモはまだ追加されていません</p>
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
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">引用情報</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        PDF本文、OpenAlex、Crossref、Semantic Scholarから統合抽出
                      </p>
                    </div>
                    <button 
                      onClick={() => extractCitationsMutation.mutate()}
                      disabled={extractCitationsMutation.isPending}
                      className="btn btn-primary btn-sm"
                    >
                      {extractCitationsMutation.isPending ? (
                        <>
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                          統合抽出中...
                        </>
                      ) : (
                        '引用を抽出'
                      )}
                    </button>
                  </div>
                  
                  {/* References: Papers this paper cites */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center">
                      <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                      この論文が引用している論文 ({references.length}件)
                    </h4>
                    {references.length === 0 ? (
                      <p className="text-sm text-gray-500 dark:text-gray-400 ml-4">
                        引用している論文はまだ抽出されていません
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {references.map((citation, index) => (
                          <div key={citation.id || index} className="p-3 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded text-xs">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="font-medium text-gray-900 dark:text-white">{citation.cited_title}</div>
                                {citation.cited_authors && citation.cited_authors.length > 0 && (
                                  <div className="text-gray-600 dark:text-gray-300 mt-1">
                                    {citation.cited_authors.join(', ')}
                                  </div>
                                )}
                                {citation.cited_year && (
                                  <div className="text-gray-500 dark:text-gray-400 mt-1">{citation.cited_year}</div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Citations: Papers that cite this paper */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center">
                      <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                      この論文を引用している論文 ({Array.isArray(citations) ? citations.length : 0}件)
                    </h4>
                    {!citations || citations.length === 0 ? (
                      <p className="text-sm text-gray-500 dark:text-gray-400 ml-4">
                        この論文を引用している論文は見つかりません
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {Array.isArray(citations) ? citations.map((citation, index) => (
                          <div key={citation.id || index} className="p-3 bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500 rounded text-xs">
                            <div className="font-medium text-gray-900 dark:text-white">
                              {/* Show the title of the citing paper */}
                              論文ID: {citation.citing_paper_id}
                            </div>
                            <div className="text-gray-600 dark:text-gray-300 mt-1">
                              この論文を引用しています
                            </div>
                          </div>
                        )) : null}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'related' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">関連論文</h3>
                    {relatedPapers.length > 0 ? (
                      <div className="space-y-3">
                        {relatedPapers.map((relatedPaper) => (
                          <div key={relatedPaper.id} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <Link 
                              to={`/papers/${relatedPaper.id}`}
                              className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2"
                            >
                              {relatedPaper.title}
                            </Link>
                            <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                              {relatedPaper.authors.slice(0, 2).join(', ')}
                              {relatedPaper.authors.length > 2 && ` +${relatedPaper.authors.length - 2}`}
                            </div>
                            {relatedPaper.year && (
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{relatedPaper.year}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 dark:text-gray-400">関連論文が見つかりませんでした</p>
                    )}
                  </div>

                  {authorPapers.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">同じ著者の他の論文</h4>
                      <div className="space-y-3">
                        {authorPapers.map((authorPaper) => (
                          <div key={authorPaper.id} className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                            <Link 
                              to={`/papers/${authorPaper.id}`}
                              className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2"
                            >
                              {authorPaper.title}
                            </Link>
                            <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                              {authorPaper.authors.slice(0, 2).join(', ')}
                            </div>
                            {authorPaper.year && (
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{authorPaper.year}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagPapers.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">似たトピックの論文</h4>
                      <div className="space-y-3">
                        {tagPapers.map((tagPaper) => (
                          <div key={tagPaper.id} className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border-l-4 border-green-500">
                            <Link 
                              to={`/papers/${tagPaper.id}`}
                              className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2"
                            >
                              {tagPaper.title}
                            </Link>
                            <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                              {tagPaper.authors.slice(0, 2).join(', ')}
                            </div>
                            {tagPaper.year && (
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{tagPaper.year}</div>
                            )}
                            {tagPaper.tags && tagPaper.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {tagPaper.tags.slice(0, 3).map((tag) => (
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
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}