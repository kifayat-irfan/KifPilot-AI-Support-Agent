import { Link } from 'react-router-dom'
import { RegisterForm } from '@/components/auth/RegisterForm'
import { AuthPageLayout } from '@/components/auth/AuthLayout'

export function RegisterPage() {
  return (
    <AuthPageLayout
      title="Create an account"
      description="Join KifPilot AI Support Agent"
      footer={
        <p className="text-center text-sm text-secondary-600">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
            Sign in
          </Link>
        </p>
      }
    >
      <RegisterForm />
    </AuthPageLayout>
  )
}

export default RegisterPage