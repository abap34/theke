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
  Panel,
  Handle,
  Position
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
function PaperNode({ data, id }: { data: any, id: string }) {
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
    } else {
      // This is a resolved paper - open Google search in new tab
      const searchQuery = encodeURIComponent(`"${data.title}" ${data.authors?.join(' ') || ''}`)
      window.open(`https://www.google.com/search?q=${searchQuery}`, '_blank')
    }
  }

  // Determine opacity based on focus state
  const getOpacity = () => {
    if (!data.focusedNodeId) {
      // No focus - show resolved papers normally, unresolved very faded
      return data.resolved ? 1 : 0.15
    }
    
    if (data.focusedNodeId === id) {
      // This is the focused node
      return 1
    }
    
    if (data.connectedNodeIds?.has(id)) {
      // This node is connected to the focused node - make it fully visible
      return 1
    }
    
    // This node is not connected to the focused node - make it very faded
    return 0.1
  }

  return (
    <div 
      className={`
        px-4 py-3 rounded-lg border-2 cursor-pointer transition-all duration-300
        ${data.resolved 
          ? 'bg-white border-primary-300 hover:border-primary-500 shadow-md' 
          : 'bg-gray-100 border-gray-300 hover:border-gray-500 border-dashed'
        }
        max-w-sm min-w-48
      `}
      style={{ opacity: getOpacity() }}
      onClick={handleNodeClick}
    >
      {/* Source handle (right side) for outgoing edges */}
      <Handle
        type="source"
        position={Position.Right}
        id="source"
        style={{ 
          background: '#6366f1', 
          width: 6, 
          height: 6,
          border: '2px solid #fff',
          boxShadow: '0 0 0 1px #6366f1'
        }}
      />
      
      {/* Target handle (left side) for incoming edges */}
      <Handle
        type="target"
        position={Position.Left}
        id="target"
        style={{ 
          background: '#6366f1', 
          width: 6, 
          height: 6,
          border: '2px solid #fff',
          boxShadow: '0 0 0 1px #6366f1'
        }}
      />

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
  const [layoutMode, setLayoutMode] = useState<'force' | 'hierarchical' | 'circular' | 'tree'>('force')
  const [showUnresolved, setShowUnresolved] = useState(true)
  const [selectedYearRange, setSelectedYearRange] = useState<[number, number] | null>(null)
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)
  const [connectedNodeIds, setConnectedNodeIds] = useState<Set<string>>(new Set())

  const { data: networkData, isLoading, refetch } = useQuery({
    queryKey: ['citation-network'],
    queryFn: () => citationsApi.getNetwork(),
  })

  // Handle node focus to highlight connections
  const handleNodeFocus = useCallback((nodeId: string) => {
    if (focusedNodeId === nodeId) {
      // Clicking the same node unfocuses
      setFocusedNodeId(null)
      setConnectedNodeIds(new Set())
    } else {
      setFocusedNodeId(nodeId)
      
      // Find all connected nodes
      const connected = new Set<string>()
      if (networkData) {
        networkData.edges.forEach(edge => {
          if (edge.source === nodeId) {
            connected.add(edge.target)
          } else if (edge.target === nodeId) {
            connected.add(edge.source)
          }
        })
      }
      setConnectedNodeIds(connected)
    }
  }, [focusedNodeId, networkData])

  // Convert backend data to ReactFlow format
  useEffect(() => {
    if (networkData) {
      const flowNodes: Node[] = networkData.nodes
        .filter(node => showUnresolved || node.resolved)
        .map((node, index) => ({
          id: node.id,
          type: 'paper',
          position: generatePosition(index, networkData.nodes.length, layoutMode, node, networkData.nodes, networkData.edges),
          data: {
            title: node.label,
            resolved: node.resolved,
            focusedNodeId,
            connectedNodeIds,
            onNodeFocus: handleNodeFocus,
            ...node.data
          },
          draggable: node.resolved,
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
          sourceHandle: 'source',
          targetHandle: 'target',
          type: 'smoothstep',
          animated: false,
          style: { 
            stroke: '#6366f1', 
            strokeWidth: 1.5,
            strokeOpacity: getEdgeOpacity(edge.source, edge.target)
          },
          markerEnd: {
            type: 'arrowclosed',
            color: '#6366f1',
            width: 12,
            height: 12
          },
        }))

      setNodes(flowNodes)
      setEdges(flowEdges)
    }
  }, [networkData, layoutMode, showUnresolved, focusedNodeId, connectedNodeIds, setNodes, setEdges, handleNodeFocus])

  // Function to determine edge opacity based on focus state
  const getEdgeOpacity = useCallback((sourceId: string, targetId: string) => {
    if (!focusedNodeId) {
      return 0.3 // Default low opacity for all edges
    }
    
    if (focusedNodeId === sourceId || focusedNodeId === targetId) {
      return 1 // High opacity for edges connected to focused node
    }
    
    return 0.05 // Very low opacity for unrelated edges
  }, [focusedNodeId, connectedNodeIds])

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  // Generate positions based on layout mode
  function generatePosition(index: number, total: number, mode: string, node?: any, allNodes?: any[], edges?: any[]) {
    const centerX = 600
    const centerY = 400
    const radius = Math.min(400 + total * 25, 1200)

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
          x: (posInLevel - levels / 2) * 400 + centerX,
          y: level * 300 + 100
        }
      
      case 'tree':
        return generateTreePosition(node, allNodes || [], edges || [])
      
      default: // force/random
        return {
          x: Math.random() * 1600 + 200,
          y: Math.random() * 1200 + 200
        }
    }
  }

  // Tree layout algorithm with resolved papers as roots
  function generateTreePosition(node: any, allNodes: any[], edges: any[]) {
    const treeData = buildTreeStructure(allNodes, edges)
    const position = treeData.positions.get(node.id)
    
    if (position) {
      return position
    }
    
    // Fallback for nodes not in tree
    return {
      x: Math.random() * 200 + 1000,
      y: Math.random() * 200 + 600
    }
  }

  // Build tree structure with resolved papers as roots
  function buildTreeStructure(nodes: any[], edges: any[]) {
    const positions = new Map<string, {x: number, y: number}>()
    const visited = new Set<string>()
    const levelWidth = 450
    const levelHeight = 200
    
    // Find resolved papers (potential roots)
    const resolvedNodes = nodes.filter(node => node.resolved)
    const unresolvedNodes = nodes.filter(node => !node.resolved)
    
    // Build adjacency list
    const adjacencyList = new Map<string, string[]>()
    edges.forEach(edge => {
      if (!adjacencyList.has(edge.source)) {
        adjacencyList.set(edge.source, [])
      }
      adjacencyList.get(edge.source)!.push(edge.target)
    })
    
    let currentRootX = 200
    const rootY = 100
    
    // Process each resolved paper as a potential root
    resolvedNodes.forEach((rootNode, rootIndex) => {
      if (visited.has(rootNode.id)) return
      
      // Position the root
      positions.set(rootNode.id, { x: currentRootX, y: rootY })
      visited.add(rootNode.id)
      
      // BFS to position children
      const queue: Array<{nodeId: string, level: number, indexInLevel: number}> = []
      const children = adjacencyList.get(rootNode.id) || []
      
      children.forEach((childId, index) => {
        queue.push({ nodeId: childId, level: 1, indexInLevel: index })
      })
      
      const levelCounts = new Map<number, number>()
      
      while (queue.length > 0) {
        const { nodeId, level, indexInLevel } = queue.shift()!
        
        if (visited.has(nodeId)) continue
        visited.add(nodeId)
        
        // Count nodes at this level
        const nodesAtLevel = levelCounts.get(level) || 0
        levelCounts.set(level, nodesAtLevel + 1)
        
        // Position the node
        const levelNodes = queue.filter(q => q.level === level).length + 1
        const startX = currentRootX - (levelNodes - 1) * levelWidth / 2
        const x = startX + indexInLevel * levelWidth
        const y = rootY + level * levelHeight
        
        positions.set(nodeId, { x, y })
        
        // Add children to queue
        const nodeChildren = adjacencyList.get(nodeId) || []
        nodeChildren.forEach((childId, childIndex) => {
          queue.push({ nodeId: childId, level: level + 1, indexInLevel: childIndex })
        })
      }
      
      // Move to next root position
      currentRootX += Math.max(600, (levelCounts.get(1) || 1) * levelWidth + 150)
    })
    
    // Position any remaining unvisited nodes (disconnected components)
    let disconnectedX = currentRootX
    let disconnectedY = rootY
    
    nodes.forEach(node => {
      if (!visited.has(node.id)) {
        positions.set(node.id, { x: disconnectedX, y: disconnectedY })
        disconnectedX += 300
        if (disconnectedX > 1800) {
          disconnectedX = currentRootX
          disconnectedY += 200
        }
      }
    })
    
    return { positions }
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
            <h1 className="text-2xl font-bold text-gray-900">Network</h1>
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
                <option value="tree">ツリー</option>
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