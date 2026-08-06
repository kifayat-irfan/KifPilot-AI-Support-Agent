import { ReactNode } from 'react'
import { Outlet } from 'react-router-dom'

interface AuthLayoutProps {
  children?: ReactNode
  title?: string
  description?: string
  showBackLink?: boolean
  backLink?: string
}

export function AuthLayout({
  children,
  title = 'KifPilot',
  description = 'AI Support Agent',
  showBackLink = false,
  backLink = '/login',
}: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-secondary-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-600 mb-6 mx-auto">
            <span className="text-2xl font-bold text-white">K</span>
          </div>
          <h1 className="text-3xl font-bold text-secondary-900">{title}</h1>
          <p className="mt-2 text-secondary-600">{description}</p>
        </div>
        {showBackLink && (
          <div className="mb-6">
            <a href={backLink} className="inline-flex items-center gap-1 text-sm text-secondary-500 hover:text-secondary-700 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </a>
          </div>
        )}
        <div className="bg-white rounded-xl border border-secondary-200 shadow-sm p-6 sm:p-8">
          {children}
        </div>
      </div>
    </div>
  )
}

export function AuthPageLayout({
  children,
  title,
  description,
  showBackLink = false,
  backLink = '/login',
  footer,
}: {
  children: ReactNode
  title: string
  description: string
  showBackLink?: boolean
  backLink?: string
  footer?: ReactNode
}) {
  return (
    <AuthLayout title={title} description={description} showBackLink={showBackLink} backLink={backLink}>
      {children}
      {footer && (
        <div className="mt-6 border-t border-secondary-200 pt-6">
          {footer}
        </div>
      )}
    </AuthLayout>
  )
}

export default AuthLayout