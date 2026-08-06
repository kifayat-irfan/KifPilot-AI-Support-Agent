import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/utils/cn'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { RefreshCw, LayoutDashboard, Building2, Users, BarChart3, Bell, Plus } from 'lucide-react'
import { adminApi, type AdminStats, type SystemHealth, type TimeSeriesData, type AdminActivity, type AdminNotification } from '@/services/admin'
import {
  OverviewCards,
  SystemHealthPanel,
  ChartsGrid,
  RecentActivityPanel,
  QuickActionsPanel,
  NotificationsPanel,
  OrganizationsTable,
  UsersTable,
} from '@/features/admin/components'
import toast from 'react-hot-toast'

export function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesData | null>(null)
  const [activities, setActivities] = useState<AdminActivity[]>([])
  const [notifications, setNotifications] = useState<AdminNotification[]>([])
  
  const [statsLoading, setStatsLoading] = useState(true)
  const [healthLoading, setHealthLoading] = useState(true)
  const [chartsLoading, setChartsLoading] = useState(true)
  const [activitiesLoading, setActivitiesLoading] = useState(true)
  const [notificationsLoading, setNotificationsLoading] = useState(true)
  
  const [activeTab, setActiveTab] = useState<string>('overview')

  const loadAllData = useCallback(async () => {
    await Promise.all([
      loadStats(),
      loadHealth(),
      loadTimeSeriesData(),
      loadActivities(),
      loadNotifications(),
    ])
  }, [])

  const loadStats = async () => {
    setStatsLoading(true)
    try {
      const data = await adminApi.getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
      toast.error('Failed to load statistics')
    } finally {
      setStatsLoading(false)
    }
  }

  const loadHealth = async () => {
    setHealthLoading(true)
    try {
      const data = await adminApi.getSystemHealth()
      setHealth(data)
    } catch (error) {
      console.error('Failed to load health:', error)
    } finally {
      setHealthLoading(false)
    }
  }

  const loadTimeSeriesData = async () => {
    setChartsLoading(true)
    try {
      const data = await adminApi.getTimeSeriesData(30)
      setTimeSeriesData(data)
    } catch (error) {
      console.error('Failed to load chart data:', error)
    } finally {
      setChartsLoading(false)
    }
  }

  const loadActivities = async () => {
    setActivitiesLoading(true)
    try {
      const response = await adminApi.getActivity({ page: 1, page_size: 50 })
      setActivities(response.items)
    } catch (error) {
      console.error('Failed to load activities:', error)
    } finally {
      setActivitiesLoading(false)
    }
  }

  const loadNotifications = async () => {
    setNotificationsLoading(true)
    try {
      const data = await adminApi.getNotifications()
      setNotifications(data)
    } catch (error) {
      console.error('Failed to load notifications:', error)
    } finally {
      setNotificationsLoading(false)
    }
  }

  const handleRefresh = useCallback(() => {
    loadAllData()
    toast.success('Data refreshed')
  }, [loadAllData])

  const handleMarkNotificationRead = async (id: string) => {
    try {
      await adminApi.markNotificationRead(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  const handleMarkAllNotificationsRead = async () => {
    try {
      await adminApi.markAllNotificationsRead()
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error)
    }
  }

  // Load data on mount
  useEffect(() => {
    loadAllData()
  }, [loadAllData])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Admin Dashboard</h1>
          <p className="text-secondary-600 mt-1">System overview and management</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRefresh} loading={statsLoading || healthLoading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Loading State */}
      {(statsLoading || healthLoading) && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 animate-pulse">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="p-6 rounded-xl border">
              <div className="h-4 bg-secondary-200 rounded w-3/4 mb-2" />
              <div className="h-8 bg-secondary-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Overview Cards */}
      {stats && (
        <OverviewCards stats={stats} loading={statsLoading} />
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">
            <LayoutDashboard className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <BarChart3 className="h-4 w-4 mr-2" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="organizations">
            <Building2 className="h-4 w-4 mr-2" />
            Organizations
          </TabsTrigger>
          <TabsTrigger value="users">
            <Users className="h-4 w-4 mr-2" />
            Users
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left Column - System Health & Quick Actions */}
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>System Health</CardTitle>
                  <Button variant="ghost" size="sm" onClick={loadHealth} loading={healthLoading}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent>
                  <SystemHealthPanel health={health} loading={healthLoading} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Quick Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <QuickActionsPanel />
                </CardContent>
              </Card>
            </div>

            {/* Right Column - Notifications & Activity */}
            <div className="space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Notifications</CardTitle>
                  <Button variant="ghost" size="sm" onClick={loadNotifications} loading={notificationsLoading}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent>
                  <NotificationsPanel
                    notifications={notifications}
                    loading={notificationsLoading}
                    onMarkRead={handleMarkNotificationRead}
                    onMarkAllRead={handleMarkAllNotificationsRead}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Recent Activity</CardTitle>
                  <Button variant="ghost" size="sm" onClick={loadActivities} loading={activitiesLoading}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent>
                  <RecentActivityPanel
                    activities={activities}
                    loading={activitiesLoading}
                  />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Analytics Charts</CardTitle>
              <CardDescription>System metrics over the last 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartsGrid data={timeSeriesData!} loading={chartsLoading} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Organizations Tab */}
        <TabsContent value="organizations">
          <OrganizationsTable onRefresh={loadStats} />
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users">
          <UsersTable onRefresh={loadStats} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AdminDashboardPage