import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Home, Search, RotateCcw } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 px-4">
      <div className="text-center">
        <div className="mb-8">
          <span className="text-9xl font-bold text-secondary-200">404</span>
        </div>
        <h1 className="text-3xl font-bold text-secondary-900 mb-4">Page Not Found</h1>
        <p className="text-secondary-600 text-lg mb-8 max-w-md mx-auto">
          Sorry, we couldn't find the page you're looking for. It might have been moved or doesn't exist.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button onClick={() => window.history.back()}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Go Back
          </Button>
          <Button variant="outline" asChild>
            <Link to="/dashboard">
              <Home className="h-4 w-4 mr-2" />
              Dashboard
            </Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link to="/search">
              <Search className="h-4 w-4 mr-2" />
              Search
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}