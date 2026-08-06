import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableFooter } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Table'
import { Badge, RoleBadge, StatusBadge } from '@/components/ui/Badge'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { Search, Plus, MoreVertical, Edit, Trash2, Shield, UserPlus, Building2 } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/stores/authStore'
import { organizationsApi } from '@/services/auth'
import { useOrganizationStore } from '@/stores/organizationStore'
import toast from 'react-hot-toast'

const mockOrganizations = [
  { id: '1', name: 'Acme Corporation', slug: 'acme-corp', description: 'Main organization', is_active: true, member_count: 12, created_at: '2024-01-01', settings: { default_top_k: 5, enable_streaming: true, enable_citations: true } },
  { id: '2', name: 'Beta Inc', slug: 'beta-inc', description: 'Development team', is_active: true, member_count: 8, created_at: '2024-01-10', settings: { default_top_k: 10, enable_streaming: true, enable_citations: true } },
  { id: '3', name: 'Gamma LLC', slug: 'gamma-llc', description: 'Support division', is_active: false, member_count: 3, created_at: '2024-01-15', settings: { default_top_k: 5, enable_streaming: false, enable_citations: false } },
]

export function OrganizationsPage() {
  const { hasRole } = useAuthStore()
  const { organizations, setOrganizations, currentOrganization } = useOrganizationStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedOrg, setSelectedOrg] = useState<typeof mockOrganizations[0] | null>(null)
  const [newOrg, setNewOrg] = useState({ name: '', slug: '', description: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isAdmin = hasRole('admin')

  const handleCreate = async () => {
    try {
      setIsSubmitting(true)
      await organizationsApi.create(newOrg)
      toast.success('Organization created successfully')
      setIsCreateModalOpen(false)
      setNewOrg({ name: '', slug: '', description: '' })
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
      await organizationsApi.update(selectedOrg.id, newOrg)
      toast.success('Organization updated successfully')
      setIsEditModalOpen(false)
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
      await organizationsApi.delete(selectedOrg.id)
      toast.success('Organization deleted successfully')
      setIsDeleteModalOpen(false)
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to delete organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openEditModal = (org: typeof mockOrganizations[0]) => {
    setSelectedOrg(org)
    setNewOrg({ name: org.name, slug: org.slug, description: org.description || '' })
    setIsEditModalOpen(true)
  }

  const openDeleteModal = (org: typeof mockOrganizations[0]) => {
    setSelectedOrg(org)
    setIsDeleteModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Organizations</h1>
          <p className="text-secondary-600 mt-1">Manage your organizations and members</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Organization
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search organizations..."
              className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            />
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableHead>Organization</TableHead>
              <TableHead width="15%">Members</TableHead>
              <TableHead width="15%">Status</TableHead>
              <TableHead width="15%">Created</TableHead>
              <TableHead width="15%">Actions</TableHead>
            </TableHeader>
            <TableBody>
              {mockOrganizations.map((org) => (
                <TableRow key={org.id} hover>
                  <TableCell>
                    <div>
                      <p className="font-medium text-secondary-900">{org.name}</p>
                      <p className="text-xs text-secondary-500">{org.slug}</p>
                      {org.description && <p className="text-xs text-secondary-400 mt-1">{org.description}</p>}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-secondary-600">{org.member_count} members</span>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={org.is_active ? 'active' : 'inactive'} />
                  </TableCell>
                  <TableCell className="text-secondary-600">{org.created_at}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="View members">
                        <Shield className="h-4 w-4 text-secondary-500" />
                      </button>
{isAdmin && (
                          <div>
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
                        )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <Pagination currentPage={currentPage} totalPages={1} onPageChange={setCurrentPage} />
            </TableFooter>
          </Table>
        </CardContent>
      </Card>

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