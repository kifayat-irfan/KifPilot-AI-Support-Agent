import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableFooter } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Table'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { Search, Upload, Download, Filter, MoreVertical, Eye, Edit, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/utils/cn'

const mockDocuments = [
  { id: '1', filename: 'API_Documentation.pdf', title: 'API Documentation', category: 'technical', status: 'completed', size: '2.4 MB', pages: 45, chunks: 120, created: '2024-01-15' },
  { id: '2', filename: 'User_Guide.docx', title: 'User Guide', category: 'general', status: 'completed', size: '1.8 MB', pages: 32, chunks: 85, created: '2024-01-10' },
  { id: '3', filename: 'Billing_FAQ.pdf', title: 'Billing FAQ', category: 'billing', status: 'completed', size: '512 KB', pages: 8, chunks: 22, created: '2024-01-08' },
  { id: '4', filename: 'Troubleshooting.pdf', title: 'Troubleshooting Guide', category: 'troubleshooting', status: 'processing', size: '3.1 MB', pages: 52, chunks: 0, created: '2024-01-18' },
  { id: '5', filename: 'Release_Notes.md', title: 'Release Notes v2.0', category: 'general', status: 'completed', size: '128 KB', pages: 5, chunks: 12, created: '2024-01-05' },
]

export function DocumentsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState('created')
  const [sortOrder, setSortOrder] = useState('desc')

  const categories = ['all', 'technical', 'general', 'billing', 'api', 'troubleshooting']

  const columns = [
    { key: 'filename', header: 'Document', width: '30%' },
    { key: 'category', header: 'Category', width: '15%' },
    { key: 'status', header: 'Status', width: '15%' },
    { key: 'size', header: 'Size', width: '10%' },
    { key: 'pages', header: 'Pages', width: '10%' },
    { key: 'chunks', header: 'Chunks', width: '10%' },
    { key: 'created', header: 'Created', width: '15%' },
  ]

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Documents</h1>
          <p className="text-secondary-600 mt-1">Manage and organize your knowledge base documents</p>
        </div>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload Document
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  width={col.width}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer select-none hover:bg-secondary-100"
                >
                  <div className="flex items-center gap-1">
                    {col.header}
                    {sortBy === col.key && (
                      <span className="text-xs">
                        {sortOrder === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </TableHead>
              ))}
              <TableHead>Actions</TableHead>
            </TableHeader>
            <TableBody>
              {mockDocuments.map((doc) => (
                <TableRow key={doc.id} hover>
                  <TableCell>
                    <div>
                      <p className="font-medium text-secondary-900 truncate max-w-xs">{doc.title || doc.filename}</p>
                      <p className="text-xs text-secondary-500 truncate max-w-xs">{doc.filename}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" size="sm">{doc.category}</Badge>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={doc.status} />
                  </TableCell>
                  <TableCell>{doc.size}</TableCell>
                  <TableCell className="text-secondary-600">{doc.pages}</TableCell>
                  <TableCell className="text-secondary-600">{doc.chunks}</TableCell>
                  <TableCell className="text-secondary-600">{doc.created}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="View">
                        <Eye className="h-4 w-4 text-secondary-500" />
                      </button>
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="Edit">
                        <Edit className="h-4 w-4 text-secondary-500" />
                      </button>
                      <button className="p-1.5 rounded hover:bg-red-50 text-red-500 transition-colors" aria-label="Delete">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <Pagination
                currentPage={currentPage}
                totalPages={3}
                onPageChange={setCurrentPage}
                showPageSize
                pageSize={20}
                onPageSizeChange={() => {}}
              />
            </TableFooter>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}