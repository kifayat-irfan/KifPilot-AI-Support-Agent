import { useState } from 'react'
import { cn } from '@/utils/cn'
import { ChevronRight, ChevronDown, Trash2, Edit2, Plus, Search, MessageSquare, X, MoreVertical } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { format } from 'date-fns'

interface SessionListProps {
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

export function SessionList({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  searchQuery,
  onSearchChange,
}: SessionListProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [showMenuId, setShowMenuId] = useState<string | null>(null)

  const filteredSessions = sessions.filter((session) =>
    (session.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const startEditing = (sessionId: string, currentTitle: string | null) => {
    setEditingId(sessionId)
    setEditTitle(currentTitle || '')
  }

  const saveEditing = (sessionId: string) => {
    if (editTitle.trim()) {
      onRenameSession(sessionId, editTitle.trim())
    }
    setEditingId(null)
    setEditTitle('')
  }

  const handleKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      saveEditing(sessionId)
    } else if (e.key === 'Escape') {
      setEditingId(null)
      setEditTitle('')
    }
  }

  const formatSessionTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = diffMs / (1000 * 60 * 60)
    const diffDays = diffHours / 24

    if (diffHours < 1) {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } else if (diffDays < 7) {
      return format(new Date(dateString), 'EEE')
    } else {
      return format(new Date(dateString), 'MMM d')
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-r border-secondary-200">
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-secondary-200">
        <div className="flex items-center gap-2">
          <button
            onClick={onCreateSession}
            className="p-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors"
            aria-label="New chat"
          >
            <Plus className="w-5 h-5" />
          </button>
          <h2 className="text-lg font-semibold text-secondary-900">Chats</h2>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-secondary-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-400" aria-hidden="true" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-secondary-50 border border-secondary-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {filteredSessions.length === 0 ? (
          <div className="p-8 text-center">
            {searchQuery ? (
              <p className="text-secondary-500">No conversations match your search</p>
            ) : (
              <p className="text-secondary-500">No conversations yet</p>
            )}
          </div>
        ) : (
          <>
            <ul className="divide-y divide-secondary-100" role="list">
              {filteredSessions.map((session) => (
                <li key={session.id} className="relative group">
                  <button
                    onClick={() => onSelectSession(session.id)}
                    className={`w-full px-4 py-3 text-left transition-colors ${
                      activeSessionId === session.id
                        ? 'bg-primary-50 border-l-4 border-primary-500'
                        : 'hover:bg-secondary-50'
                    }`}
                    aria-current={activeSessionId === session.id ? 'true' : 'false'}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className={`truncate font-medium ${activeSessionId === session.id ? 'text-primary-700' : 'text-secondary-900'}`}>
                          {session.title || 'New conversation'}
                        </p>
                        <p className="text-xs text-secondary-500 mt-1 truncate">
                          {session.message_count} messages
                        </p>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setShowMenuId(showMenuId === session.id ? null : session.id)
                          }}
                          className="p-1.5 rounded hover:bg-secondary-100 text-secondary-400 hover:text-secondary-600"
                          aria-label="More options"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </button>

                    {/* Menu Dropdown */}
                    {showMenuId === session.id && (
                      <div className="relative">
                        <div
                          className="fixed inset-0 z-40"
                          onClick={() => setShowMenuId(null)}
                          aria-hidden="true"
                        />
                        <div className="absolute right-2 top-10 z-50 w-40 bg-white rounded-lg shadow-lg border border-secondary-200 py-1 animate-slide-down">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              startEditing(session.id, session.title)
                            }}
                            className="w-full px-4 py-2 text-left text-sm text-secondary-700 hover:bg-secondary-50 flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Rename
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteSession(session.id, e)
                            }}
                            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  <div className="text-right text-xs text-secondary-400 pr-2 pt-1">
                    {formatDistanceToNow(new Date(session.last_activity || session.updated_at), { addSuffix: true })}
                  </div>
                </li>
              ))}
            </ul>

            {/* Inline Editor */}
            {editingId && (
              <li className="px-2 py-1">
                <div className="flex gap-1">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, editingId!)}
                    onBlur={() => saveEditing(editingId!)}
                    autoFocus
                    className="flex-1 px-2 py-1.5 text-sm border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="Conversation title"
                  />
                  <button
                    onClick={() => saveEditing(editingId!)}
                    className="p-1.5 rounded text-primary-600 hover:bg-primary-50"
                    aria-label="Save"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="p-1.5 rounded text-secondary-400 hover:text-secondary-600"
                    aria-label="Cancel"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </li>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default SessionList