import { cn } from '@/utils/cn'
import {
  Building2,
  Users,
  FileText,
  CheckCircle,
  MessageSquare,
  Database,
  HardDrive,
  Clock,
  TrendingUp,
} from 'lucide-react'
import type { AdminStats } from '@/types'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  color: string
  bg: string
  trend?: { value: string; label: string }
  onClick?: () => void
}

function StatCard({ title, value, icon, color, bg, trend, onClick }: StatCardProps) {
  return (
    <div
      className={cn(
        'p-6 rounded-xl border transition-all hover:shadow-md',
        onClick && 'cursor-pointer'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-secondary-600 mb-1">{title}</p>
          <p className="text-3xl font-bold text-secondary-900">{value}</p>
          {trend && (
            <p className="mt-1 text-xs text-secondary-500 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-600" aria-hidden="true" />
              <span className="text-green-600">{trend.value}</span>
              <span>{trend.label}</span>
            </p>
          )}
        </div>
        <div className={cn('p-3 rounded-xl', bg)}>
          <div className={cn('h-6 w-6', color)}>
            {icon}
          </div>
        </div>
      </div>
    </div>
  )
}

export function OverviewCards({ stats, loading = false }: { stats: AdminStats; loading?: boolean }) {
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toLocaleString()
  }

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="p-6 rounded-xl border animate-pulse">
            <div className="h-4 bg-secondary-200 rounded w-3/4 mb-2" />
            <div className="h-8 bg-secondary-200 rounded w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
      <StatCard
        title="Total Organizations"
        value={formatNumber(stats.total_organizations)}
        icon={<Building2 className="h-6 w-6" />}
        color="text-blue-600"
        bg="bg-blue-100"
      />
      <StatCard
        title="Total Users"
        value={formatNumber(stats.total_users)}
        icon={<Users className="h-6 w-6" />}
        color="text-green-600"
        bg="bg-green-100"
      />
      <StatCard
        title="Total Documents"
        value={formatNumber(stats.total_documents)}
        icon={<FileText className="h-6 w-6" />}
        color="text-purple-600"
        bg="bg-purple-100"
      />
      <StatCard
        title="Indexed Documents"
        value={formatNumber(stats.indexed_documents)}
        icon={<CheckCircle className="h-6 w-6" />}
        color="text-teal-600"
        bg="bg-teal-100"
      />
      <StatCard
        title="Chat Sessions"
        value={formatNumber(stats.chat_sessions)}
        icon={<MessageSquare className="h-6 w-6" />}
        color="text-orange-600"
        bg="bg-orange-100"
      />
      <StatCard
        title="Total Messages"
        value={formatNumber(stats.total_messages)}
        icon={<Database className="h-6 w-6" />}
        color="text-indigo-600"
        bg="bg-indigo-100"
      />
      <StatCard
        title="Storage Used"
        value={formatBytes(stats.storage_used_bytes)}
        icon={<HardDrive className="h-6 w-6" />}
        color="text-pink-600"
        bg="bg-pink-100"
      />
      <StatCard
        title="Avg Response Time"
        value={`${stats.avg_response_time_ms}ms`}
        icon={<Clock className="h-6 w-6" />}
        color="text-red-600"
        bg="bg-red-100"
      />
    </div>
  )
}

export default OverviewCards