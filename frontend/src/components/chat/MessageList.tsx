import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown, Flag, ChevronDown, ChevronUp, FileText } from 'lucide-react'
import { cn } from '@/utils/cn'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: Source[]
  feedback?: 'positive' | 'negative'
}

interface Source {
  id: string
  content: string
  score: number
  documentName: string
}

interface MessageListProps {
  messages: Message[]
  onFeedback: (messageId: string, feedback: 'positive' | 'negative') => void
  onCopy: (content: string) => void
  messagesEndRef: React.RefObject<HTMLDivElement | null>
  isLoading: boolean
}

export function MessageList({ messages, onFeedback, onCopy, messagesEndRef, isLoading }: MessageListProps) {
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set())

  const toggleSources = (messageId: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center p-8">
          <Bot className="w-16 h-16 text-secondary-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-secondary-900">Welcome to KifPilot</h3>
          <p className="text-secondary-500 mt-2 max-w-xs mx-auto">
            Start a conversation by typing a message below. I'm here to help with any questions you have.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-6 pb-4">
        {messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            onFeedback={onFeedback}
            onCopy={onCopy}
            expandedSources={expandedSources}
            onToggleSources={toggleSources}
          />
        ))}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-primary-600" />
            </div>
            <div className="flex-1 max-w-3xl">
              <div className="bg-secondary-100 rounded-2xl p-4 animate-pulse">
                <div className="h-4 bg-secondary-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-secondary-200 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

function MessageItem({ message, onFeedback, onCopy, expandedSources, onToggleSources }: {
  message: Message
  onFeedback: (messageId: string, feedback: 'positive' | 'negative') => void
  onCopy: (content: string) => void
  expandedSources: Set<string>
  onToggleSources: (messageId: string) => void
}) {
  const isAssistant = message.role === 'assistant'
  const isExpanded = expandedSources.has(message.id)
  const hasSources = message.sources && message.sources.length > 0

  return (
    <div className={cn('flex gap-3', isAssistant ? '' : 'flex-row-reverse')}>
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isAssistant ? 'bg-primary-100' : 'bg-secondary-100'
        )}
      >
        {isAssistant ? (
          <Bot className="w-5 h-5 text-primary-600" />
        ) : (
          <User className="w-5 h-5 text-secondary-600" />
        )}
      </div>
      <div className={cn('flex-1 max-w-3xl', isAssistant ? '' : 'text-right')}>
        <div
          className={cn(
            'relative rounded-2xl px-4 py-3',
            isAssistant
              ? 'bg-white text-secondary-900 shadow-sm border border-secondary-200'
              : 'bg-primary-600 text-white'
          )}
        >
          <div className="prose prose-sm max-w-none dark:prose-invert">
            {message.content}
          </div>
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-current/10">
            <span className="text-xs text-current/60">
              {formatDistanceToNow(message.timestamp, { addSuffix: true })}
            </span>
            <span className="w-px h-4 bg-current/10 mx-1" />
            <button
              onClick={() => onCopy(message.content)}
              className="p-1.5 rounded hover:bg-current/10 transition-colors"
              aria-label="Copy message"
            >
              <Copy className="w-4 h-4" />
            </button>
            {isAssistant && (
              <>
                <button
                  onClick={() => onFeedback(message.id, 'positive')}
                  className={cn(
                    'p-1.5 rounded transition-colors',
                    message.feedback === 'positive'
                      ? 'text-green-500 bg-green-50'
                      : 'hover:bg-current/10'
                  )}
                  aria-label="Helpful"
                >
                  <ThumbsUp className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'negative')}
                  className={cn(
                    'p-1.5 rounded transition-colors',
                    message.feedback === 'negative'
                      ? 'text-red-500 bg-red-50'
                      : 'hover:bg-current/10'
                  )}
                  aria-label="Not helpful"
                >
                  <ThumbsDown className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'negative')}
                  className="p-1.5 rounded hover:bg-current/10 transition-colors"
                  aria-label="Report"
                >
                  <Flag className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
        {isAssistant && hasSources && (
          <div className="mt-2">
            <button
              onClick={() => onToggleSources(message.id)}
              className="text-sm text-secondary-500 hover:text-secondary-700 flex items-center gap-1"
            >
              <FileText className="w-4 h-4" />
              Sources ({message.sources!.length})
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {isExpanded && (
              <div className="mt-2 space-y-2 pl-10">
                {message.sources!.map((source) => (
                  <SourceItem key={source.id} source={source} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceItem({ source }: { source: Source }) {
  return (
    <div className="bg-secondary-50 rounded-lg p-3 border border-secondary-200">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-secondary-700">{source.documentName}</span>
        <span className="text-xs text-secondary-500">Relevance: {(source.score * 100).toFixed(0)}%</span>
      </div>
      <p className="text-sm text-secondary-600 line-clamp-2">{source.content}</p>
    </div>
  )
}