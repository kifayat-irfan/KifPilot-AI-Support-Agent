import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'
import { PasswordInput } from './PasswordInput'
import { Input } from '@/components/ui/Input'
import { User, AlertCircle } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/services/auth'
import toast from 'react-hot-toast'

const loginSchema = z.object({
  username: z.string().min(1, 'Username or email is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSuccess?: () => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [showPassword, setShowPassword] = useState(false)
  const { setTokens, setUser, setLoading } = useAuthStore()
  const navigate = useNavigate()
  const isLoading = useAuthStore((s) => s.isLoading)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      rememberMe: false,
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      setLoading(true)
      const tokens = await authApi.login({
        username: data.username,
        password: data.password,
      })
      setTokens(tokens.access_token, tokens.refresh_token)

      const user = await authApi.getMe()
      setUser(user)

      toast.success('Welcome back!')

      if (onSuccess) {
        onSuccess()
      } else {
        navigate('/dashboard')
      }
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } } }
      toast.error(axiosError.response?.data?.error || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="relative">
        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" aria-hidden="true" />
        <Input
          {...register('username')}
          type="text"
          placeholder="Username or email"
          error={errors.username?.message}
          className="pl-10"
          autoComplete="username"
        />
      </div>

      <PasswordInput
        {...register('password')}
        placeholder="Password"
        error={errors.password?.message}
        autoComplete="current-password"
      />

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            {...register('rememberMe')}
            className="w-4 h-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-secondary-600">Remember me</span>
        </label>
        <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
          Forgot password?
        </Link>
      </div>

      {errors.form && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <span>{errors.form.message}</span>
        </div>
      )}

      <Button type="submit" className="w-full" size="lg" loading={isLoading}>
        Sign in
      </Button>
    </form>
  )
}

export default LoginForm