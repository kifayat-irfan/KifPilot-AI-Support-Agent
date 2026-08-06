import { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface BadgeProps {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline'
  size?: 'sm' | 'md'
  className?: string
  dot?: boolean
  dotColor?: string
}

export function Badge({
  children,
  variant = 'secondary',
  size = 'md',
  className,
  dot,
  dotColor,
}: BadgeProps) {
  const variants = {
    primary: 'bg-primary-100 text-primary-700',
    secondary: 'bg-secondary-100 text-secondary-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    destructive: 'bg-red-100 text-red-700',
    outline: 'border border-secondary-300 bg-transparent text-secondary-700',
  }

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: dotColor || 'currentColor' }}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
    completed: 'success',
    processing: 'primary',
    uploading: 'primary',
    parsing: 'primary',
    chunking: 'primary',
    embedding: 'primary',
    storing: 'primary',
    failed: 'destructive',
    pending: 'warning',
    active: 'success',
    inactive: 'secondary',
    draft: 'secondary',
    published: 'success',
    archived: 'secondary',
  }

  return (
    <Badge variant={variants[status] || 'secondary'} size="sm">
      {status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ')}
    </Badge>
  )
}

export function RoleBadge({ role }: { role: string }) {
  const variants: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
    owner: 'destructive',
    admin: 'warning',
    member: 'primary',
    viewer: 'secondary',
    editor: 'primary',
    manager: 'warning',
  }

  return (
    <Badge variant={variants[role] || 'secondary'} size="sm">
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </Badge>
  )
}