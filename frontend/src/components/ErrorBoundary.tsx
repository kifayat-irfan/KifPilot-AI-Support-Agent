import { Component, ErrorInfo, ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error)
    console.error('Component stack:', errorInfo.componentStack)
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-secondary-50 px-4">
          <Card className="w-full max-w-md">
            <CardContent className="pt-6 pb-8 px-6 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-8 w-8 text-red-600" aria-hidden="true" />
              </div>
              <h1 className="text-2xl font-bold text-secondary-900 mb-2">Something went wrong</h1>
              <p className="text-secondary-600 mb-6">
                We encountered an unexpected error. Our team has been notified.
              </p>

              {this.state.error && import.meta.env.DEV && (
                <details className="mb-6 text-left">
                  <summary className="cursor-pointer text-sm text-secondary-500">
                    Error Details (Development)
                  </summary>
                  <pre className="mt-2 p-3 bg-secondary-100 rounded text-xs overflow-auto text-secondary-700">
                    {this.state.error?.message}
                    {this.state.error?.stack}
                  </pre>
                </details>
              )}

              <div className="flex flex-col sm:flex-row gap-3">
                <Button onClick={this.handleRetry} className="w-full sm:w-auto">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
                <Button variant="outline" className="w-full sm:w-auto">
                  <Link to="/dashboard">
                    <Home className="h-4 w-4 mr-2" />
                    Go to Dashboard
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}