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
import { Badge, RoleBadge, StatusBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { Search, Plus, MoreVertical, Edit, Trash2, Shield, UserPlus, Mail, User as UserIcon } from 'lucide-react'
import type { AdminUser } from '@/types'
import toast from 'react-hot-toast'
import { adminApi } from '@/services/admin'

interface UsersTableProps {
  onRefresh?: () => void
}

export function UsersTable({ onRefresh }: UsersTableProps) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [newUser, setNewUser] = useState({ email: '', username: '', password: '', is_active: true })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await adminApi.getUsers({
        search: searchQuery || undefined,
        role: selectedRole || undefined,
        is_active: selectedStatus === '' ? undefined : selectedStatus === 'active',
        page: currentPage,
        page_size: 20,
      })
      setUsers(response.items)
      setTotalPages(response.total_pages)
    } catch (error) {
      console.error('Failed to load users:', error)
      toast.error('Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      setIsSubmitting(true)
      // Note: This would need a create user endpoint in adminApi
      toast.success('User creation would be implemented here')
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
      await adminApi.updateUser(selectedUser.id, {
        email: newUser.email,
        username: newUser.username,
        is_active: newUser.is_active,
      })
      toast.success('User updated successfully')
      setIsEditModalOpen(false)
      loadUsers()
      onRefresh?.()
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
      await adminApi.deleteUser(selectedUser.id)
      toast.success('User deleted successfully')
      setIsDeleteModalOpen(false)
      loadUsers()
      onRefresh?.()
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Failed to delete user')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openEditModal = (user: AdminUser) => {
    setSelectedUser(user)
    setNewUser({ email: user.email, username: user.username, password: '', is_active: user.is_active })
    setIsEditModalOpen(true)
  }

  const openDeleteModal = (user: AdminUser) => {
    setSelectedUser(user)
    setIsDeleteModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-secondary-900">Users</h2>
          <p className="text-secondary-600 mt-1">Manage user accounts and permissions</p>
        </div>
        <Button onClick={() => { setNewUser({ email: '', username: '', password: '', is_active: true }); setIsCreateModalOpen(true) }}>
          <UserPlus className="h-4 w-4 mr-2" />
          Invite User
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-secondary-200">
        <div className="p-4 border-b border-secondary-200">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1) }}
                placeholder="Search users..."
                className="w-full pl-10 pr-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <select
              value={selectedRole}
              onChange={(e) => { setSelectedRole(e.target.value); setCurrentPage(1) }}
              className="px-3 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white w-40"
            >
              <option value="">All Roles</option>
              <option value="admin">Admin</option>
              <option value="manager">Manager</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>
            <select
              value={selectedStatus}
              onChange={(e) => { setSelectedStatus(e.target.value); setCurrentPage(1) }}
              className="px-3 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white w-40"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableHead>User</TableHead>
            <TableHead width="15%">Roles</TableHead>
            <TableHead width="12%">Organization</TableHead>
            <TableHead width="12%">Status</TableHead>
            <TableHead width="15%">Last Login</TableHead>
            <TableHead width="15%">Joined</TableHead>
            <TableHead width="12%">Actions</TableHead>
          </TableHeader>
          <TableBody>
            {loading
              ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12">
                    <div className="flex items-center justify-center gap-2 text-secondary-500">
                      <svg className="animate-spin h-5 w-5 text-primary-600" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Loading users...
                    </div>
                  </TableCell>
                </TableRow>
              )
              : users.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12">
                    <div className="flex flex-col items-center gap-2 text-secondary-500">
                      <UserIcon className="h-10 w-10" />
                      <p>No users found</p>
                    </div>
                  </TableCell>
                </TableRow>
              )
              : (
                users.map((user) => (
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
                  <TableCell className="text-secondary-600">{user.organization_name}</TableCell>
                  <TableCell>
                    <StatusBadge status={user.is_active ? 'active' : 'inactive'} />
                  </TableCell>
                  <TableCell className="text-secondary-600">
                    {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                  </TableCell>
                  <TableCell className="text-secondary-600">{new Date(user.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-secondary-100 transition-colors" aria-label="View">
                        <Shield className="h-4 w-4 text-secondary-500" />
                      </button>
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

export default UsersTable