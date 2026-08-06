import { cn } from '@/utils/cn'
import { FileText, CheckCircle, Loader2, AlertCircle, Database, ExternalLink } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  variant: 'primary' | 'success' | 'warning' | 'destructive' | 'secondary'
  trend?: { value: string; label: string }
  onClick?: () => void
}

function StatCard({ title, value, icon, variant, trend, onClick }: StatCardProps) {
  const variants = {
    primary: 'bg-primary-50 text-primary-700 border-primary-200',
    success: 'bg-green-50 text-green-700 border-green-200',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    destructive: 'bg-red-50 text-red-700 border-red-200',
    secondary: 'bg-secondary-50 text-secondary-700 border-secondary-200',
  }

  return (
    <div
      className={cn(
        'p-5 rounded-xl border transition-all hover:shadow-md',
        onClick && 'cursor-pointer',
        variants[variant]
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-secondary-600 mb-1">{title}</p>
          <p className="text-2xl font-bold text-secondary-900">{value}</p>
          {trend && (
            <p className="mt-1 text-xs text-secondary-500 flex items-center gap-1">
              <span className="text-green-600">{trend.value}</span>
              <span>{trend.label}</span>
            </p>
          )}
        </div>
        <div className="p-2 rounded-lg bg-white/50">
          {icon}
        </div>
      </div>
    </div>
  )
}

export function StatisticsCards({
  stats,
  onCardClick,
}: {
  stats: {
    total_documents: number
    indexed_documents: number
    processing_documents: number
    failed_documents: number
    storage_used_bytes: number
  }
  onCardClick?: (type: string) => void
}) {
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <StatCard
        title="Total Documents"
        value={stats.total_documents.toLocaleString()}
        icon={<FileText className="h-6 w-6" />}
        variant="primary"
        onClick={() => onCardClick?.('total')}
      />
      <StatCard
        title="Indexed"
        value={stats.indexed_documents.toLocaleString()}
        icon={<CheckCircle className="h-6 w-6" />}
        variant="success"
        onClick={() => onCardClick?.('indexed')}
      />
      <StatCard
        title="Processing"
        value={stats.processing_documents.toLocaleString()}
        icon={<Loader2 className="h-6 w-6 animate-spin" />}
        variant="warning"
        onClick={() => onCardClick?.('processing')}
      />
      <StatCard
        title="Failed"
        value={stats.failed_documents.toLocaleString()}
        icon={<AlertCircle className="h-6 w-6" />}
        variant="destructive"
        onClick={() => onCardClick?.('failed')}
      />
      <StatCard
        title="Storage Used"
        value={formatBytes(stats.storage_used_bytes)}
        icon={<Database className="h-6 w-6" />}
        variant="secondary"
        onClick={() => onCardClick?.('storage')}
      />
    </div>
  )
}

export default StatisticsCards