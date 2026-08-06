import { useState } from 'react'
import { cn } from '@/utils/cn'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Search, Filter, X, ChevronDown, SlidersHorizontal } from 'lucide-react'
import type { DocumentFilters } from '@/services/knowledgeBase'

interface FilterPanelProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  onSearchSubmit: (query: string) => void
  filters: DocumentFilters
  onFiltersChange: (filters: DocumentFilters) => void
  onClearFilters: () => void
  hasActiveFilters: boolean
  categories: string[]
  languages: string[]
  organizations: Array<{ id: string; name: string }>
  isExpanded?: boolean
  onToggleExpand?: () => void
}

export function FilterPanel({
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  filters,
  onFiltersChange,
  onClearFilters,
  hasActiveFilters,
  categories,
  languages,
  organizations,
  isExpanded = false,
  onToggleExpand,
}: FilterPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(isExpanded)

  const handleFilterChange = (key: keyof typeof filters, value: string) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  return (
    <div className="bg-white rounded-xl border border-secondary-200 overflow-hidden">
      {/* Search Bar */}
      <div className="p-4 border-b border-secondary-200">
        <div className="relative max-w-xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit(e.currentTarget.value)}
            placeholder="Search by title, filename, description..."
            className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Quick Filters */}
      <div className="p-4 border-b border-secondary-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-secondary-700">Quick Filters</h3>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={onClearFilters}>
              <X className="h-3.5 w-3.5 mr-1" />
              Clear all
            </Button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange('category', e.currentTarget.value)}
            className="px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
            aria-label="Category filter"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.currentTarget.value)}
            className="px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
            aria-label="Status filter"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="uploading">Uploading</option>
            <option value="parsing">Parsing</option>
            <option value="chunking">Chunking</option>
            <option value="embedding">Embedding</option>
            <option value="storing">Storing</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Advanced Filters */}
      <Button
        variant="outline"
        size="sm"
        className="mx-4 mb-2"
        onClick={() => setShowAdvanced(!showAdvanced)}
      >
        <SlidersHorizontal className="h-4 w-4 mr-2" />
        {showAdvanced ? 'Hide advanced filters' : 'Show advanced filters'}
        <ChevronDown className={cn('h-4 w-4 ml-1 transition-transform', showAdvanced && 'rotate-180')} />
      </Button>

      {showAdvanced && (
        <div className="px-4 pb-4 space-y-4 animate-slide-down">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-secondary-500 mb-1">Language</label>
              <select
                value={filters.language}
                onChange={(e) => handleFilterChange('language', e.currentTarget.value)}
                className="w-full px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
                aria-label="Language filter"
              >
                <option value="">All Languages</option>
                {languages.map((lang) => (
                  <option key={lang} value={lang}>{lang.toUpperCase()}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-500 mb-1">Organization</label>
              <select
                value={filters.organization_id}
                onChange={(e) => handleFilterChange('organization_id', e.currentTarget.value)}
                className="w-full px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
                aria-label="Organization filter"
              >
                <option value="">All Organizations</option>
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-secondary-500 mb-1">Created After</label>
              <input
                type="date"
                value={filters.created_after}
                onChange={(e) => handleFilterChange('created_after', e.currentTarget.value)}
                className="w-full px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-500 mb-1">Created Before</label>
              <input
                type="date"
                value={filters.created_before}
                onChange={(e) => handleFilterChange('created_before', e.currentTarget.value)}
                className="w-full px-3 py-2 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default FilterPanel