import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  BookOpen, 
  Tag, 
  Quote, 
  Network, 
  Search, 
  Settings, 
  Menu,
  X,
  Plus
} from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: BookOpen },
  { name: 'Network', href: '/network', icon: Network },
  { name: 'Tags', href: '/tags', icon: Tag },
  { name: 'Citations', href: '/citations', icon: Quote },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const isDashboard = location.pathname === '/'
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isHovering, setIsHovering] = useState(false)

  const shouldShowSidebar = isDashboard || sidebarOpen || isHovering

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left hover trigger for non-dashboard pages */}
      {!isDashboard && (
        <div 
          className="fixed inset-y-0 left-0 z-30 w-4 bg-transparent"
          onMouseEnter={() => setIsHovering(true)}
        />
      )}

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div 
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform
          ${shouldShowSidebar ? 'translate-x-0' : '-translate-x-full'}
          ${isDashboard ? 'lg:translate-x-0 lg:static lg:inset-0' : 'lg:fixed lg:inset-y-0'}
          transition-transform duration-200 ease-in-out
        `}
        onMouseLeave={() => setIsHovering(false)}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <Link to="/" className="flex items-center space-x-2">
            <BookOpen className="w-8 h-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">Theke</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`
                  flex items-center px-3 py-3 text-sm font-medium rounded-lg transition-colors
                  ${isActive 
                    ? 'bg-primary-50 text-primary-700' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }
                `}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="w-5 h-5 mr-3" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main content area */}
      <div className={`flex-1 flex flex-col min-w-0 ${isDashboard ? '' : 'lg:ml-0'}`}>
        {/* Top bar */}
        {/* Page content */}
        <main className="flex-1 overflow-auto p-4">
          {children}
        </main>
      </div>
    </div>
  )
}