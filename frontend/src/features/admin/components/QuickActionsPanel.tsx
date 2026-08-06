import { cn } from '@/utils/cn'
import {
  Upload,
  Building2,
  UserPlus,
  Database,
  MessageSquare,
  FileText,
  ExternalLink,
} from 'lucide-react'
import type { QuickAction } from '@/types'

interface QuickActionsPanelProps {
  actions?: QuickAction[]
  loading?: boolean
}

const defaultActions: QuickAction[] = [
  {
    id: 'upload-document',
    label: 'Upload Document',
    description: 'Add new documents to the knowledge base',
    icon: 'upload',
    href: '/documents',
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'create-org',
    label: 'Create Organization',
    description: 'Set up a new organization',
    icon: 'building',
    href: '/organizations',
    color: 'bg-green-100 text-green-600',
  },
  {
    id: 'invite-user',
    label: 'Invite User',
    description: 'Add a new team member',
    icon: 'user-plus',
    href: '/users',
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'knowledge-base',
    label: 'Open Knowledge Base',
    description: 'Search and browse documentation',
    icon: 'database',
    href: '/knowledge-base',
    color: 'bg-orange-100 text-orange-600',
  },
  {
    id: 'chat',
    label: 'Start Chat',
    description: 'Open AI chat interface',
    icon: 'message-square',
    href: '/chat',
    color: 'bg-pink-100 text-pink-600',
  },
  {
    id: 'documents',
    label: 'Manage Documents',
    description: 'View and organize documents',
    icon: 'file-text',
    href: '/documents',
    color: 'bg-indigo-100 text-indigo-600',
  },
]

const actionIcons = {
  upload: Upload,
  building: Building2,
  'user-plus': UserPlus,
  database: Database,
  'message-square': MessageSquare,
  'file-text': FileText,
}

export function QuickActionsPanel({ actions = defaultActions, loading = false }: QuickActionsPanelProps) {
  const ActionIcon = ({ name, color }: { name: keyof typeof actionIcons; color: string }) => {
    const Icon = actionIcons[name] || FileText
    return <Icon className={cn('h-5 w-5', color)} aria-hidden="true" />
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200 p-6 animate-pulse">
        <div className="h-5 bg-secondary-200 rounded w-1/4 mb-4" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-4 border border-secondary-200 rounded-lg">
              <div className="h-10 w-10 bg-secondary-200 rounded-lg mb-2" />
              <div className="h-4 bg-secondary-200 rounded w-3/4 mb-1" />
              <div className="h-3 bg-secondary-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-secondary-200 p-6">
      <h3 className="text-lg font-semibold text-secondary-900 mb-4">Quick Actions</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {actions.map((action) => {
          const Icon = actionIcons[action.icon as keyof typeof actionIcons] || FileText
          return (
            <a
              key={action.id}
              href={action.href}
              className="flex items-center gap-3 p-4 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-colors group"
            >
              <div className={cn('p-2 rounded-lg flex-shrink-0', action.color)}>
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-secondary-900 group-hover:text-primary-600 transition-colors">{action.label}</p>
                <p className="text-sm text-secondary-500">{action.description}</p>
              </div>
              <ExternalLink className="h-4 w-4 text-secondary-400 group-hover:text-primary-600 transition-colors" aria-hidden="true" />
            </a>
          )
        })}
      </div>
    </div>
  )
}

export default QuickActionsPanel