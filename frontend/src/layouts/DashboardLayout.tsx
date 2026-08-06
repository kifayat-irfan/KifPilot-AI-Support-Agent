import { ReactNode, useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useOrganizationStore } from '@/stores/organizationStore'
import {
  LayoutDashboard,
  MessageSquare,
  Database,
  FileText,
  Users,
  Settings,
  Building2,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  Bell,
  Sun,
  Moon,
  Monitor,
  Search,
} from 'lucide-react'
import { cn } from '@/utils/cn'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Knowledge Base', href: '/knowledge-base', icon: Database },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Organizations', href: '/organizations', icon: Building2 },
  { name: 'Users', href: '/users', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed)
  const location = useLocation()
  const { user, logout, currentOrganization, hasRole } = useAuthStore()

  const handleLogout = async () => {
    await logout()
  }

  const toggleTheme = () => {
    const { theme, setTheme } = useSettingsStore.getState()
    const themes: ('light' | 'dark' | 'system')[] = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }

  const getThemeIcon = () => {
    const { theme } = useSettingsStore.getState()
    if (theme === 'dark') return <Moon className="h-5 w-5" />
    if (theme === 'light') return <Sun className="h-5 w-5" />
    return <Monitor className="h-5 w-5" />
  }

  return (
    <div className="min-h-screen bg-secondary-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 bg-white border-r border-secondary-200 transition-all duration-300 ease-in-out flex flex-col',
          sidebarCollapsed ? 'w-16' : 'w-64',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className={cn('flex items-center h-16 px-4 border-b border-secondary-200', sidebarCollapsed && 'justify-center')}>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">K</span>
            </div>
            {!sidebarCollapsed && (
              <span className="font-semibold text-lg text-secondary-900">KifPilot</span>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Main">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/')
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900',
                  sidebarCollapsed && 'justify-center'
                )}
                title={sidebarCollapsed ? item.name : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Organization selector */}
        {!sidebarCollapsed && currentOrganization && (
          <div className="p-3 border-t border-secondary-200">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-primary-50 rounded-lg">
              <Building2 className="h-4 w-4 text-primary-600" aria-hidden="true" />
              <span className="text-sm font-medium text-primary-700 truncate">{currentOrganization.name}</span>
            </div>
          </div>
        )}

        {/* User menu */}
        <div className={cn('p-3 border-t border-secondary-200', sidebarCollapsed && 'px-2')}>
          {user && (
            <div className="flex items-center gap-3">
              <div className={cn('w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0', sidebarCollapsed && 'mx-auto')}>
                <span className="text-sm font-medium text-primary-700">
                  {user.username.charAt(0).toUpperCase()}
                </span>
              </div>
              {!sidebarCollapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-secondary-900 truncate">{user.username}</p>
                  <p className="text-xs text-secondary-500 truncate">{user.email}</p>
                </div>
              )}
            </div>
          )}
          <div className="flex items-center gap-1 mt-3">
            <button
              onClick={toggleTheme}
              className={cn(
                'p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors',
                sidebarCollapsed && 'mx-auto'
              )}
              aria-label="Toggle theme"
              title={sidebarCollapsed ? 'Toggle theme' : undefined}
            >
              {getThemeIcon()}
            </button>
            <button
              onClick={handleLogout}
              className={cn(
                'p-2 rounded-lg text-secondary-500 hover:text-red-600 hover:bg-red-50 transition-colors',
                sidebarCollapsed && 'mx-auto'
              )}
              aria-label="Logout"
              title={sidebarCollapsed ? 'Logout' : undefined}
            >
              <LogOut className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className={cn('flex-1 flex flex-col min-w-0 lg:ml-0', sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64')}>
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-secondary-200">
          <div className="flex items-center justify-between h-16 px-4 lg:px-6">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100"
              aria-label="Open menu"
            >
              <Menu className="h-6 w-6" aria-hidden="true" />
            </button>

            <div className="flex-1 lg:flex lg:items-center lg:justify-end gap-4">
              {/* Search */}
              <div className="hidden lg:block w-72">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-secondary-400" aria-hidden="true" />
                  <input
                    type="search"
                    placeholder="Search..."
                    className="w-full pl-10 pr-4 py-2 text-sm bg-secondary-50 border border-secondary-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    aria-label="Search"
                  />
                </div>
              </div>

              {/* Notifications */}
              <button className="p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 relative" aria-label="Notifications">
                <Bell className="h-5 w-5" aria-hidden="true" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}