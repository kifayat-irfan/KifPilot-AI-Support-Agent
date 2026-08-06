import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Loader } from '@/components/ui/Loader'
import { Building2, MessageSquare, Database, FileText, Users, Settings, TrendingUp } from 'lucide-react'

const stats = [
  { name: 'Total Organizations', value: '3', icon: Building2, color: 'text-blue-600', bg: 'bg-blue-100' },
  { name: 'Active Chats', value: '12', icon: MessageSquare, color: 'text-green-600', bg: 'bg-green-100' },
  { name: 'Documents', value: '1,234', icon: FileText, color: 'text-purple-600', bg: 'bg-purple-100' },
  { name: 'Team Members', value: '8', icon: Users, color: 'text-orange-600', bg: 'bg-orange-100' },
]

const recentActivity = [
  { action: 'New document uploaded', resource: 'API Documentation.pdf', time: '2 minutes ago' },
  { action: 'Chat session created', resource: 'Support Query #452', time: '15 minutes ago' },
  { action: 'Member added to organization', resource: 'John Doe', time: '1 hour ago' },
  { action: 'Settings updated', resource: 'RAG Configuration', time: '3 hours ago' },
]

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Dashboard</h1>
          <p className="text-secondary-600 mt-1">Overview of your KifPilot workspace</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name} hover>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">{stat.name}</p>
                  <p className="text-3xl font-bold text-secondary-900 mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-xl ${stat.bg}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} aria-hidden="true" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions & Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest actions across your workspace</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-center gap-4 p-3 bg-secondary-50 rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                      <TrendingUp className="h-5 w-5 text-primary-600" aria-hidden="true" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-secondary-900">{activity.action}</p>
                      <p className="text-sm text-secondary-500">{activity.resource}</p>
                    </div>
                    <span className="text-xs text-secondary-400 whitespace-nowrap">{activity.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Common tasks and shortcuts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-colors text-left">
                  <MessageSquare className="h-5 w-5 text-primary-600" aria-hidden="true" />
                  <span className="font-medium text-secondary-900">Start New Chat</span>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-colors text-left">
                  <FileText className="h-5 w-5 text-primary-600" aria-hidden="true" />
                  <span className="font-medium text-secondary-900">Upload Document</span>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-colors text-left">
                  <Database className="h-5 w-5 text-primary-600" aria-hidden="true" />
                  <span className="font-medium text-secondary-900">Search Knowledge Base</span>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-colors text-left">
                  <Settings className="h-5 w-5 text-primary-600" aria-hidden="true" />
                  <span className="font-medium text-secondary-900">Manage Organization</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}