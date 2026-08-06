import { useState } from 'react'
import { User, Bell, Shield, Palette, Globe, Save, Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'notifications' | 'security' | 'appearance'>('general')
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    name: 'John Doe',
    email: 'john@example.com',
    language: 'en',
    timezone: 'UTC',
    emailNotifications: true,
    pushNotifications: false,
    weeklyDigest: true,
    twoFactorEnabled: false,
    theme: 'system' as 'light' | 'dark' | 'system',
    compactMode: false,
  })

  const tabs = [
    { id: 'general', label: 'General', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'appearance', label: 'Appearance', icon: Palette },
  ]

  const handleSave = async () => {
    setSaving(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaving(false)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-secondary-900">Settings</h2>
        <p className="text-secondary-500 mt-1">Manage your account and preferences</p>
      </div>

      <div className="card">
        <div className="border-b border-secondary-200">
          <nav className="flex gap-1 p-1" aria-label="Settings tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all',
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'general' && <GeneralSettings settings={settings} setSettings={setSettings} />}
          {activeTab === 'notifications' && <NotificationSettings settings={settings} setSettings={setSettings} />}
          {activeTab === 'security' && <SecuritySettings settings={settings} setSettings={setSettings} />}
          {activeTab === 'appearance' && <AppearanceSettings settings={settings} setSettings={setSettings} />}

          <div className="flex justify-end pt-6 border-t border-secondary-200 mt-6">
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function GeneralSettings({ settings, setSettings }: { settings: any; setSettings: any }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-secondary-900">Profile Information</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Full Name</label>
          <input
            type="text"
            value={settings.name}
            onChange={(e) => setSettings({ ...settings, name: e.target.value })}
            className="input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Email</label>
          <input
            type="email"
            value={settings.email}
            onChange={(e) => setSettings({ ...settings, email: e.target.value })}
            className="input"
          />
        </div>
      </div>

      <h3 className="text-lg font-semibold text-secondary-900 mt-8">Preferences</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Language</label>
          <select
            value={settings.language}
            onChange={(e) => setSettings({ ...settings, language: e.target.value })}
            className="input"
          >
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Timezone</label>
          <select
            value={settings.timezone}
            onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            className="input"
          >
            <option value="UTC">UTC</option>
            <option value="America/New_York">Eastern Time</option>
            <option value="America/Chicago">Central Time</option>
            <option value="America/Denver">Mountain Time</option>
            <option value="America/Los_Angeles">Pacific Time</option>
            <option value="Europe/London">London</option>
            <option value="Europe/Paris">Paris</option>
            <option value="Asia/Tokyo">Tokyo</option>
          </select>
        </div>
      </div>
    </div>
  )
}

function NotificationSettings({ settings, setSettings }: { settings: any; setSettings: any }) {
  const toggle = (key: string) => setSettings({ ...settings, [key]: !settings[key] })

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-secondary-900">Email Notifications</h3>
      <div className="space-y-4">
        <SettingToggle
          label="Email Notifications"
          description="Receive email notifications for important updates"
          checked={settings.emailNotifications}
          onChange={() => toggle('emailNotifications')}
        />
        <SettingToggle
          label="Weekly Digest"
          description="Get a weekly summary of activity"
          checked={settings.weeklyDigest}
          onChange={() => toggle('weeklyDigest')}
        />
      </div>

      <h3 className="text-lg font-semibold text-secondary-900 mt-8">Push Notifications</h3>
      <div className="space-y-4">
        <SettingToggle
          label="Push Notifications"
          description="Receive browser push notifications"
          checked={settings.pushNotifications}
          onChange={() => toggle('pushNotifications')}
        />
      </div>
    </div>
  )
}

function SecuritySettings({ settings, setSettings }: { settings: any; setSettings: any }) {
  const toggle = (key: string) => setSettings({ ...settings, [key]: !settings[key] })

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-secondary-900">Two-Factor Authentication</h3>
      <SettingToggle
        label="Enable 2FA"
        description="Add an extra layer of security to your account"
        checked={settings.twoFactorEnabled}
        onChange={() => toggle('twoFactorEnabled')}
      />
      {settings.twoFactorEnabled && (
        <div className="ml-10 space-y-3">
          <button className="btn-secondary text-sm">View Backup Codes</button>
          <button className="btn-secondary text-sm text-red-600 hover:bg-red-50">Disable 2FA</button>
        </div>
      )}

      <h3 className="text-lg font-semibold text-secondary-900 mt-8">Password</h3>
      <div className="space-y-3">
        <button className="btn-secondary">Change Password</button>
      </div>

      <h3 className="text-lg font-semibold text-secondary-900 mt-8">Active Sessions</h3>
      <div className="space-y-3">
        <div className="p-4 bg-secondary-50 rounded-lg flex items-center justify-between">
          <div>
            <p className="font-medium text-secondary-900">Current Session</p>
            <p className="text-sm text-secondary-500">Chrome on Windows • Active now</p>
          </div>
          <span className="badge badge-success">Current</span>
        </div>
      </div>
    </div>
  )
}

function AppearanceSettings({ settings, setSettings }: { settings: any; setSettings: any }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-secondary-900">Theme</h3>
      <div className="grid gap-4 sm:grid-cols-3">
        {['light', 'dark', 'system'].map((theme) => (
          <button
            key={theme}
            onClick={() => setSettings({ ...settings, theme: theme as any })}
            className={cn(
              'p-4 rounded-xl border-2 transition-all text-left',
              settings.theme === theme
                ? 'border-primary-500 bg-primary-50'
                : 'border-secondary-200 hover:border-secondary-300'
            )}
          >
            <div className="font-medium text-secondary-900 capitalize">{theme}</div>
            <div className="text-sm text-secondary-500 mt-1">
              {theme === 'light' && 'Always use light mode'}
              {theme === 'dark' && 'Always use dark mode'}
              {theme === 'system' && 'Match system preference'}
            </div>
          </button>
        ))}
      </div>

      <h3 className="text-lg font-semibold text-secondary-900 mt-8">Layout</h3>
      <SettingToggle
        label="Compact Mode"
        description="Reduce spacing for a denser interface"
        checked={settings.compactMode}
        onChange={() => setSettings({ ...settings, compactMode: !settings.compactMode })}
      />
    </div>
  )
}

function SettingToggle({ label, description, checked, onChange }: {
  label: string
  description: string
  checked: boolean
  onChange: () => void
}) {
  return (
    <label className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg cursor-pointer hover:bg-secondary-100 transition-colors">
      <div>
        <p className="font-medium text-secondary-900">{label}</p>
        <p className="text-sm text-secondary-500">{description}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
          checked ? 'bg-primary-600' : 'bg-secondary-300'
        )}
        role="switch"
        aria-checked={checked}
        aria-label={label}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </button>
    </label>
  )
}