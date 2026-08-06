import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableFooter } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Table'
import { Badge, RoleBadge, StatusBadge } from '@/components/ui/Badge'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { Search, Plus, MoreVertical, Edit, Trash2, Shield, UserPlus, Mail, User as UserIcon } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/stores/authStore'
import { usersApi } from '@/services/resources'
import toast from 'react-hot-toast'

const mockUsers = [
  { id: '1', email: 'admin@acme.com', username: 'admin', is_active: true, created_at: '2024-01-01', roles: [{ id: '1', name: 'admin' }] },
  { id: '2', email: 'john@acme.com', username: 'john_doe', is_active: true, created_at: '2024-01-05', roles: [{ id: '2', name: 'editor' }] },
  { id: '3', email: 'jane@acme.com', username: 'jane_smith', is_active: true, created_at: '2024-01-10', roles: [{ id: '3', name: 'viewer' }] },
  { id: '4', email: 'bob@acme.com', username: 'bob_wilson', is_active: false, created_at: '2024-01-15', roles: [{ id: '2', name: 'editor' }] },
  { id: '5', email: 'alice@acme.com', username: 'alice_jones', is_active: true, created_at: '2024-01-20', roles: [{ id: '3', name: 'viewer' }] },
]

export function UsersPage() {
  const { hasRole } = useAuthStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<typeof mockUsers[0] | null>(null)
  const [newUser, setNewUser] = useState({ email: '', username: '', password: '', is_active: true })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isAdmin = hasRole('admin')

  const handleCreate = async () => {
    try {
      setIsSubmitting(true)
      // await usersApi.create(newUser)
      toast.success('User created successfully')
      setIsCreateModalOpen(false)
      setNewUser({ email: '', username: '', password: '', is_active: true })
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to create user')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = async () => {
    if (!selectedUser) return
    try {
      setIsSubmitting(true)
      // await usersApi.update(selectedUser.id, newUser)
      toast.success('User updated successfully')
      setIsEditModalOpen(false)
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to update user')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedUser) return
    try {
      setIsSubmitting(true)
      // await usersApi.delete(selectedUser.id)
      toast.success('User deleted successfully')
      setIsDeleteModalOpen(false)
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to delete user')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openEditModal = (user: typeof mockUsers[0]) => {
    setSelectedUser(user)
    setNewUser({ email: user.email, username: user.username, password: '', is_active: user.is_active })
    setIsEditModalOpen(true)
  }

  const openDeleteModal = (user: typeof mockUsers[0]) => {
    setSelectedUser(user)
    setIsDeleteModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Users</h1>
          <p className="text-secondary-600 mt-1">Manage user accounts and permissions</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <UserPlus className="h-4 w-4 mr-2" />
            Invite User
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
              placeholder="Search users..."
              className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            />
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableHead>User</TableHead>
              <TableHead width="15%">Roles</TableHead>
              <TableHead width="15%">Status</TableHead>
              <TableHead width="15%">Joined</TableHead>
              <TableHead width="15%">Actions</TableHead>
            </TableHeader>
            <TableBody>
              {mockUsers.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                        <UserIcon className="h-4 w-4 text-primary-700" aria-hidden="true" />
                      </div>
                      <div>
                        <p className="font-medium text-secondary-900">{user.username}</p>
                        <p className="text-xs text-secondary-500">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <RoleBadge key={role.id} role={role.name} />
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={user.is_active ? 'active' : 'inactive'} />
                  </TableCell>
                  <TableCell className="text-secondary-600">{user.created_at}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="View">
                        <Shield className="h-4 w-4 text-secondary-500" />
                      </button>
{isAdmin && (
                          <div>
                            <button
                              onClick={() => openEditModal(user)}
                              className="p-1.5 rounded hover:bg-secondary-100 transition-colors"
                              aria-label="Edit"
                            >
                              <Edit className="h-4 w-4 text-secondary-500" />
                            </button>
                            <button
                              onClick={() => openDeleteModal(user)}
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

      {/* Create User Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Invite User"
        description="Enter the user's details to invite them to the organization"
      >
        <form onSubmit={(e) => { e.preventDefault(); handleCreate() }} className="space-y-4">
          <Input label="Email" type="email" value={newUser.email} onChange={(e) => setNewUser({...newUser, email: e.target.value})} placeholder="user@example.com" required />
          <Input label="Username" value={newUser.username} onChange={(e) => setNewUser({...newUser, username: e.target.value})} placeholder="username" required />
          <Input label="Password" type="password" value={newUser.password} onChange={(e) => setNewUser({...newUser, password: e.target.value})} placeholder="••••••••" required />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active" checked={newUser.is_active} onChange={(e) => setNewUser({...newUser, is_active: e.target.checked})} className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500" />
            <label htmlFor="is_active" className="text-sm text-secondary-700">Active</label>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => setIsCreateModalOpen(false)}>Cancel</Button>
            <Button type="submit" loading={isSubmitting}>Invite User</Button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => { setIsEditModalOpen(false); setSelectedUser(null); }}
        title="Edit User"
        description="Update user details and roles"
      >
        <form onSubmit={(e) => { e.preventDefault(); handleEdit() }} className="space-y-4">
          <Input label="Email" type="email" value={newUser.email} onChange={(e) => setNewUser({...newUser, email: e.target.value})} required />
          <Input label="Username" value={newUser.username} onChange={(e) => setNewUser({...newUser, username: e.target.value})} required />
          <Input label="New Password (leave blank to keep current)" type="password" value={newUser.password} onChange={(e) => setNewUser({...newUser, password: e.target.value})} placeholder="••••••••" />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active_edit" checked={newUser.is_active} onChange={(e) => setNewUser({...newUser, is_active: e.target.checked})} className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500" />
            <label htmlFor="is_active_edit" className="text-sm text-secondary-700">Active</label>
          </div>
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
        title="Delete User"
        message={`Are you sure you want to delete "${selectedUser?.username}"? This action cannot be undone.`}
        confirmText="Delete"
        variant="danger"
        loading={isSubmitting}
      />
    </div>
  )
}