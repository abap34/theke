import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import PaperDetail from '@/pages/PaperDetail'
import NetworkGraph from '@/pages/NetworkGraph'
import TagManagement from '@/pages/TagManagement'
import CitationManagement from '@/pages/CitationManagement'
import Settings from '@/pages/Settings'
import Search from '@/pages/Search'
import PaperEdit from '@/pages/PaperEdit'
import { Toaster } from '@/components/ui/Toaster'

function App() {
  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/papers/:id" element={<PaperDetail />} />
          <Route path="/papers/:id/edit" element={<PaperEdit />} />
          <Route path="/papers/new" element={<PaperEdit />} />
          <Route path="/network" element={<NetworkGraph />} />
          <Route path="/tags" element={<TagManagement />} />
          <Route path="/citations" element={<CitationManagement />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/search" element={<Search />} />
        </Routes>
      </Layout>
      <Toaster />
    </>
  )
}

export default App