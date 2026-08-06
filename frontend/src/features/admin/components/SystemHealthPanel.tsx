import { cn } from '@/utils/cn'
import {
  Server,
  Database,
  Cpu,
  HardDrive,
  Layers,
  Globe,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
} from 'lucide-react'
import type { SystemHealth } from '@/types'

interface HealthCardProps {
  label: string
  status: 'healthy' | 'degraded' | 'down'
  icon: React.ReactNode
  loading?: boolean
}

function HealthCard({ label, status, icon, loading }: HealthCardProps) {
  const statusConfig = {
    healthy: { color: 'text-green-600', bg: 'bg-green-100', border: 'border-green-200', icon: CheckCircle },
    degraded: { color: 'text-yellow-600', bg: 'bg-yellow-100', border: 'border-yellow-200', icon: AlertTriangle },
    down: { color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200', icon: XCircle },
  }

  const config = statusConfig[status]

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-secondary-200 animate-pulse">
        <div className="h-10 w-10 bg-secondary-200 rounded-lg flex items-center justify-center mb-2" />
        <div className="h-4 bg-secondary-200 rounded w-3/4 mb-1" />
        <div className="h-3 bg-secondary-200 rounded w-1/2" />
      </div>
    )
  }

  return (
    <div className={cn('p-4 rounded-xl border', config.border)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', config.bg)}>
            {icon}
          </div>
          <div>
            <p className="text-sm font-medium text-secondary-600">{label}</p>
            <p className="text-sm font-semibold" style={{ color: config.color.replace('text-', '') }}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </p>
          </div>
        </div>
        <div className={cn('p-2 rounded-full', config.bg)}>
          {status === 'healthy' ? (
            <CheckCircle className={cn('h-5 w-5', config.color)} />
          ) : status === 'degraded' ? (
            <AlertTriangle className={cn('h-5 w-5', config.color)} />
          ) : (
            <XCircle className={cn('h-5 w-5', config.color)} />
          )}
        </div>
      </div>
    </div>
  )
}

export function SystemHealthPanel({ health, loading = false }: { health: SystemHealth | null; loading?: boolean }) {
  if (!health && !loading) return null

  const services = [
    { key: 'backend', label: 'Backend API', icon: <Server className="h-5 w-5" /> },
    { key: 'database', label: 'Database', icon: <Database className="h-5 w-5" /> },
    { key: 'ollama', label: 'Ollama', icon: <Cpu className="h-5 w-5" /> },
    { key: 'chromadb', label: 'ChromaDB', icon: <HardDrive className="h-5 w-5" /> },
    { key: 'vector_collections', label: 'Vector Collections', icon: <Layers className="h-5 w-5" /> },
    { key: 'api', label: 'API Gateway', icon: <Globe className="h-5 w-5" /> },
    { key: 'background_services', label: 'Background Services', icon: <Activity className="h-5 w-5" /> },
  ] as const

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-secondary-900">System Health</h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {services.map((service) => (
          <HealthCard
            key={service.key}
            label={service.label}
            status={health?.[service.key] || 'healthy'}
            icon={service.icon}
            loading={loading}
          />
        ))}
      </div>
    </div>
  )
}

export default SystemHealthPanel