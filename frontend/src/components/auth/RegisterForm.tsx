import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { PasswordInput } from './PasswordInput'
import { Input } from '@/components/ui/Input'
import { Mail, AlertCircle } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/services/auth'
import toast from 'react-hot-toast'

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  username: z.string().min(3, 'Username must be at least 3 characters').max(100),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

type RegisterFormData = z.infer<typeof registerSchema>

interface RegisterFormProps {
  onSuccess?: () => void
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { setTokens, setUser, setLoading } = useAuthStore()
  const navigate = useNavigate()
  const isLoading = useAuthStore((s) => s.isLoading)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const password = watch('password', '')

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setLoading(true)
      const user = await authApi.register({
        email: data.email,
        username: data.username,
        password: data.password,
      })

      const tokens = await authApi.login({ username: data.username, password: data.password })
      setTokens(tokens.access_token, tokens.refresh_token)
      setUser(user)

      toast.success('Account created successfully!')

      if (onSuccess) {
        onSuccess()
      } else {
        navigate('/dashboard')
      }
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        {...register('email')}
        type="email"
        placeholder="Email address"
        label="Email"
        error={errors.email?.message}
        autoComplete="email"
      />

      <Input
        {...register('username')}
        type="text"
        placeholder="Username"
        label="Username"
        error={errors.username?.message}
        autoComplete="username"
      />

      <PasswordInput
        {...register('password')}
        placeholder="Password (min 8 characters)"
        label="Password"
        error={errors.password?.message}
        autoComplete="new-password"
      />

      <PasswordInput
        {...register('confirmPassword')}
        placeholder="Confirm password"
        label="Confirm Password"
        error={errors.confirmPassword?.message}
        autoComplete="new-password"
      />

      {/* Password strength indicator */}
      <div className="space-y-1">
        <div className="flex gap-1" role="progressbar" aria-valuenow={password.length >= 8 ? 100 : password.length * 12} aria-valuemin={0} aria-valuemax={100} aria-label="Password strength">
          <div className={`h-1.5 flex-1 rounded transition-colors ${password.length >= 8 ? 'bg-green-500' : password.length > 0 ? 'bg-yellow-500' : 'bg-secondary-200'}`} />
          <div className={`h-1.5 flex-1 rounded transition-colors ${password.length >= 10 ? 'bg-green-500' : password.length > 5 ? 'bg-yellow-500' : 'bg-secondary-200'}`} />
          <div className={`h-1.5 flex-1 rounded transition-colors ${password.length >= 12 ? 'bg-green-500' : password.length > 8 ? 'bg-yellow-500' : 'bg-secondary-200'}`} />
          <div className={`h-1.5 flex-1 rounded transition-colors ${password.length >= 16 ? 'bg-green-500' : password.length > 10 ? 'bg-yellow-500' : 'bg-secondary-200'}`} />
        </div>
        <p className="text-xs text-secondary-500">
          {password.length === 0 ? 'Enter a password' : password.length < 8 ? 'Too short' : password.length < 10 ? 'Weak' : password.length < 12 ? 'Fair' : 'Strong'}
        </p>
      </div>

      {errors.form && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <span>{errors.form.message}</span>
        </div>
      )}

      <Button type="submit" className="w-full" size="lg" loading={isLoading}>
        Create account
      </Button>
    </form>
  )
}

export default RegisterForm