import { SessionList } from './SessionList'
import { cn } from '@/utils/cn'
import { Building2, ChevronLeft, Plus } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useOrganizationStore } from '@/stores/organizationStore'

interface ConversationSidebarProps {
  isOpen: boolean
  onClose: () => void
  sessions: Array<{
    id: string
    title: string | null
    message_count: number
    last_activity: string
    created_at: string
    updated_at: string
  }>
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onCreateSession: () => void
  onDeleteSession: (sessionId: string, e: React.MouseEvent) => void
  onRenameSession: (sessionId: string, newTitle: string) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

export function ConversationSidebar({
  isOpen,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  searchQuery,
  onSearchChange,
}: ConversationSidebarProps) {
  const { currentOrganization } = useOrganizationStore()
  const { hasRole } = useAuthStore()
  const isAdmin = hasRole('admin')

  if (!isOpen) return null

  return (
    <>
      {/* Mobile overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/50 lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 bg-white border-r border-secondary-200 transition-all duration-300 ease-in-out flex flex-col',
          'w-80',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Conversation history"
      >
        {/* Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-secondary-200">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary-600" aria-hidden="true" />
            <h2 className="font-semibold text-lg text-secondary-900">Conversations</h2>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors"
            aria-label="Close sidebar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Organization selector */}
        {currentOrganization && (
          <div className="px-4 py-3 border-b border-secondary-200">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-primary-50 rounded-lg">
              <Building2 className="h-4 w-4 text-primary-600" aria-hidden="true" />
              <span className="text-sm font-medium text-primary-700 truncate">{currentOrganization.name}</span>
            </div>
          </div>
        )}

        {/* Session List */}
        <SessionList
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={onSelectSession}
          onCreateSession={onCreateSession}
          onDeleteSession={onDeleteSession}
          onRenameSession={onRenameSession}
          searchQuery=""
          onSearchChange={() => {}}
        />
      </aside>
    </>
  )
}

export default ConversationSidebar