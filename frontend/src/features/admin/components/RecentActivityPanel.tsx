import { cn } from '@/utils/cn'
import { formatDistanceToNow } from 'date-fns'
import {
  FileText,
  LogIn,
  MessageSquare,
  AlertCircle,
  RotateCcw,
  Building2,
  UserPlus,
} from 'lucide-react'
import type { AdminActivity } from '@/types'

interface RecentActivityProps {
  activities: AdminActivity[]
  loading?: boolean
  onViewAll?: () => void
}

const activityIcons = {
  document_upload: FileText,
  login: LogIn,
  chat_session: MessageSquare,
  error: AlertCircle,
  reindex_job: RotateCcw,
  organization_created: Building2,
  user_created: UserPlus,
}

const activityColors = {
  document_upload: 'text-blue-600 bg-blue-100',
  login: 'text-green-600 bg-green-100',
  chat_session: 'text-purple-600 bg-purple-100',
  error: 'text-red-600 bg-red-100',
  reindex_job: 'text-orange-600 bg-orange-100',
  organization_created: 'text-indigo-600 bg-indigo-100',
  user_created: 'text-pink-600 bg-pink-100',
}

export function RecentActivityPanel({ activities, loading = false, onViewAll }: RecentActivityProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200 p-6 animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-5 bg-secondary-200 rounded w-1/4" />
          <div className="h-5 bg-secondary-200 rounded w-1/6" />
        </div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-3 bg-secondary-50 rounded-lg">
            <div className="w-10 h-10 bg-secondary-200 rounded-full" />
            <div className="flex-1">
              <div className="h-4 bg-secondary-200 rounded w-1/2 mb-1" />
              <div className="h-3 bg-secondary-200 rounded w-1/3" />
            </div>
            <div className="h-3 bg-secondary-200 rounded w-20" />
          </div>
        ))}
      </div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200 p-6">
        <h3 className="text-lg font-semibold text-secondary-900 mb-4">Recent Activity</h3>
        <div className="text-center py-8 text-secondary-500">
          <MessageSquare className="h-10 w-10 mx-auto text-secondary-300 mb-2" />
          <p>No recent activity</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-secondary-200">
      <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-secondary-900">Recent Activity</h3>
        {onViewAll && (
          <button onClick={onViewAll} className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            View all
          </button>
        )}
      </div>
      <div className="divide-y divide-secondary-200">
        {activities.slice(0, 10).map((activity, index) => {
          const Icon = activityIcons[activity.type] || FileText
          const colorClass = activityColors[activity.type] || 'text-secondary-600 bg-secondary-100'
          
          return (
            <div key={index} className="flex items-center gap-4 p-4 hover:bg-secondary-50 transition-colors">
              <div className={cn('p-2 rounded-lg flex-shrink-0', colorClass)}>
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-secondary-900">{activity.title}</p>
                <p className="text-sm text-secondary-500 truncate">{activity.description}</p>
                <p className="text-xs text-secondary-400 mt-1">
                  {activity.organization_name} • {activity.username || 'System'}
                </p>
              </div>
              <span className="text-xs text-secondary-400 whitespace-nowrap">
                {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default RecentActivityPanel