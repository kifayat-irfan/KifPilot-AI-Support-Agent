import { cn } from '@/utils/cn'
import type { TimeSeriesData } from '@/types'

interface ChartProps {
  data: Array<{ date: string; value: number }>
  title: string
  color: string
  loading?: boolean
  formatValue?: (value: number) => string
  height?: number
}

function Chart({ data, title, color, loading = false, formatValue, height = 200 }: ChartProps) {
  if (loading || !data.length) {
    return (
      <div className="bg-white rounded-xl border border-secondary-200 p-6 h-[250px] animate-pulse">
        <div className="h-5 bg-secondary-200 rounded w-1/4 mb-4" />
        <div className="h-[200px] bg-secondary-100 rounded" />
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.value))
  const minValue = Math.min(...data.map(d => d.value))
  const range = maxValue - minValue || 1

  const getY = (value: number) => {
    return height - ((value - minValue) / range) * (height - 20) - 10
  }

  const getX = (index: number) => {
    return (index / (data.length - 1 || 1)) * (width - 40) + 20
  }

  const width = 600 // This will be responsive via CSS

  const points = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' ')

  return (
    <div className="bg-white rounded-xl border border-secondary-200 p-6">
      <h3 className="text-lg font-semibold text-secondary-900 mb-4">{title}</h3>
      <div className="relative h-[200px] w-full">
        <svg className="w-full h-full" viewBox="0 0 600 200" preserveAspectRatio="none">
          {/* Grid lines */}
          <defs>
            <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          
          {/* Area */}
          <path
            d={`M${points} L${width - 20},${height - 10} L20,${height - 10} Z`}
            fill="url(#gradient)"
            stroke="none"
          />
          
          {/* Line */}
          <path
            d={`M${points}`}
            stroke={color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          
          {/* Points */}
          {data.map((d, i) => (
            <circle
              key={i}
              cx={getX(i)}
              cy={getY(d.value)}
              r="4"
              fill={color}
              stroke="white"
              strokeWidth="2"
            />
          ))}
        </svg>
        
        {/* X-axis labels */}
        <div className="flex justify-between mt-2 text-xs text-secondary-500">
          {data.length > 0 && (
            <>
              <span>{new Date(data[0].date).toLocaleDateString()}</span>
              <span>{new Date(data[Math.floor(data.length / 2)].date).toLocaleDateString()}</span>
              <span>{new Date(data[data.length - 1].date).toLocaleDateString()}</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

interface ChartsGridProps {
  data: TimeSeriesData
  loading?: boolean
}

export function ChartsGrid({ data, loading = false }: ChartsGridProps) {
  const charts = [
    { key: 'documents_uploaded', title: 'Documents Uploaded Per Day', color: '#3b82f6', data: data.documents_uploaded },
    { key: 'questions_per_day', title: 'Questions Per Day', color: '#10b981', data: data.questions_per_day },
    { key: 'response_time_trend', title: 'Response Time Trend (ms)', color: '#f59e0b', data: data.response_time_trend },
    { key: 'active_users', title: 'Active Users', color: '#8b5cf6', data: data.active_users },
    { key: 'storage_growth', title: 'Storage Growth (MB)', color: '#ec4899', data: data.storage_growth },
  ]

  return (
    <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
      {charts.map((chart) => (
        <Chart
          key={chart.key}
          title={chart.title}
          data={chart.data}
          color={chart.color}
          loading={loading}
          formatValue={chart.key === 'storage_growth' ? (v) => `${(v / 1024 / 1024).toFixed(1)} MB` : undefined}
        />
      ))}
    </div>
  )
}

export default ChartsGrid