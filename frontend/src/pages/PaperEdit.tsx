import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useFieldArray } from 'react-hook-form'
import { ArrowLeft, Upload, X, Plus, Save } from 'lucide-react'
import { papersApi, tagsApi } from '@/services/api'
import { PaperCreate, PaperUpdate, Tag } from '@/types'
import { toast } from '@/components/ui/Toaster'

type FormData = {
  title: string
  authors: { name: string }[]
  year: number | null
  doi: string
  journal: string
  abstract: string
  notes: string
  selectedTags: number[]
}

export default function PaperEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = id !== undefined
  const paperId = isEditing ? parseInt(id, 10) : null

  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [useLlmExtraction, setUseLlmExtraction] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [extractedMetadata, setExtractedMetadata] = useState<any>(null)
  const [isInitialExtracting, setIsInitialExtracting] = useState(false)

  const { data: paper } = useQuery({
    queryKey: ['paper', paperId],
    queryFn: () => papersApi.getById(paperId!),
    enabled: isEditing && !isNaN(paperId!),
  })

  const { data: tags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: () => tagsApi.getAll(),
  })

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isValid }
  } = useForm<FormData>({
    defaultValues: {
      title: '',
      authors: [{ name: '' }],
      year: null,
      doi: '',
      journal: '',
      abstract: '',
      notes: '',
      selectedTags: []
    }
  })

  const { fields: authorFields, append: appendAuthor, remove: removeAuthor } = useFieldArray({
    control,
    name: 'authors'
  })

  // Populate form when editing
  useEffect(() => {
    if (paper && isEditing) {
      setValue('title', paper.title)
      setValue('authors', paper.authors.map(name => ({ name })))
      setValue('year', paper.year)
      setValue('doi', paper.doi || '')
      setValue('journal', paper.journal || '')
      setValue('abstract', paper.abstract || '')
      setValue('notes', paper.notes || '')
      setValue('selectedTags', paper.tags.map(tag => tag.id))
    }
  }, [paper, isEditing, setValue])

  const createPaperMutation = useMutation({
    mutationFn: (data: PaperCreate) => papersApi.create(data),
    onSuccess: (newPaper) => {
      toast.success('作成完了', '論文を作成しました')
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      navigate(`/papers/${newPaper.id}`)
    },
    onError: () => {
      toast.error('エラー', '論文の作成に失敗しました')
    }
  })

  const updatePaperMutation = useMutation({
    mutationFn: ({ id, data }: { id: number, data: PaperUpdate }) => 
      papersApi.update(id, data),
    onSuccess: () => {
      toast.success('更新完了', '論文を更新しました')
      queryClient.invalidateQueries({ queryKey: ['paper', paperId] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      navigate(`/papers/${paperId}`)
    },
    onError: () => {
      toast.error('エラー', '論文の更新に失敗しました')
    }
  })

  const uploadPaperMutation = useMutation({
    mutationFn: ({ file, metadata, useLlm }: { file: File, metadata: Partial<PaperCreate>, useLlm?: boolean }) =>
      papersApi.upload(file, metadata, useLlm),
    onSuccess: async (newPaper) => {
      toast.success('アップロード完了', 'PDFから論文を作成しました')
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      
      // Add 0.5 second delay after PDF upload
      await new Promise(resolve => setTimeout(resolve, 500))
      
      
      // すべての処理が完了してから画面遷移
      navigate(`/papers/${newPaper.id}`)
    },
    onError: () => {
      toast.error('エラー', 'PDFのアップロードに失敗しました')
    }
  })

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (file.type !== 'application/pdf') {
      toast.error('エラー', 'PDFファイルを選択してください')
      return
    }

    setUploadedFile(file)
    setIsInitialExtracting(true)
    setExtractedMetadata(null)

    try {
      toast.info('抽出中', 'PDFからメタデータを抽出しています...')
      
      // 規則ベースで抽出（デフォルト）
      const metadata = await papersApi.extractMetadata(file, false)
      setExtractedMetadata(metadata)
      
      // フォームに抽出結果を設定
      if (metadata.title) setValue('title', metadata.title)
      if (metadata.authors && metadata.authors.length > 0) {
        setValue('authors', metadata.authors.map((name: string) => ({ name })))
      }
      if (metadata.year) setValue('year', metadata.year)
      if (metadata.journal) setValue('journal', metadata.journal)
      if (metadata.abstract) setValue('abstract', metadata.abstract)
      if (metadata.doi) setValue('doi', metadata.doi)
      
      toast.success('抽出完了', '規則ベースでメタデータを抽出しました')
    } catch (error) {
      toast.error('エラー', 'PDFの読み込みに失敗しました')
      // フォールバック：ファイル名をタイトルに設定
      const filename = file.name.replace('.pdf', '')
      setValue('title', filename)
    } finally {
      setIsInitialExtracting(false)
    }
  }

  const handleLlmExtraction = async () => {
    if (!uploadedFile) return

    setIsExtracting(true)
    try {
      toast.info('AI抽出中', 'LLMでメタデータを再抽出しています...')
      
      // LLMで抽出
      const metadata = await papersApi.extractMetadata(uploadedFile, true)
      setExtractedMetadata(metadata)
      
      // フォームに抽出結果を設定
      if (metadata.title) setValue('title', metadata.title)
      if (metadata.authors && metadata.authors.length > 0) {
        setValue('authors', metadata.authors.map((name: string) => ({ name })))
      }
      if (metadata.year) setValue('year', metadata.year)
      if (metadata.journal) setValue('journal', metadata.journal)
      if (metadata.abstract) setValue('abstract', metadata.abstract)
      if (metadata.doi) setValue('doi', metadata.doi)
      
      toast.success('AI抽出完了', 'LLMによるメタデータ抽出が完了しました')
    } catch (error: any) {
      let errorMessage = 'AIによる抽出に失敗しました'
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail.includes('API key') || detail.includes('configured')) {
          errorMessage = 'LLM APIキーが設定されていません。設定を確認してください。'
        } else if (detail.includes('rate limit')) {
          errorMessage = 'API利用制限に達しました。しばらくしてから再試行してください。'
        } else if (detail.includes('quota')) {
          errorMessage = 'API利用クォータを超過しました。請求情報を確認してください。'
        } else {
          errorMessage = detail
        }
      }
      
      toast.error('AI抽出エラー', errorMessage)
    } finally {
      setIsExtracting(false)
    }
  }

  const onSubmit = (data: FormData) => {
    const paperData = {
      title: data.title,
      authors: data.authors.map(a => a.name).filter(name => name.trim() !== ''),
      year: data.year,
      doi: data.doi || undefined,
      journal: data.journal || undefined,
      abstract: data.abstract || undefined,
      notes: data.notes || undefined,
    }

    if (uploadedFile && !isEditing) {
      // Upload new PDF
      uploadPaperMutation.mutate({ file: uploadedFile, metadata: paperData, useLlm: useLlmExtraction })
    } else if (isEditing && paperId) {
      // Update existing paper
      updatePaperMutation.mutate({ id: paperId, data: paperData })
    } else {
      // Create new paper without PDF
      createPaperMutation.mutate(paperData)
    }
  }

  const selectedTags = watch('selectedTags')

  const isProcessing = uploadPaperMutation.isPending || createPaperMutation.isPending || updatePaperMutation.isPending

  return (
    <div className="max-w-4xl mx-auto p-6 relative">
      {/* Processing Overlay */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600 mr-3"></div>
              <h3 className="text-lg font-medium text-gray-900">
                {uploadPaperMutation.isPending ? 'アップロード中' : '保存中'}
              </h3>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              {uploadPaperMutation.isPending ? 
                'PDFをアップロードしています。完了まで画面を閉じないでください。' :
                '論文を保存しています...'
              }
            </p>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Link to={isEditing ? `/papers/${paperId}` : '/'} className="p-2 rounded-md hover:bg-gray-100">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEditing ? '論文を編集' : '論文を追加'}
          </h1>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <fieldset disabled={isProcessing} className="space-y-6">
        {/* PDF Upload (only for new papers) */}
        {!isEditing && (
          <div className="card p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">PDFアップロード</h3>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
              <div className="text-center">
                <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <div className="flex text-sm text-gray-600">
                  <label className="relative cursor-pointer bg-white rounded-md font-medium text-primary-600 hover:text-primary-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500">
                    <span>PDFファイルをアップロード</span>
                    <input
                      type="file"
                      accept=".pdf"
                      className="sr-only"
                      onChange={handleFileUpload}
                      disabled={isUploading}
                    />
                  </label>
                  <p className="pl-1">またはドラッグ&ドロップ</p>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  PDF形式のみ対応（最大50MB）
                </p>
              </div>
            </div>
            
            {uploadedFile && (
              <div className="mt-4 space-y-3">
                <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                  <span className="text-sm text-gray-700">{uploadedFile.name}</span>
                  <button
                    type="button"
                    onClick={() => {
                      setUploadedFile(null)
                      setExtractedMetadata(null)
                    }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                {/* Initial Extraction Loading */}
                {isInitialExtracting && (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-3"></div>
                      <span className="text-sm text-gray-700">規則ベースでメタデータを抽出中...</span>
                    </div>
                  </div>
                )}
                
                {/* Extraction Results */}
                {extractedMetadata && !isInitialExtracting && (
                  <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="text-sm font-medium text-green-900">抽出完了</h4>
                        <p className="text-xs text-green-700">以下の情報を抽出しました。フォームに反映されています。</p>
                      </div>
                    </div>
                    
                    <div className="text-xs text-green-800 space-y-1">
                      {extractedMetadata.title && <div><strong>タイトル:</strong> {extractedMetadata.title}</div>}
                      {extractedMetadata.authors && extractedMetadata.authors.length > 0 && (
                        <div><strong>著者:</strong> {extractedMetadata.authors.join(', ')}</div>
                      )}
                      {extractedMetadata.year && <div><strong>発行年:</strong> {extractedMetadata.year}</div>}
                      {extractedMetadata.journal && <div><strong>ジャーナル:</strong> {extractedMetadata.journal}</div>}
                      {extractedMetadata.doi && <div><strong>DOI:</strong> {extractedMetadata.doi}</div>}
                    </div>
                    
                    <div className="mt-3 pt-3 border-t border-green-200 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-green-800">間違っていますか？</span>
                        <button
                          type="button"
                          onClick={handleLlmExtraction}
                          disabled={isExtracting}
                          className="btn btn-primary btn-sm"
                        >
                          {isExtracting ? (
                            <>
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                              LLM抽出中...
                            </>
                          ) : (
                            'LLM で抽出'
                          )}
                        </button>
                      </div>
                      
                      <label className="flex items-center text-sm text-green-800">
                        <input
                          type="checkbox"
                          checked={autoExtractCitations}
                          onChange={(e) => setAutoExtractCitations(e.target.checked)}
                          className="rounded mr-2"
                        />
                        <span>保存後に自動で引用を抽出する</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Basic Information */}
          <div className="card p-6 space-y-4">
            <h3 className="text-lg font-medium text-gray-900">基本情報</h3>
            
            <div>
              <label className="label">タイトル *</label>
              <input
                type="text"
                className="input"
                {...register('title', { required: 'タイトルは必須です' })}
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
              )}
            </div>

            <div>
              <label className="label">著者</label>
              {authorFields.map((field, index) => (
                <div key={field.id} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    placeholder="著者名"
                    className="input flex-1"
                    {...register(`authors.${index}.name`)}
                  />
                  {authorFields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeAuthor(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={() => appendAuthor({ name: '' })}
                className="flex items-center text-sm text-primary-600 hover:text-primary-700"
              >
                <Plus className="w-4 h-4 mr-1" />
                著者を追加
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">発行年</label>
                <input
                  type="number"
                  min="1900"
                  max="2030"
                  className="input"
                  {...register('year', { valueAsNumber: true })}
                />
              </div>
              <div>
                <label className="label">DOI</label>
                <input
                  type="text"
                  placeholder="10.1000/xyz123"
                  className="input"
                  {...register('doi')}
                />
              </div>
            </div>

            <div>
              <label className="label">ジャーナル・学会</label>
              <input
                type="text"
                className="input"
                {...register('journal')}
              />
            </div>
          </div>

          {/* Abstract and Tags */}
          <div className="card p-6 space-y-4">
            <h3 className="text-lg font-medium text-gray-900">詳細情報</h3>
            
            <div>
              <label className="label">アブストラクト</label>
              <textarea
                rows={6}
                className="input resize-none"
                {...register('abstract')}
              />
            </div>

            <div>
              <label className="label">タグ</label>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {tags.map((tag) => (
                  <label key={tag.id} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      value={tag.id}
                      checked={selectedTags.includes(tag.id)}
                      {...register('selectedTags')}
                      className="rounded"
                    />
                    <span
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs"
                      style={{ 
                        backgroundColor: tag.color + '20',
                        color: tag.color
                      }}
                    >
                      {tag.name}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="label">メモ</label>
              <textarea
                rows={4}
                placeholder="この論文についてのメモ..."
                className="input resize-none"
                {...register('notes')}
              />
            </div>
          </div>
        </div>

        {/* Submit Buttons */}
        <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200">
          <Link
            to={isEditing ? `/papers/${paperId}` : '/'}
            className="btn btn-outline btn-md"
          >
            キャンセル
          </Link>
          <button
            type="submit"
            disabled={!isValid || createPaperMutation.isPending || updatePaperMutation.isPending || uploadPaperMutation.isPending}
            className="btn btn-primary btn-md"
          >
            {(createPaperMutation.isPending || updatePaperMutation.isPending || uploadPaperMutation.isPending) ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {uploadPaperMutation.isPending ? 'アップロード中...' : '保存中...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                {isEditing ? '更新' : '作成'}
              </>
            )}
          </button>
        </div>
        </fieldset>
      </form>
    </div>
  )
}