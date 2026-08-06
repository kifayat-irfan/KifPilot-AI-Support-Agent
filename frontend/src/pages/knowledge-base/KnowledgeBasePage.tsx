import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/utils/cn'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Upload, Download, Filter, RotateCcw, Trash2, Plus, X } from 'lucide-react'
import { knowledgeBaseService, DocumentFilters } from '@/services/knowledgeBase'
import type { Document, KnowledgeBaseStats } from '@/types'
import { StatisticsCards } from '@/features/knowledge-base/components/StatisticsCards'
import { DocumentTable } from '@/features/knowledge-base/components/DocumentTable'
import { UploadDrawer } from '@/features/knowledge-base/components/UploadDrawer'
import { DetailsDrawer } from '@/features/knowledge-base/components/DetailsDrawer'
import { FilterPanel } from '@/features/knowledge-base/components/FilterPanel'
import toast from 'react-hot-toast'

const STATUSES = ['completed', 'processing', 'uploading', 'parsing', 'chunking', 'embedding', 'storing', 'failed']

export function KnowledgeBasePage() {
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>('')
  const [stats, setStats] = useState<KnowledgeBaseStats | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [statsLoading, setStatsLoading] = useState(false)
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalPages, setTotalPages] = useState(1)
  const [totalDocuments, setTotalDocuments] = useState(0)
  
  // Sorting
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  
  // Selection
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  
  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('')
  const [filters, setFilters] = useState<DocumentFilters>({
    category: '',
    language: '',
    organization_id: '',
    status: '',
    created_after: '',
    created_before: '',
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
  })
  
  // UI State
  const [uploadDrawerOpen, setUploadDrawerOpen] = useState(false)
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [filterPanelExpanded, setFilterPanelExpanded] = useState(false)

  // Mock data for filters
  const categories = ['technical', 'billing', 'general', 'api', 'troubleshooting', 'legal', 'marketing']
  const languages = ['en', 'es', 'fr', 'de', 'zh', 'ja', 'ko', 'pt', 'it', 'ru']
  const organizations = [
    { id: 'org-1', name: 'Acme Corporation' },
    { id: 'org-2', name: 'Global Tech Inc' },
    { id: 'org-3', name: 'StartupXYZ' },
  ]

  // Load knowledge bases on mount
  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  const loadKnowledgeBases = async () => {
    try {
      const response = await knowledgeBaseService.getKnowledgeBases({ limit: 1 })
      if (response.items.length > 0) {
        setKnowledgeBaseId(response.items[0].id)
      }
    } catch (error) {
      console.error('Failed to load knowledge bases:', error)
    }
  }

  const loadStats = useCallback(async () => {
    if (!knowledgeBaseId) return
    setStatsLoading(true)
    try {
      const data = await knowledgeBaseService.getStats(knowledgeBaseId)
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setStatsLoading(false)
    }
  }, [knowledgeBaseId])

  const loadDocuments = useCallback(async () => {
    if (!knowledgeBaseId) return
    setLoading(true)
    try {
      const currentFilters: DocumentFilters = {
        ...filters,
        search: debouncedSearchQuery || undefined,
        page: currentPage,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      const response = await knowledgeBaseService.getDocuments(knowledgeBaseId, currentFilters)
      setDocuments(response.items)
      setTotalPages(response.total_pages)
      setTotalDocuments(response.total)
    } catch (error) {
      console.error('Failed to load documents:', error)
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [knowledgeBaseId, filters, debouncedSearchQuery, currentPage, pageSize, sortBy, sortOrder])

  // Load data when knowledge base changes
  useEffect(() => {
    if (knowledgeBaseId) {
      loadStats()
      loadDocuments()
    }
  }, [knowledgeBaseId, loadStats, loadDocuments])

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery)
      setCurrentPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
  }

  const handleSelectionChange = (ids: string[]) => {
    setSelectedIds(ids)
  }

  const handleView = (document: Document) => {
    setSelectedDocument(document)
    setDetailsDrawerOpen(true)
  }

  const handleEdit = (document: Document) => {
    // TODO: Implement edit metadata
    toast('Edit metadata coming soon')
  }

  const handleDelete = async (document: Document) => {
    if (!confirm(`Delete "${document.title || document.filename}"?`)) return
    try {
      await knowledgeBaseService.deleteDocument(document.id)
      toast.success('Document deleted')
      loadDocuments()
      loadStats()
    } catch (error) {
      console.error('Failed to delete document:', error)
      toast.error('Failed to delete document')
    }
  }

  const handleRestore = async (document: Document) => {
    try {
      await knowledgeBaseService.restoreDocument(document.id)
      toast.success('Document restored')
      loadDocuments()
      loadStats()
    } catch (error) {
      console.error('Failed to restore document:', error)
      toast.error('Failed to restore document')
    }
  }

  const handleReindex = async (document: Document) => {
    try {
      await knowledgeBaseService.reindexDocument(document.id)
      toast.success('Reindex started')
      loadDocuments()
      loadStats()
    } catch (error) {
      console.error('Failed to reindex document:', error)
      toast.error('Failed to reindex document')
    }
  }

  const handleDownload = async (document: Document) => {
    // TODO: Implement download
    toast('Download coming soon')
  }

  const handleUploadComplete = (newDocuments: Document[]) => {
    toast.success(`${newDocuments.length} document(s) uploaded`)
    setUploadDrawerOpen(false)
    loadDocuments()
    loadStats()
  }

  const handleBulkAction = async (action: 'delete' | 'restore' | 'reindex') => {
    if (selectedIds.length === 0) return
    if (!confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} ${selectedIds.length} document(s)?`)) return
    try {
      const result = await knowledgeBaseService.bulkAction(knowledgeBaseId, {
        document_ids: selectedIds,
        action,
      })
      toast.success(`${result.success} document(s) ${action}d${result.failed > 0 ? `, ${result.failed} failed` : ''}`)
      setSelectedIds([])
      loadDocuments()
      loadStats()
    } catch (error) {
      console.error(`Failed to ${action} documents:`, error)
      toast.error(`Failed to ${action} documents`)
    }
  }

  const hasActiveFilters = Object.values(filters).some(v => v !== '' && v !== undefined)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Knowledge Base</h1>
          <p className="text-secondary-600 mt-1">Manage and organize your documents</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setFilterPanelExpanded(!filterPanelExpanded)}>
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button onClick={() => setUploadDrawerOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Documents
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <StatisticsCards
          stats={stats}
          onCardClick={(type: string) => {
            // Could filter by status when clicking stats cards
            console.log('Stat card clicked:', type)
          }}
        />
      )}

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Sidebar - Filter Panel */}
        <aside className="lg:col-span-1 hidden lg:block">
          <FilterPanel
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSearchSubmit={(q: string) => { setDebouncedSearchQuery(q); setCurrentPage(1); }}
            filters={filters}
            onFiltersChange={setFilters}
            onClearFilters={() => setFilters({
              category: '',
              language: '',
              organization_id: '',
              status: '',
              created_after: '',
              created_before: '',
            })}
            hasActiveFilters={hasActiveFilters}
            categories={categories}
            languages={languages}
            organizations={organizations}
            isExpanded={filterPanelExpanded}
            onToggleExpand={() => setFilterPanelExpanded(!filterPanelExpanded)}
          />
        </aside>

        {/* Main Content */}
        <div className="lg:col-span-3 min-w-0">
          <Card>
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <CardTitle className="text-base">Documents</CardTitle>
                  <CardDescription>
                    {totalDocuments} document{totalDocuments !== 1 ? 's' : ''} • Page {currentPage} of {totalPages || 1}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {selectedIds.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-secondary-600">
                        {selectedIds.length} selected
                      </span>
                      <Button variant="outline" size="sm" onClick={() => handleBulkAction('delete')}>
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Delete
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleBulkAction('restore')}>
                        <RotateCcw className="h-3.5 w-3.5 mr-1" />
                        Restore
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleBulkAction('reindex')}>
                        <RotateCcw className="h-3.5 w-3.5 mr-1" />
                        Reindex
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>
                        <X className="h-3.5 w-3.5 mr-1" />
                        Clear
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <DocumentTable
                documents={documents}
                loading={loading}
                selectedIds={selectedIds}
                onSelectionChange={handleSelectionChange}
                onView={handleView}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onRestore={handleRestore}
                onReindex={handleReindex}
                currentPage={currentPage}
                totalPages={totalPages}
                pageSize={pageSize}
                onPageChange={setCurrentPage}
                onPageSizeChange={setPageSize}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Upload Drawer */}
      <UploadDrawer
        isOpen={uploadDrawerOpen}
        onClose={() => setUploadDrawerOpen(false)}
        knowledgeBaseId={knowledgeBaseId}
        onUploadComplete={handleUploadComplete}
      />

      {/* Details Drawer */}
      <DetailsDrawer
        isOpen={detailsDrawerOpen}
        onClose={() => { setDetailsDrawerOpen(false); setSelectedDocument(null) }}
        document={selectedDocument}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onRestore={handleRestore}
        onReindex={handleReindex}
        onDownload={handleDownload}
      />
    </div>
  )
}

export default KnowledgeBasePage