import { cn } from '@/utils/cn'
import { formatDistanceToNow } from 'date-fns'
import { Bell, AlertTriangle, Server, Database, Cpu, HardDrive, X } from 'lucide-react'
import type { AdminNotification } from '@/types'

interface NotificationsPanelProps {
  notifications: AdminNotification[]
  loading?: boolean
  onMarkRead?: (id: string) => void
  onMarkAllRead?: () => void
}

const notificationIcons = {
  failed_indexing: AlertTriangle,
  system_error: AlertTriangle,
  model_offline: Cpu,
  database_issue: Database,
  storage_warning: HardDrive,
}

const severityColors = {
  info: 'text-blue-600 bg-blue-100 border-blue-200',
  warning: 'text-yellow-600 bg-yellow-100 border-yellow-200',
  critical: 'text-red-600 bg-red-100 border-red-200',
}

export function NotificationsPanel({ notifications, loading = false, onMarkRead, onMarkAllRead }: NotificationsPanelProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200 animate-pulse">
        <div className="p-4 border-b border-secondary-200">
          <div className="h-5 bg-secondary-200 rounded w-1/4" />
        </div>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="p-4 border-b border-secondary-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-secondary-200 rounded-lg" />
              <div className="flex-1">
                <div className="h-4 bg-secondary-200 rounded w-1/3 mb-1" />
                <div className="h-3 bg-secondary-200 rounded w-1/2" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  const unreadCount = notifications.filter(n => !n.is_read).length

  if (notifications.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200">
        <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-secondary-900">Notifications</h3>
          <Bell className="h-5 w-5 text-secondary-400" />
        </div>
        <div className="p-6 text-center text-secondary-500">
          <Bell className="h-10 w-10 mx-auto text-secondary-300 mb-2" />
          <p>No notifications</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-secondary-200 max-h-[400px] flex flex-col">
      <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-secondary-900">Notifications</h3>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs font-medium">
              {unreadCount} unread
            </span>
          )}
          {unreadCount > 0 && onMarkAllRead && (
            <button
              onClick={onMarkAllRead}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Mark all read
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto divide-y divide-secondary-200">
        {notifications.slice(0, 20).map((notification, index) => {
          const Icon = notificationIcons[notification.type] || Bell
          const severityClass = severityColors[notification.severity]
          
          return (
            <div key={index} className={cn('p-4 hover:bg-secondary-50 transition-colors', !notification.is_read && 'bg-blue-50/50')}>
              <div className="flex items-start gap-3">
                <div className={cn('p-2 rounded-lg flex-shrink-0', severityClass)}>
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-secondary-900">{notification.title}</p>
                    <span className="text-xs text-secondary-400 whitespace-nowrap">
                      {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-sm text-secondary-600 mt-1">{notification.message}</p>
                  {notification.organization_id && (
                    <p className="text-xs text-secondary-400 mt-1">Organization: {notification.organization_id.slice(0, 8)}...</p>
                  )}
                </div>
                {!notification.is_read && onMarkRead && (
                  <button
                    onClick={() => onMarkRead(notification.id)}
                    className="p-1.5 rounded hover:bg-secondary-100 transition-colors text-secondary-400 hover:text-secondary-600"
                    aria-label="Mark as read"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default NotificationsPanel