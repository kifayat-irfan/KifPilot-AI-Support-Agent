import { Database, Plus, Search, Upload, Trash2, Edit, Eye, MoreVertical } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/utils/cn'

interface KnowledgeBase {
  id: string
  name: string
  description: string
  documentCount: number
  chunkCount: number
  status: 'active' | 'inactive' | 'processing'
  createdAt: string
}

const mockKnowledgeBases: KnowledgeBase[] = [
  {
    id: '1',
    name: 'Product Documentation',
    description: 'Official product documentation and user guides',
    documentCount: 12,
    chunkCount: 342,
    status: 'active',
    createdAt: '2024-01-15',
  },
  {
    id: '2',
    name: 'FAQ & Troubleshooting',
    description: 'Frequently asked questions and troubleshooting guides',
    documentCount: 8,
    chunkCount: 156,
    status: 'active',
    createdAt: '2024-01-20',
  },
  {
    id: '3',
    name: 'API Reference',
    description: 'Complete API documentation with examples',
    documentCount: 5,
    chunkCount: 89,
    status: 'processing',
    createdAt: '2024-02-01',
  },
]

export function KnowledgeBasePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDescription, setNewKbDescription] = useState('')

  const handleCreate = () => {
    if (newKbName.trim()) {
      // TODO: Call API to create knowledge base
      setShowCreateModal(false)
      setNewKbName('')
      setNewKbDescription('')
    }
  }

  const filteredKBs = mockKnowledgeBases.filter(kb =>
    kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    kb.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-secondary-900">Knowledge Base</h2>
          <p className="text-secondary-500 mt-1">Manage your knowledge bases and documents</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
        >
          <Plus className="w-4 h-4" />
          New Knowledge Base
        </button>
      </div>

      <div className="card">
        <div className="p-4 border-b border-secondary-200">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge bases..."
              className="input pl-10"
            />
          </div>
        </div>
        <div className="divide-y divide-secondary-200">
          {filteredKBs.map((kb) => (
            <div key={kb.id} className="p-4 hover:bg-secondary-50 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center">
                    <Database className="w-6 h-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-secondary-900">{kb.name}</h3>
                    <p className="text-sm text-secondary-500">{kb.description}</p>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <div className="flex items-center gap-4 text-sm text-secondary-500">
                    <span>{kb.documentCount} documents</span>
                    <span>{kb.chunkCount} chunks</span>
                  </div>
                  <span className={cn(
                    'badge',
                    kb.status === 'active' && 'badge-success',
                    kb.status === 'inactive' && 'badge-warning',
                    kb.status === 'processing' && 'badge-info'
                  )}>
                    {kb.status}
                  </span>
                  <div className="flex items-center gap-2">
                    <button className="p-2 rounded-lg hover:bg-secondary-100 transition-colors" aria-label="View documents">
                      <Eye className="w-5 h-5 text-secondary-500" />
                    </button>
                    <button className="p-2 rounded-lg hover:bg-secondary-100 transition-colors" aria-label="Edit">
                      <Edit className="w-5 h-5 text-secondary-500" />
                    </button>
                    <button className="p-2 rounded-lg hover:bg-secondary-100 transition-colors" aria-label="More options">
                      <MoreVertical className="w-5 h-5 text-secondary-500" />
                    </button>
                    <button className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors" aria-label="Delete">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {filteredKBs.length === 0 && (
            <div className="py-12 text-center">
              <Database className="w-12 h-12 text-secondary-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-secondary-900">No knowledge bases found</h3>
              <p className="text-secondary-500 mt-1">Create your first knowledge base to get started</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-secondary-900 mb-4">Create Knowledge Base</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Name</label>
                <input
                  type="text"
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  className="input"
                  placeholder="e.g., Product Documentation"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Description</label>
                <textarea
                  value={newKbDescription}
                  onChange={(e) => setNewKbDescription(e.target.value)}
                  className="input min-h-[100px]"
                  placeholder="Optional description"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowCreateModal(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleCreate} className="btn-primary">Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}