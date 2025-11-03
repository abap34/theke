import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import PaperDetail from '@/pages/PaperDetail'
import TagManagement from '@/pages/TagManagement'
import CitationManagement from '@/pages/CitationManagement'
import Settings from '@/pages/Settings'
import Search from '@/pages/Search'
import PaperEdit from '@/pages/PaperEdit'
import PaperSearch from '@/pages/PaperSearch'
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
          <Route path="/search" element={<PaperSearch />} />
          <Route path="/tags" element={<TagManagement />} />
          <Route path="/citations" element={<CitationManagement />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
      <Toaster />
    </>
  )
}

export default App