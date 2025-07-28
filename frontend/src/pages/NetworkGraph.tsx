import { useState, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, { 
  Node, 
  Edge, 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  NodeTypes,
  EdgeTypes,
  Panel
} from 'reactflow'
import 'reactflow/dist/style.css'
import { 
  Search, 
  Settings, 
  Download, 
  Maximize2,
  Filter,
  RefreshCw
} from 'lucide-react'
import { citationsApi, externalApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'

// Custom node component for papers
function PaperNode({ data }: { data: any }) {
  const [showSuggestions, setShowSuggestions] = useState(false)

  const handleNodeClick = async () => {
    if (!data.resolved) {
      // This is an unresolved citation - show search suggestions
      setShowSuggestions(true)
      try {
        const suggestions = await externalApi.searchAll(data.title, 3, ['arxiv', 'crossref', 'semantic_scholar'])
        // Handle suggestions...
        toast.info('論文検索', `${data.title}の候補を検索中...`)
      } catch (error) {
        toast.error('エラー', '論文の検索に失敗しました')
      }
    }
  }

  return (
    <div 
      className={`
        px-4 py-3 rounded-lg border-2 cursor-pointer transition-all
        ${data.resolved 
          ? 'bg-white border-primary-300 hover:border-primary-500 shadow-md' 
          : 'bg-gray-100 border-gray-300 hover:border-gray-500 border-dashed'
        }
        max-w-xs
      `}
      onClick={handleNodeClick}
    >
      <div className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
        {data.title}
      </div>
      {data.authors && (
        <div className="text-xs text-gray-600 line-clamp-1">
          {data.authors.slice(0, 2).join(', ')}
          {data.authors.length > 2 && ` +${data.authors.length - 2}`}
        </div>
      )}
      {data.year && (
        <div className="text-xs text-gray-500 mt-1">{data.year}</div>
      )}
      {!data.resolved && (
        <div className="text-xs text-orange-600 mt-1 font-medium">
          クリックして検索
        </div>
      )}
    </div>
  )
}

const nodeTypes: NodeTypes = {
  paper: PaperNode,
}

export default function NetworkGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [layoutMode, setLayoutMode] = useState<'force' | 'hierarchical' | 'circular'>('force')
  const [showUnresolved, setShowUnresolved] = useState(true)
  const [selectedYearRange, setSelectedYearRange] = useState<[number, number] | null>(null)

  const { data: networkData, isLoading, refetch } = useQuery({
    queryKey: ['citation-network'],
    queryFn: () => citationsApi.getNetwork(),
  })

  // Convert backend data to ReactFlow format
  useEffect(() => {
    if (networkData) {
      const flowNodes: Node[] = networkData.nodes
        .filter(node => showUnresolved || node.resolved)
        .map((node, index) => ({
          id: node.id,
          type: 'paper',
          position: generatePosition(index, networkData.nodes.length, layoutMode),
          data: {
            title: node.label,
            resolved: node.resolved,
            ...node.data
          },
          draggable: true,
        }))

      const flowEdges: Edge[] = networkData.edges
        .filter(edge => {
          // Only show edges where both nodes are visible
          const sourceVisible = flowNodes.some(n => n.id === edge.source)
          const targetVisible = flowNodes.some(n => n.id === edge.target)
          return sourceVisible && targetVisible
        })
        .map(edge => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: {
            type: 'arrowclosed',
            color: '#6366f1',
          },
        }))

      setNodes(flowNodes)
      setEdges(flowEdges)
    }
  }, [networkData, layoutMode, showUnresolved, setNodes, setEdges])

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  // Generate positions based on layout mode
  function generatePosition(index: number, total: number, mode: string) {
    const centerX = 400
    const centerY = 300
    const radius = Math.min(200 + total * 10, 500)

    switch (mode) {
      case 'circular':
        const angle = (index / total) * 2 * Math.PI
        return {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle)
        }
      
      case 'hierarchical':
        const levels = Math.ceil(Math.sqrt(total))
        const level = Math.floor(index / levels)
        const posInLevel = index % levels
        return {
          x: (posInLevel - levels / 2) * 200 + centerX,
          y: level * 150 + 100
        }
      
      default: // force/random
        return {
          x: Math.random() * 800 + 100,
          y: Math.random() * 600 + 100
        }
    }
  }

  const handleExportImage = () => {
    // Implementation for exporting the graph as image
    toast.info('エクスポート', 'グラフの画像エクスポート機能は開発中です')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">ネットワークを読み込み中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">引用ネットワーク</h1>
            <p className="text-gray-600">
              {nodes.length}件の論文、{edges.length}件の引用関係
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Layout Controls */}
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-700">レイアウト:</label>
              <select
                value={layoutMode}
                onChange={(e) => setLayoutMode(e.target.value as any)}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="force">Force-directed</option>
                <option value="hierarchical">階層</option>
                <option value="circular">円形</option>
              </select>
            </div>

            {/* Show unresolved toggle */}
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={showUnresolved}
                onChange={(e) => setShowUnresolved(e.target.checked)}
                className="rounded"
              />
              <span>未解決の引用を表示</span>
            </label>

            <button
              onClick={() => refetch()}
              className="btn btn-outline btn-sm"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              更新
            </button>

            <button
              onClick={handleExportImage}
              className="btn btn-outline btn-sm"
            >
              <Download className="w-4 h-4 mr-2" />
              画像出力
            </button>
          </div>
        </div>
      </div>

      {/* Network Graph */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
          <MiniMap 
            nodeColor={(node) => node.data.resolved ? '#3b82f6' : '#9ca3af'}
            nodeStrokeWidth={2}
            className="bg-white"
          />
          
          {/* Info Panel */}
          <Panel position="top-right">
            <div className="bg-white rounded-lg shadow-lg p-4 max-w-sm">
              <h3 className="font-medium text-gray-900 mb-2">操作方法</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• ドラッグしてノードを移動</li>
                <li>• マウスホイールでズーム</li>
                <li>• 灰色のノードをクリックして論文を検索</li>
                <li>• 青色のノードをクリックして詳細表示</li>
              </ul>
            </div>
          </Panel>

          {/* Empty State */}
          {nodes.length === 0 && (
            <Panel position="center">
              <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                <div className="text-gray-400 mb-4">
                  <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} 
                          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  引用ネットワークがありません
                </h3>
                <p className="text-gray-600 mb-4">
                  論文の引用情報を抽出して、関係性を可視化しましょう
                </p>
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>
    </div>
  )
}