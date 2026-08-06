import { cn } from '@/utils/cn'
import { ChevronLeft, Sun, Moon, Monitor, Bell, Settings, LogOut, MoreVertical, Search } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useSettingsStore } from '@/stores/settingsStore'

interface ChatHeaderProps {
  title?: string
  subtitle?: string
  onToggleSidebar: () => void
  sidebarOpen: boolean
  showSearch?: boolean
  onSearchChange?: (query: string) => void
  searchQuery?: string
}

export function ChatHeader({
  title = 'AI Assistant',
  subtitle,
  onToggleSidebar,
  sidebarOpen,
  showSearch = true,
  onSearchChange,
  searchQuery = '',
}: ChatHeaderProps) {
  const { user, logout, hasRole } = useAuthStore()
  const { theme, toggleSidebar: toggleTheme } = useSettingsStore()

  const getThemeIcon = () => {
    if (theme === 'dark') return <Moon className="h-5 w-5" />
    if (theme === 'light') return <Sun className="h-5 w-5" />
    return <Monitor className="h-5 w-5" />
  }

  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-secondary-200">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        {/* Left side - Menu toggle and title */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors"
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-semibold text-secondary-900 truncate">{title}</h1>
            {subtitle && (
              <p className="text-xs text-secondary-500 truncate">{subtitle}</p>
            )}
          </div>
        </div>

        {/* Right side - Search, Theme, Notifications, User menu */}
        <div className="flex items-center gap-2 lg:gap-4">
          {/* Search */}
          {showSearch && (
            <div className="hidden sm:block relative w-64">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="search"
                placeholder="Search..."
                value=""
                onChange={() => {}}
                className="w-full pl-10 pr-4 py-2 text-sm bg-secondary-50 border border-secondary-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
          )}

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors"
            aria-label="Toggle theme"
            title="Toggle theme"
          >
            {(() => {
              if (theme === 'dark') return <Moon className="h-5 w-5" />
              if (theme === 'light') return <Sun className="h-5 w-5" />
              return <Monitor className="h-5 w-5" />
            })()}
          </button>

          {/* Notifications */}
          <button className="p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors relative" aria-label="Notifications">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.381C7.673 5.04 8 5.504 8 6v.381A6.002 6.002 0 004 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>

          {/* User Menu */}
          <div className="relative">
            <button
              className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-secondary-100 transition-colors"
              aria-label="User menu"
            >
              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                <span className="text-sm font-medium text-primary-700">
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
              <span className="hidden md:block text-sm font-medium text-secondary-700 truncate max-w-[120px]">
                {user?.username}
              </span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default ChatHeader