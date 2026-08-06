import { cn } from '@/utils/cn'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { X, Copy, CheckCircle, AlertCircle, Loader2, ExternalLink, Edit, Trash2, RotateCcw, Download, FileText, Clock, Hash, Database, Layers } from 'lucide-react'
import { Document } from '@/types'

interface DetailsDrawerProps {
  isOpen: boolean
  onClose: () => void
  document: Document | null
  loading?: boolean
  onEdit?: (document: Document) => void
  onDelete?: (document: Document) => void
  onRestore?: (document: Document) => void
  onReindex?: (document: Document) => void
  onDownload?: (document: Document) => void
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateString
  }
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return formatDate(dateString)
  } catch {
    return dateString
  }
}

export function DetailsDrawer({
  isOpen,
  onClose,
  document,
  loading = false,
  onEdit,
  onDelete,
  onRestore,
  onReindex,
  onDownload,
}: DetailsDrawerProps) {
  if (!isOpen || !document) return null

  const isDeleted = !!document.deleted_at
  const isProcessing = ['uploading', 'parsing', 'chunking', 'embedding', 'storing'].includes(document.status)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/50 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col animate-slide-up">
        <CardHeader className="border-b border-secondary-200">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg flex-shrink-0">
                  <FileText className="h-5 w-5 text-primary-600" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-lg truncate">{document.title || document.filename}</CardTitle>
                  <p className="text-sm text-secondary-500 truncate">{document.filename}</p>
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Close details"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto p-0">
          {loading ? (
            <div className="p-8 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-2" />
              <p className="text-secondary-500">Loading details...</p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {/* Status & Category */}
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={document.status} />
                {document.category && (
                  <Badge variant="secondary" size="sm">{document.category}</Badge>
                )}
                {document.language && (
                  <Badge variant="outline" size="sm">{document.language.toUpperCase()}</Badge>
                )}
                {isDeleted && (
                  <Badge variant="destructive" size="sm" dot>Deleted</Badge>
                )}
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">File Size</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {formatBytes(document.file_size)}
                      <Button variant="ghost" size="sm" className="h-6 p-0" onClick={() => navigator.clipboard.writeText(formatBytes(document.file_size))} aria-label="Copy file size">
                        <Copy className="h-3.5 w-3.5 text-secondary-400" />
                      </Button>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">MIME Type</p>
                    <p className="font-mono text-sm text-secondary-700">{document.mime_type}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">File Type</p>
                    <p className="font-medium text-secondary-900">{document.file_type.toUpperCase()}</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">Pages</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {document.page_count.toLocaleString()}
                      <FileText className="h-3.5 w-3.5 text-secondary-400" />
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">Chunks</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {document.chunk_count.toLocaleString()}
                      <Layers className="h-3.5 w-3.5 text-secondary-400" />
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">Embeddings</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {document.embeddings_created.toLocaleString()}
                      <Database className="h-3.5 w-3.5 text-secondary-400" />
                    </p>
                  </div>
                </div>
              </div>

              {/* Processing Info */}
              {document.processing_time_ms && (
                <div className="pt-4 border-t border-secondary-200">
                  <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider mb-2">Processing Information</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium text-secondary-500">Processing Time</p>
                      <p className="font-medium text-secondary-900 flex items-center gap-2">
                        {(document.processing_time_ms / 1000).toFixed(1)}s
                        <Clock className="h-3.5 w-3.5 text-secondary-400" />
                      </p>
                    </div>
                    {document.error_message && (
                      <div>
                        <p className="text-xs font-medium text-secondary-500">Error</p>
                        <p className="font-medium text-red-600 flex items-center gap-2">
                          <AlertCircle className="h-3.5 w-3.5" />
                          {document.error_message}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="pt-4 border-t border-secondary-200">
                <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider mb-2">Timestamps</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-secondary-500">Created</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {formatDate(document.created_at)}
                      <span className="text-secondary-500 text-sm">({formatRelativeTime(document.created_at)})</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-secondary-500">Updated</p>
                    <p className="font-medium text-secondary-900 flex items-center gap-2">
                      {formatDate(document.updated_at)}
                      <span className="text-secondary-500 text-sm">({formatRelativeTime(document.updated_at)})</span>
                    </p>
                  </div>
                  {document.deleted_at && (
                    <>
                      <div>
                        <p className="text-xs font-medium text-secondary-500">Deleted</p>
                        <p className="font-medium text-red-600 flex items-center gap-2">
                          {formatDate(document.deleted_at)}
                          <span className="text-secondary-500 text-sm">({formatRelativeTime(document.deleted_at)})</span>
                        </p>
                      </div>
                      <div />
                    </>
                  )}
                </div>
              </div>

              {/* Description & Tags */}
              {(document.description || document.tags?.length) && (
                <div className="pt-4 border-t border-secondary-200 space-y-4">
                  {document.description && (
                    <div>
                      <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider mb-1">Description</p>
                      <p className="text-secondary-700">{document.description}</p>
                    </div>
                  )}
                  {document.tags?.length && (
                    <div>
                      <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider mb-1">Tags</p>
                      <div className="flex flex-wrap gap-2">
                        {document.tags.map((tag, i) => (
                          <Badge key={i} variant="outline" size="sm">{tag}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* IDs */}
              <div className="pt-4 border-t border-secondary-200">
                <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider mb-2">Identifiers</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-secondary-50 rounded-lg">
                    <span className="text-xs font-medium text-secondary-500">Document ID</span>
                    <div className="flex items-center gap-2">
                      <code className="font-mono text-sm text-secondary-700 truncate max-w-[200px]">{document.id}</code>
                      <Button variant="ghost" size="sm" className="h-6 p-0" onClick={() => navigator.clipboard.writeText(document.id)} aria-label="Copy document ID">
                        <Copy className="h-3.5 w-3.5 text-secondary-400" />
                      </Button>
                    </div>
                  </div>
                  {document.knowledge_base_id && (
                    <div className="flex items-center justify-between p-2 bg-secondary-50 rounded-lg">
                      <span className="text-xs font-medium text-secondary-500">Knowledge Base ID</span>
                      <div className="flex items-center gap-2">
                        <code className="font-mono text-sm text-secondary-700 truncate max-w-[200px]">{document.knowledge_base_id}</code>
                        <Button variant="ghost" size="sm" className="h-6 p-0" onClick={() => navigator.clipboard.writeText(document.knowledge_base_id!)} aria-label="Copy knowledge base ID">
                          <Copy className="h-3.5 w-3.5 text-secondary-400" />
                        </Button>
                      </div>
                    </div>
                  )}
                  {document.organization_id && (
                    <div className="flex items-center justify-between p-2 bg-secondary-50 rounded-lg">
                      <span className="text-xs font-medium text-secondary-500">Organization ID</span>
                      <div className="flex items-center gap-2">
                        <code className="font-mono text-sm text-secondary-700 truncate max-w-[200px]">{document.organization_id}</code>
                        <Button variant="ghost" size="sm" className="h-6 p-0" onClick={() => navigator.clipboard.writeText(document.organization_id!)} aria-label="Copy organization ID">
                          <Copy className="h-3.5 w-3.5 text-secondary-400" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="border-t border-secondary-200 flex-wrap gap-3">
          <div className="flex-1 flex items-center gap-2">
            <Button variant="outline" onClick={onClose}>Close</Button>
            {onDownload && (
              <Button variant="secondary" onClick={() => onDownload?.(document)}>
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isDeleted && onRestore && (
              <Button variant="primary" onClick={() => onRestore?.(document)}>
                <RotateCcw className="h-4 w-4 mr-1" />
                Restore
              </Button>
            )}
            {!isDeleted && (
              <>
                {onEdit && (
                  <Button variant="outline" onClick={() => onEdit?.(document)}>
                    <Edit className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                )}
                {document.status === 'completed' && onReindex && (
                  <Button variant="secondary" onClick={() => onReindex?.(document)}>
                    <RotateCcw className="h-4 w-4 mr-1" />
                    Reindex
                  </Button>
                )}
                {onDelete && (
                  <Button variant="destructive" onClick={() => onDelete?.(document)}>
                    <Trash2 className="h-4 w-4 mr-1" />
                    {isDeleted ? 'Hard Delete' : 'Delete'}
                  </Button>
                )}
              </>
            )}
          </div>
        </CardFooter>
      </div>
    </div>
  )
}

export default DetailsDrawer