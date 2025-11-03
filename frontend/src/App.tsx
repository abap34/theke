import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import PaperDetail from '@/pages/PaperDetail'
import TagManagement from '@/pages/TagManagement'
import Settings from '@/pages/Settings'
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
          <Route path="/tags" element={<TagManagement />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
      <Toaster />
    </>
  )
}

export default App