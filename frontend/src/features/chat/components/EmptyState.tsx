import { Bot, MessageSquare, Sparkles, ArrowRight, HelpCircle, FileText, Lightbulb, Search, AlertCircle, Loader2, Shield, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'

interface EmptyStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  variant?: 'welcome' | 'no-results' | 'error' | 'loading'
  className?: string
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  variant = 'welcome',
  className,
}: EmptyStateProps) {
  const configs = {
    welcome: {
      icon: Bot,
      defaultTitle: 'Welcome to KifPilot AI Assistant',
      defaultDescription: 'Start a conversation by typing a message below. I\'m here to help with any questions you have about our products and services.',
      actionLabel: 'New Conversation',
    },
    'no-results': {
      icon: Search,
      defaultTitle: 'No conversations found',
      defaultDescription: 'Try adjusting your search terms or create a new conversation.',
      actionLabel: 'New Conversation',
    },
    error: {
      icon: AlertCircle,
      defaultTitle: 'Something went wrong',
      defaultDescription: 'We encountered an unexpected error. Please try again or contact support.',
      actionLabel: 'Try Again',
    },
    loading: {
      icon: Loader2,
      defaultTitle: 'Loading...',
      defaultDescription: 'Please wait while we load your conversations.',
      actionLabel: '',
    },
  }

  const config = configs[variant]
  const Icon = config.icon

  return (
    <div className={cn('flex-1 flex items-center justify-center px-6 py-12', className)}>
      <div className="text-center max-w-md">
        <div className={cn(
          'inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-6',
          variant === 'error' && 'bg-red-100 text-red-600',
          variant === 'loading' && 'bg-primary-100 text-primary-600',
          variant === 'welcome' && 'bg-primary-100 text-primary-600',
          variant === 'no-results' && 'bg-secondary-100 text-secondary-600'
        )}>
          <Icon className="w-10 h-10" aria-hidden="true" />
        </div>
        
        <h2 className="text-2xl font-bold text-secondary-900 mb-2">
          {title || config.defaultTitle}
        </h2>
        
        <p className="text-secondary-600 mb-6 max-w-sm mx-auto">
          {description || config.defaultDescription}
        </p>
        
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {actionLabel}
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}

export function WelcomeEmptyState({ onNewChat }: { onNewChat: (query: string) => void }) {
  const suggestions = [
    { label: 'How do I reset my password?', query: 'How do I reset my password?' },
    { label: 'What are the pricing plans?', query: 'What are the pricing plans?' },
    { label: 'How to integrate the API?', query: 'How to integrate the API?' },
    { label: 'Troubleshoot login issues', query: 'Troubleshoot login issues' },
  ]

  return (
    <div className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="text-center max-w-2xl">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary-100 text-primary-600 mb-6">
          <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        
        <h1 className="text-3xl font-bold text-secondary-900 mb-2">Welcome to KifPilot</h1>
        <p className="text-secondary-600 text-lg mb-8 max-w-md mx-auto">
          I'm your AI support assistant. Ask me anything about our products, services, or documentation.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 max-w-md mx-auto mb-8">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => onNewChat(suggestion.query)}
              className="p-4 rounded-xl border border-secondary-200 hover:border-primary-300 hover:bg-primary-50 transition-all text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg text-primary-600 group-hover:bg-primary-200 transition-colors">
                  <Sparkles className="w-5 h-5" />
                </div>
                <span className="font-medium text-secondary-900 group-hover:text-primary-600 transition-colors">
                  {suggestion.label}
                </span>
              </div>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-center gap-4 text-sm text-secondary-500">
          <div className="flex items-center gap-1.5">
            <Shield className="w-4 h-4" />
            <span>Your data is private</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="w-4 h-4" />
            <span>Powered by AI</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function NoConversationsState({ onNewChat }: { onNewChat: () => void }) {
  return (
    <EmptyState
      variant="welcome"
      title="No conversations yet"
      description="Start your first conversation with KifPilot AI Assistant"
      actionLabel="Start New Chat"
      onAction={onNewChat}
    />
  )
}

export function NoSearchResultsState({ onClearSearch }: { onClearSearch: () => void }) {
  return (
    <EmptyState
      variant="no-results"
      title="No matching conversations"
      description="Try adjusting your search terms or create a new conversation"
      actionLabel="Clear Search"
      onAction={onClearSearch}
    />
  )
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      variant="error"
      title="Something went wrong"
      description="We encountered an unexpected error. Please try again."
      actionLabel="Try Again"
      onAction={onRetry}
    />
  )
}