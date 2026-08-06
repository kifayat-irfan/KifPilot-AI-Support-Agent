import { Link } from 'react-router-dom'
import { LoginForm } from '@/components/auth/LoginForm'
import { AuthPageLayout } from '@/components/auth/AuthLayout'

export function LoginPage() {
  return (
    <AuthPageLayout
      title="Welcome back"
      description="Sign in to your KifPilot account"
      footer={
        <p className="text-center text-sm text-secondary-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600 hover:text-primary-700 font-medium">
            Sign up
          </Link>
        </p>
      }
    >
      <LoginForm />
    </AuthPageLayout>
  )
}

export default LoginPage