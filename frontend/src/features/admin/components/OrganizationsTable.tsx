import { useState } from 'react'
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
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { Search, Plus, MoreVertical, Edit, Trash2, Eye, Shield } from 'lucide-react'
import type { AdminOrganization } from '@/types'
import toast from 'react-hot-toast'
import { adminApi } from '@/services/admin'

interface OrganizationsTableProps {
  onRefresh?: () => void
}

export function OrganizationsTable({ onRefresh }: OrganizationsTableProps) {
  const [organizations, setOrganizations] = useState<AdminOrganization[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedOrg, setSelectedOrg] = useState<AdminOrganization | null>(null)
  const [newOrg, setNewOrg] = useState({ name: '', slug: '', description: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadOrganizations = async () => {
    setLoading(true)
    try {
      const response = await adminApi.getOrganizations({
        search: searchQuery || undefined,
        page: currentPage,
        page_size: 20,
      })
      setOrganizations(response.items)
      setTotalPages(response.total_pages)
    } catch (error) {
      console.error('Failed to load organizations:', error)
      toast.error('Failed to load organizations')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      setIsSubmitting(true)
      await adminApi.createOrganization({
        name: newOrg.name,
        slug: newOrg.slug,
        description: newOrg.description,
      })
      toast.success('Organization created successfully')
      setIsCreateModalOpen(false)
      setNewOrg({ name: '', slug: '', description: '' })
      loadOrganizations()
      onRefresh?.()
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to create organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = async () => {
    if (!selectedOrg) return
    try {
      setIsSubmitting(true)
      await adminApi.updateOrganization(selectedOrg.id, newOrg)
      toast.success('Organization updated successfully')
      setIsEditModalOpen(false)
      loadOrganizations()
      onRefresh?.()
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to update organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedOrg) return
    try {
      setIsSubmitting(true)
      await adminApi.deleteOrganization(selectedOrg.id)
      toast.success('Organization deleted successfully')
      setIsDeleteModalOpen(false)
      loadOrganizations()
      onRefresh?.()
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to delete organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openEditModal = (org: AdminOrganization) => {
    setSelectedOrg(org)
    setNewOrg({ name: org.name, slug: org.slug, description: org.description || '' })
    setIsEditModalOpen(true)
  }

  const openDeleteModal = (org: AdminOrganization) => {
    setSelectedOrg(org)
    setIsDeleteModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-secondary-900">Organizations</h2>
          <p className="text-secondary-600 mt-1">Manage organizations and their settings</p>
        </div>
        <Button onClick={() => { setNewOrg({ name: '', slug: '', description: '' }); setIsCreateModalOpen(true) }}>
          <Plus className="h-4 w-4 mr-2" />
          Create Organization
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-secondary-200">
        <div className="p-4 border-b border-secondary-200">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1) }}
              placeholder="Search organizations..."
              className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            />
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableHead>Organization</TableHead>
            <TableHead width="12%">Members</TableHead>
            <TableHead width="12%">Documents</TableHead>
            <TableHead width="12%">Storage</TableHead>
            <TableHead width="12%">Status</TableHead>
            <TableHead width="15%">Created</TableHead>
            <TableHead width="12%">Actions</TableHead>
          </TableHeader>
<TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12">
                  <div className="flex items-center justify-center gap-2 text-secondary-500">
                    <svg className="animate-spin h-5 w-5 text-primary-600" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Loading organizations...
                  </div>
                </TableCell>
              </TableRow>
            ) : organizations.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12">
                  <div className="flex flex-col items-center gap-2 text-secondary-500">
                    <Shield className="h-10 w-10" />
                    <p>No organizations found</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              organizations.map((org) => (
                <TableRow key={org.id} hover>
                  <TableCell>
                    <div>
                      <p className="font-medium text-secondary-900 truncate max-w-xs">{org.name}</p>
                      <p className="text-xs text-secondary-500 truncate max-w-xs">{org.slug}</p>
                      {org.description && <p className="text-xs text-secondary-400 mt-1 truncate max-w-xs">{org.description}</p>}
                    </div>
                  </TableCell>
                  <TableCell className="text-secondary-600">{org.member_count.toLocaleString()} members</TableCell>
                  <TableCell className="text-secondary-600">{org.document_count.toLocaleString()}</TableCell>
                  <TableCell className="text-secondary-600">
                    {(org.storage_used_bytes / 1024 / 1024 / 1024).toFixed(2)} GB
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={org.is_active ? 'active' : 'inactive'} />
                  </TableCell>
                  <TableCell className="text-secondary-600">{new Date(org.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="View">
                        <Eye className="h-4 w-4 text-secondary-500" />
                      </button>
                      <button
                        onClick={() => openEditModal(org)}
                        className="p-1.5 rounded hover:bg-secondary-100 transition-colors"
                        aria-label="Edit"
                      >
                        <Edit className="h-4 w-4 text-secondary-500" />
                      </button>
                      <button
                        onClick={() => openDeleteModal(org)}
                        className="p-1.5 rounded hover:bg-red-50 text-red-500 transition-colors"
                        aria-label="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
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
              onPageChange={setCurrentPage}
            />
          </TableFooter>
        </Table>
      </div>

      {/* Create Organization Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Organization"
        description="Enter the details for your new organization"
      >
        <form onSubmit={(e) => { e.preventDefault(); handleCreate() }} className="space-y-4">
          <Input label="Name" value={newOrg.name} onChange={(e) => setNewOrg({...newOrg, name: e.target.value})} placeholder="Acme Corporation" required />
          <Input label="Slug" value={newOrg.slug} onChange={(e) => setNewOrg({...newOrg, slug: e.target.value})} placeholder="acme-corp" helperText="URL-friendly identifier" required />
          <Input label="Description" value={newOrg.description} onChange={(e) => setNewOrg({...newOrg, description: e.target.value})} placeholder="Optional description" />
          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => setIsCreateModalOpen(false)}>Cancel</Button>
            <Button type="submit" loading={isSubmitting}>Create Organization</Button>
          </div>
        </form>
      </Modal>

      {/* Edit Organization Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => { setIsEditModalOpen(false); setSelectedOrg(null); }}
        title="Edit Organization"
        description="Update organization details"
      >
        <form onSubmit={(e) => { e.preventDefault(); handleEdit() }} className="space-y-4">
          <Input label="Name" value={newOrg.name} onChange={(e) => setNewOrg({...newOrg, name: e.target.value})} required />
          <Input label="Slug" value={newOrg.slug} onChange={(e) => setNewOrg({...newOrg, slug: e.target.value})} required />
          <Input label="Description" value={newOrg.description} onChange={(e) => setNewOrg({...newOrg, description: e.target.value})} />
          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
            <Button type="submit" loading={isSubmitting}>Save Changes</Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDelete}
        title="Delete Organization"
        message={`Are you sure you want to delete "${selectedOrg?.name}"? This action cannot be undone and will remove all associated documents, chat sessions, and members.`}
        confirmText="Delete"
        variant="danger"
        loading={isSubmitting}
      />
    </div>
  )
}

export default OrganizationsTable