import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { useState } from 'react'
import { cn } from '@/utils/cn'
import {
  Bell,
  Shield,
  Palette,
  Database,
  Zap,
  FileText,
  User,
  Moon,
  Sun,
  Monitor,
  Save,
  Loader2,
  Download,
  Key,
  LogOut,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useSettingsStore } from '@/stores/settingsStore'
import { useAuthStore } from '@/stores/authStore'
import toast from 'react-hot-toast'

const settingsSections = [
  {
    id: 'profile',
    label: 'Profile',
    icon: User,
    description: 'Manage your account profile and password',
  },
  {
    id: 'appearance',
    label: 'Appearance',
    icon: Palette,
    description: 'Customize how KifPilot looks',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    icon: Bell,
    description: 'Configure notification preferences',
  },
  {
    id: 'chat',
    label: 'Chat',
    icon: FileText,
    description: 'Configure chat behavior and streaming',
  },
  {
    id: 'security',
    label: 'Security',
    icon: Shield,
    description: 'Manage authentication and sessions',
  },
  {
    id: 'data',
    label: 'Data & Storage',
    icon: Database,
    description: 'Manage data retention and export',
  },
]

export function SettingsPage() {
  const [activeSection, setActiveSection] = useState('profile')
  const {
    theme,
    language,
    sidebarCollapsed,
    compactMode,
    notificationsEnabled,
    streamingEnabled,
    citationsEnabled,
  } = useSettingsStore()
  const { user } = useAuthStore()
  const [isSaving, setIsSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleSave = async () => {
    setIsSaving(true)
    // Simulate save
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSaving(false)
    toast.success('Settings saved successfully')
  }

  const handlePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setIsSaving(true)
    // Simulate password change
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSaving(false)
    toast.success('Password updated successfully')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
  }

  const renderSection = () => {
    switch (activeSection) {
      case 'profile':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input label="Full Name" defaultValue={user?.username || ''} placeholder="John Doe" />
                  <Input label="Email" type="email" defaultValue={user?.email || ''} placeholder="john@example.com" />
                </div>
                <Input label="Username" defaultValue={user?.username || ''} placeholder="johndoe" />
              </CardContent>
              <CardFooter>
                <Button onClick={handleSave} loading={isSaving}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Update your account password</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input label="Current Password" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="••••••••" />
                <Input label="New Password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="••••••••" helperText="Must be at least 8 characters" />
                <Input label="Confirm New Password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="••••••••" />
              </CardContent>
              <CardFooter>
                <Button onClick={handlePasswordChange} loading={isSaving} variant="secondary">
                  Update Password
                </Button>
              </CardFooter>
            </Card>
          </div>
        )

      case 'appearance':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Theme</CardTitle>
                <CardDescription>Choose your preferred color scheme</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    { value: 'light', label: 'Light', icon: <Sun className="h-5 w-5" /> },
                    { value: 'dark', label: 'Dark', icon: <Moon className="h-5 w-5" /> },
                    { value: 'system', label: 'System', icon: <Monitor className="h-5 w-5" /> },
                  ].map((t) => (
                    <button
                      key={t.value}
                      onClick={() => useSettingsStore.getState().setTheme(t.value as 'light' | 'dark' | 'system')}
                      className={cn(
                        'relative p-6 rounded-xl border-2 transition-all',
                        theme === t.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-secondary-200 hover:border-secondary-300'
                      )}
                    >
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <span className="text-2xl">{t.icon}</span>
                      </div>
                      <p className="font-medium text-secondary-900">{t.label}</p>
                      {theme === t.value && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Layout</CardTitle>
                <CardDescription>Customize your workspace layout</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-secondary-900">Collapsed Sidebar</p>
                    <p className="text-sm text-secondary-500">Show only icons in the sidebar</p>
                  </div>
                  <button
                    onClick={() => useSettingsStore.getState().toggleSidebar}
                    className={cn(
                      'relative w-12 h-7 rounded-full transition-colors',
                      sidebarCollapsed ? 'bg-primary-600' : 'bg-secondary-300'
                    )}
                    role="switch"
                    aria-checked={sidebarCollapsed}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                        sidebarCollapsed ? 'translate-x-6' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-secondary-900">Compact Mode</p>
                    <p className="text-sm text-secondary-500">Reduce padding and spacing</p>
                  </div>
                  <button
                    onClick={() => useSettingsStore.getState().setCompactMode(!compactMode)}
                    className={cn(
                      'relative w-12 h-7 rounded-full transition-colors',
                      compactMode ? 'bg-primary-600' : 'bg-secondary-300'
                    )}
                    role="switch"
                    aria-checked={compactMode}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                        compactMode ? 'translate-x-6' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Language</CardTitle>
                <CardDescription>Choose your preferred language</CardDescription>
              </CardHeader>
              <CardContent>
                <select
                  value={language}
                  onChange={(e) => useSettingsStore.getState().setLanguage(e.target.value)}
                  className="w-full max-w-md px-4 py-2.5 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="ja">Japanese</option>
                  <option value="zh">Chinese</option>
                </select>
              </CardContent>
            </Card>
          </div>
        )

      case 'notifications':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Choose what notifications you receive</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-secondary-900">Enable Notifications</p>
                    <p className="text-sm text-secondary-500">Receive push notifications for important updates</p>
                  </div>
                  <button
                    onClick={() => useSettingsStore.getState().setNotificationsEnabled(!notificationsEnabled)}
                    className={cn(
                      'relative w-12 h-7 rounded-full transition-colors',
                      notificationsEnabled ? 'bg-primary-600' : 'bg-secondary-300'
                    )}
                    role="switch"
                    aria-checked={notificationsEnabled}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                        notificationsEnabled ? 'translate-x-6' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'chat':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Chat Settings</CardTitle>
                <CardDescription>Configure chat behavior</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-secondary-900">Streaming Responses</p>
                    <p className="text-sm text-secondary-500">Stream AI responses in real-time</p>
                  </div>
                  <button
                    onClick={() => useSettingsStore.getState().setStreamingEnabled(!streamingEnabled)}
                    className={cn(
                      'relative w-12 h-7 rounded-full transition-colors',
                      streamingEnabled ? 'bg-primary-600' : 'bg-secondary-300'
                    )}
                    role="switch"
                    aria-checked={streamingEnabled}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                        streamingEnabled ? 'translate-x-6' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-secondary-900">Show Citations</p>
                    <p className="text-sm text-secondary-500">Display source citations in responses</p>
                  </div>
                  <button
                    onClick={() => useSettingsStore.getState().setCitationsEnabled(!citationsEnabled)}
                    className={cn(
                      'relative w-12 h-7 rounded-full transition-colors',
                      citationsEnabled ? 'bg-primary-600' : 'bg-secondary-300'
                    )}
                    role="switch"
                    aria-checked={citationsEnabled}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
                        citationsEnabled ? 'translate-x-6' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'security':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Security Settings</CardTitle>
                <CardDescription>Manage your account security</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button variant="outline" className="w-full justify-start">
                  <Shield className="h-4 w-4 mr-2" />
                  Enable Two-Factor Authentication
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Key className="h-4 w-4 mr-2" />
                  Manage API Keys
                </Button>
                <Button variant="outline" className="w-full justify-start text-red-600 hover:text-red-700 border-red-200 hover:border-red-300">
                  <LogOut className="h-4 w-4 mr-2" />
                  Revoke All Sessions
                </Button>
              </CardContent>
            </Card>
          </div>
        )

      case 'data':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Management</CardTitle>
                <CardDescription>Export or delete your data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button variant="outline" className="w-full justify-start">
                  <Download className="h-4 w-4 mr-2" />
                  Export My Data
                </Button>
                <Button variant="outline" className="w-full justify-start text-red-600 hover:text-red-700 border-red-200 hover:border-red-300">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete My Account
                </Button>
              </CardContent>
            </Card>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Settings</h1>
          <p className="text-secondary-600 mt-1">Manage your account and preferences</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar Navigation */}
        <aside className="lg:col-span-1">
          <Card>
            <CardContent className="p-2">
              <nav className="space-y-1" aria-label="Settings navigation">
                {settingsSections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
                      activeSection === section.id
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                    )}
                  >
                    <section.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                    <span>{section.label}</span>
                  </button>
                ))}
              </nav>
            </CardContent>
          </Card>
        </aside>

        {/* Main Content */}
        <div className="lg:col-span-3">
          {renderSection()}
        </div>
      </div>
    </div>
  )
}