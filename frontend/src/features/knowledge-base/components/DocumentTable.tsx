import { useState, useMemo, useRef, useEffect } from 'react'
import { cn } from '@/utils/cn'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableFooter,
  Pagination,
} from '@/components/ui/Table'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { Search, Upload, Download, Filter, MoreVertical, Eye, Edit, Trash2, RotateCcw, ChevronUp, ChevronDown } from 'lucide-react'
import { Document } from '@/types'
import { formatDistanceToNow } from 'date-fns'

interface DocumentTableProps {
  documents: Document[]
  loading?: boolean
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onView: (document: Document) => void
  onEdit: (document: Document) => void
  onDelete: (document: Document) => void
  onRestore: (document: Document) => void
  onReindex: (document: Document) => void
  currentPage: number
  totalPages: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
  sortBy: string
  sortOrder: 'asc' | 'desc'
  onSort: (key: string) => void
}

export function DocumentTable({
  documents,
  loading = false,
  selectedIds,
  onSelectionChange,
  onView,
  onEdit,
  onDelete,
  onRestore,
  onReindex,
  currentPage,
  totalPages,
  pageSize,
  onPageChange,
  onPageSizeChange,
  sortBy,
  sortOrder,
  onSort,
}: DocumentTableProps) {
  const selectAllRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = selectedIds.length > 0 && selectedIds.length < documents.length
    }
  }, [selectedIds, documents.length])

  const handleSelectAll = () => {
    if (selectedIds.length === documents.length) {
      onSelectionChange([])
    } else {
      onSelectionChange(documents.map(d => d.id))
    }
  }

  const handleSelectOne = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter(s => s !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  const columns = [
    { key: 'select', header: '', width: '40px' },
    { key: 'filename', header: 'Document Name', width: '25%' },
    { key: 'category', header: 'Category', width: '12%' },
    { key: 'organization_id', header: 'Organization', width: '12%' },
    { key: 'language', header: 'Language', width: '10%' },
    { key: 'page_count', header: 'Pages', width: '8%' },
    { key: 'chunk_count', header: 'Chunks', width: '8%' },
    { key: 'embeddings_created', header: 'Embeddings', width: '10%' },
    { key: 'status', header: 'Processing Status', width: '15%' },
    { key: 'created_at', header: 'Created Date', width: '12%' },
    { key: 'actions', header: 'Actions', width: '80px' },
  ]

  const getCategoryLabel = (category: string | null): string => {
    if (!category) return 'Uncategorized'
    return category.charAt(0).toUpperCase() + category.slice(1)
  }

  const getLanguageLabel = (language: string | null): string => {
    if (!language) return 'Unknown'
    return language.toUpperCase()
  }

  const formatDate = (dateString: string): string => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return dateString
    }
  }

  return (
    <div className="bg-white rounded-xl border border-secondary-200 overflow-hidden">
      <Table stickyHeader>
        <TableHeader>
          {columns.map((col) => (
            <TableHead
              key={col.key}
              width={col.width}
              onClick={col.key !== 'select' && col.key !== 'actions' ? () => onSort(col.key) : undefined}
              className={cn('cursor-pointer select-none hover:bg-secondary-100', col.key === 'select' && 'w-10')}
            >
              <div className="flex items-center gap-1">
                {col.key === 'select' ? (
                  <input
                    ref={selectAllRef}
                    type="checkbox"
                    checked={selectedIds.length === documents.length && documents.length > 0}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                    aria-label="Select all"
                  />
                ) : (
                  <>
                    {col.header}
                    {sortBy === col.key && (
                      <span className="text-xs">
                        {sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      </span>
                    )}
                  </>
                )}
              </div>
            </TableHead>
          ))}
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <td colSpan={columns.length} className="text-center py-12">
                <div className="flex items-center justify-center gap-2 text-secondary-500">
                  <svg className="animate-spin h-5 w-5 text-primary-600" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Loading documents...
                </div>
              </td>
            </TableRow>
          ) : documents.length === 0 ? (
            <TableRow>
              <td colSpan={columns.length} className="text-center py-12">
                <div className="flex flex-col items-center gap-2 text-secondary-500">
                  <svg className="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
                  </svg>
                  <p>No documents found</p>
                </div>
              </td>
            </TableRow>
          ) : (
            documents.map((doc) => (
              <TableRow key={doc.id} hover selected={selectedIds.includes(doc.id)}>
                <TableCell className="w-10">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(doc.id)}
                    onChange={() => handleSelectOne(doc.id)}
                    className="w-4 h-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                    aria-label={`Select ${doc.filename}`}
                  />
                </TableCell>
                <TableCell>
                  <div>
                    <p className="font-medium text-secondary-900 truncate max-w-xs">{doc.title || doc.filename}</p>
                    <p className="text-xs text-secondary-500 truncate max-w-xs">{doc.filename}</p>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" size="sm">{getCategoryLabel(doc.category)}</Badge>
                </TableCell>
                <TableCell className="text-secondary-600">
                  {doc.organization_id ? `Org ${doc.organization_id.slice(0, 8)}...` : '—'}
                </TableCell>
                <TableCell className="text-secondary-600">{getLanguageLabel(doc.language)}</TableCell>
                <TableCell className="text-secondary-600">{doc.page_count.toLocaleString()}</TableCell>
                <TableCell className="text-secondary-600">{doc.chunk_count.toLocaleString()}</TableCell>
                <TableCell className="text-secondary-600">{doc.embeddings_created.toLocaleString()}</TableCell>
                <TableCell>
                  <StatusBadge status={doc.status} />
                </TableCell>
                <TableCell className="text-secondary-600 whitespace-nowrap">{formatDate(doc.created_at)}</TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => onView(doc)}
                      className="p-1.5 rounded hover:bg-secondary-100 transition-colors"
                      aria-label="View details"
                    >
                      <Eye className="h-4 w-4 text-secondary-500" />
                    </button>
                    <button
                      onClick={() => onEdit(doc)}
                      className="p-1.5 rounded hover:bg-secondary-100 transition-colors"
                      aria-label="Edit metadata"
                    >
                      <Edit className="h-4 w-4 text-secondary-500" />
                    </button>
                    {doc.status === 'completed' ? (
                      <button
                        onClick={() => onReindex(doc)}
                        className="p-1.5 rounded hover:bg-blue-50 text-blue-600 transition-colors"
                        aria-label="Reindex document"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>
                    ) : null}
                    {doc.deleted_at ? (
                      <button
                        onClick={() => onRestore(doc)}
                        className="p-1.5 rounded hover:bg-green-50 text-green-600 transition-colors"
                        aria-label="Restore document"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => onDelete(doc)}
                        className="p-1.5 rounded hover:bg-red-50 text-red-500 transition-colors"
                        aria-label="Delete document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
        <TableFooter>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={onPageChange}
            showPageSize
            pageSize={pageSize}
            onPageSizeChange={onPageSizeChange}
          />
        </TableFooter>
      </Table>
    </div>
  )
}

export default DocumentTable