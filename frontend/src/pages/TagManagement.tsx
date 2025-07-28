import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Palette } from 'lucide-react'
import { tagsApi } from '@/services/api'
import { TagCreate, TagUpdate } from '@/types'
import { toast } from '@/components/ui/Toaster'

const PRESET_COLORS = [
  '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
]

export default function TagManagement() {
  const [isCreating, setIsCreating] = useState(false)
  const [editingTag, setEditingTag] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data: tags = [], isLoading } = useQuery({
    queryKey: ['tags'],
    queryFn: () => tagsApi.getAll(),
  })

  const createMutation = useMutation({
    mutationFn: (tag: TagCreate) => tagsApi.create(tag),
    onSuccess: () => {
      toast.success('作成完了', 'タグを作成しました')
      queryClient.invalidateQueries({ queryKey: ['tags'] })
      setIsCreating(false)
    },
    onError: () => {
      toast.error('エラー', 'タグの作成に失敗しました')
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number, data: TagUpdate }) => 
      tagsApi.update(id, data),
    onSuccess: () => {
      toast.success('更新完了', 'タグを更新しました')
      queryClient.invalidateQueries({ queryKey: ['tags'] })
      setEditingTag(null)
    },
    onError: () => {
      toast.error('エラー', 'タグの更新に失敗しました')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tagsApi.delete(id),
    onSuccess: () => {
      toast.success('削除完了', 'タグを削除しました')
      queryClient.invalidateQueries({ queryKey: ['tags'] })
    },
    onError: () => {
      toast.error('エラー', 'タグの削除に失敗しました')
    }
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">タグ管理</h1>
          <p className="text-gray-600">{tags.length}個のタグが作成されています</p>
        </div>
        
        <button
          onClick={() => setIsCreating(true)}
          className="btn btn-primary btn-md"
        >
          <Plus className="w-4 h-4 mr-2" />
          タグを作成
        </button>
      </div>

      {/* Create Form */}
      {isCreating && (
        <div className="card p-6 mb-8">
          <TagForm
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setIsCreating(false)}
            isLoading={createMutation.isPending}
          />
        </div>
      )}

      {/* Tags List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {tags.map((tag) => (
          <TagCard
            key={tag.id}
            tag={tag}
            isEditing={editingTag === tag.id}
            onEdit={() => setEditingTag(tag.id)}
            onCancelEdit={() => setEditingTag(null)}
            onUpdate={(data) => updateMutation.mutate({ id: tag.id, data })}
            onDelete={() => {
              if (window.confirm('このタグを削除しますか？')) {
                deleteMutation.mutate(tag.id)
              }
            }}
            isUpdating={updateMutation.isPending}
            isDeleting={deleteMutation.isPending}
          />
        ))}
      </div>

      {/* Empty State */}
      {tags.length === 0 && (
        <div className="text-center py-12">
          <Palette className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">タグがありません</h3>
          <p className="text-gray-600 mb-6">
            論文を分類するためのタグを作成しましょう
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="btn btn-primary btn-md"
          >
            <Plus className="w-4 h-4 mr-2" />
            最初のタグを作成
          </button>
        </div>
      )}
    </div>
  )
}

interface TagFormProps {
  initialData?: { name: string; color: string }
  onSubmit: (data: TagCreate | TagUpdate) => void
  onCancel: () => void
  isLoading: boolean
}

function TagForm({ initialData, onSubmit, onCancel, isLoading }: TagFormProps) {
  const [name, setName] = useState(initialData?.name || '')
  const [color, setColor] = useState(initialData?.color || PRESET_COLORS[0])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim()) {
      onSubmit({ name: name.trim(), color })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="label">タグ名</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input"
          placeholder="タグ名を入力..."
          required
        />
      </div>

      <div>
        <label className="label">色</label>
        <div className="flex flex-wrap gap-2">
          {PRESET_COLORS.map((presetColor) => (
            <button
              key={presetColor}
              type="button"
              onClick={() => setColor(presetColor)}
              className={`w-8 h-8 rounded-full border-2 ${
                color === presetColor ? 'border-gray-800' : 'border-gray-300'
              }`}
              style={{ backgroundColor: presetColor }}
            />
          ))}
        </div>
        <div className="mt-2">
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-16 h-8 rounded border border-gray-300"
          />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <button type="submit" disabled={!name.trim() || isLoading} className="btn btn-primary btn-sm">
          {isLoading ? '処理中...' : '保存'}
        </button>
        <button type="button" onClick={onCancel} className="btn btn-outline btn-sm">
          キャンセル
        </button>
      </div>

      {name.trim() && (
        <div className="mt-4">
          <p className="text-sm text-gray-600 mb-2">プレビュー:</p>
          <span
            className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
            style={{ backgroundColor: color + '20', color }}
          >
            {name}
          </span>
        </div>
      )}
    </form>
  )
}

interface TagCardProps {
  tag: any
  isEditing: boolean
  onEdit: () => void
  onCancelEdit: () => void
  onUpdate: (data: TagUpdate) => void
  onDelete: () => void
  isUpdating: boolean
  isDeleting: boolean
}

function TagCard({ 
  tag, 
  isEditing, 
  onEdit, 
  onCancelEdit, 
  onUpdate, 
  onDelete,
  isUpdating,
  isDeleting 
}: TagCardProps) {
  return (
    <div className="card card-hover p-5">
      {isEditing ? (
        <TagForm
          initialData={{ name: tag.name, color: tag.color }}
          onSubmit={onUpdate}
          onCancel={onCancelEdit}
          isLoading={isUpdating}
        />
      ) : (
        <div>
          <div className="flex items-center justify-between mb-3">
            <span
              className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
              style={{ backgroundColor: tag.color + '20', color: tag.color }}
            >
              {tag.name}
            </span>
            
            <div className="flex items-center space-x-1">
              <button
                onClick={onEdit}
                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="編集"
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={onDelete}
                disabled={isDeleting}
                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="削除"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="text-sm text-gray-600">
            <p>作成日: {new Date(tag.created_at).toLocaleDateString()}</p>
            {/* TODO: Add paper count */}
            {/* <p>使用論文: {tag.paperCount}件</p> */}
          </div>
        </div>
      )}
    </div>
  )
}