import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Mail, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react'

const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

export function ForgotPasswordPage() {
  const [step, setStep] = useState<'email' | 'success'>('email')
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  const onSubmit = async (data: ForgotPasswordForm) => {
    try {
      setIsLoading(true)
      await new Promise((resolve) => setTimeout(resolve, 1000))
      setStep('success')
      toast.success('Password reset email sent!')
    } catch {
      toast.error('Failed to send reset email. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (step === 'success') {
    return (
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-green-100 mb-6">
            <CheckCircle className="h-8 w-8 text-green-600" aria-hidden="true" />
          </div>
          <h1 className="text-3xl font-bold text-secondary-900">Check your email</h1>
          <p className="mt-2 text-secondary-600">
            We've sent password reset instructions to your email address.
          </p>
        </div>

        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <p className="text-secondary-600 text-center">
                If you don't see the email within a few minutes, check your spam folder.
              </p>
              <Button variant="primary" className="w-full" size="lg" onClick={() => navigate('/login')}>
                Back to sign in
              </Button>
              <Button variant="ghost" className="w-full" onClick={() => { setStep('email'); reset(); }}>
                Resend email
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <Button variant="ghost" size="sm" className="absolute left-0 top-0" onClick={() => navigate('/login')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-600 mb-6">
          <span className="text-2xl font-bold text-white">K</span>
        </div>
        <h1 className="text-3xl font-bold text-secondary-900">Forgot password?</h1>
        <p className="mt-2 text-secondary-600">Enter your email and we'll send you reset instructions</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reset password</CardTitle>
          <CardDescription>Enter your email address to receive a password reset link</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" aria-hidden="true" />
              <Input
                {...register('email')}
                type="email"
                placeholder="Email address"
                error={errors.email?.message}
                className="pl-10"
                autoComplete="email"
              />
            </div>

            {errors.form && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                <AlertCircle className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                <span>{errors.form.message}</span>
              </div>
            )}

            <Button type="submit" className="w-full" size="lg" loading={isLoading}>
              Send reset link
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col items-center gap-3 border-t-0 pt-0">
          <p className="text-sm text-secondary-600">
            Remember your password?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

export default ForgotPasswordPage