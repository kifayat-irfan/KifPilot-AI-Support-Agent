import { useRef, useState } from 'react'
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown, Flag, ChevronDown, ChevronUp, FileText, ExternalLink } from 'lucide-react'
import { cn } from '@/utils/cn'
import ReactMarkdown from 'react-markdown'
import { Citation } from '@/types'
import rehypeHighlight from 'rehype-highlight'

interface ChatMessageProps {
  message: {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: Date | string
    citations?: Citation[]
    feedback?: 'positive' | 'negative'
    isStreaming?: boolean
  }
  onFeedback: (messageId: string, feedback: 'positive' | 'negative') => void
  onCopy: (content: string) => void
  onToggleSources: (messageId: string) => void
  expandedSources: Set<string>
  onRegenerate?: (messageId: string) => void
  onOpenCitationPanel?: (citations: Citation[]) => void
}

function SourceItem({ source }: { source: Citation }) {
  return (
    <div className="bg-secondary-50 rounded-lg p-3 border border-secondary-200">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-secondary-700">{source.document_name}</span>
        <span className="text-xs text-secondary-500">Relevance: {(source.similarity_score * 100).toFixed(0)}%</span>
      </div>
      <p className="text-sm text-secondary-600 line-clamp-2">{source.section || 'No section'}</p>
    </div>
  )
}

export function ChatMessage({
  message,
  onFeedback,
  onCopy,
  onToggleSources,
  expandedSources,
  onRegenerate,
  onOpenCitationPanel,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const isAssistant = message.role === 'assistant'
  const isExpanded = expandedSources.has(message.id)
  const hasSources = message.citations && message.citations.length > 0
  const contentRef = useRef<HTMLDivElement>(null)

  const handleCopy = () => {
    onCopy(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const timestamp = typeof message.timestamp === 'string'
    ? new Date(message.timestamp)
    : message.timestamp

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={cn('flex gap-3', message.role === 'user' ? 'flex-row-reverse' : '')}>
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          message.role === 'assistant' ? 'bg-primary-100' : message.role === 'user' ? 'bg-primary-100' : 'bg-secondary-100'
        )}
      >
        {message.role === 'assistant' ? (
          <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-secondary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        )}
      </div>
      <div className={cn('flex-1 max-w-3xl', message.role === 'user' ? 'text-right' : '')}>
        <div
          className={cn(
            'relative rounded-2xl px-4 py-3',
            message.role === 'assistant'
              ? 'bg-white text-secondary-900 shadow-sm border border-secondary-200'
              : 'bg-primary-600 text-white'
          )}
        >
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown
              rehypePlugins={[rehypeHighlight]}
              components={{
                code: ({ children, ...props }: React.ComponentProps<'code'>) => (
                  <pre className="bg-secondary-900 rounded-lg p-3 overflow-x-auto">
                    <code {...props} className="text-sm text-secondary-100" />
                  </pre>
                ),
                blockquote: ({ children, ...props }: React.ComponentProps<'blockquote'>) => (
                  <blockquote {...props} className="border-l-4 border-primary-500 pl-4 italic text-secondary-600 my-2">
                    {children}
                  </blockquote>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-current/10">
            <span className="text-xs text-current/60 flex-1 text-right">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="w-px h-4 bg-current/10 mx-1" />
            <button
              onClick={handleCopy}
              className="p-1.5 rounded hover:bg-current/10 transition-colors"
              aria-label="Copy message"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 00-2 2h-2M8 5a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 00-2 2h-2M8 5a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 00-2 2h-2M8 5a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 00-2 2h-2" />
              </svg>
            </button>
            {message.role === 'assistant' && (
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
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7.086a2 2 0 01-1.789 1.114H4a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l3.5 3.5a1 1 0 010 1.414z" />
                  </svg>
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
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H4a2 2 0 01-2-2V5a2 2 0 012-2h6a2 2 0 012 2v7M10 14l4 4m0 0l4-4m-4 4v10" />
                  </svg>
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'negative')}
                  className="p-1.5 rounded hover:bg-current/10 transition-colors"
                  aria-label="Report"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>
        {message.role === 'assistant' && hasSources && (
          <div className="mt-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => onToggleSources(message.id)}
                className="text-sm text-secondary-500 hover:text-secondary-700 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
                </svg>
                Sources ({message.citations!.length})
                {isExpanded ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </button>
              {onOpenCitationPanel && (
                <button
                  onClick={() => onOpenCitationPanel(message.citations!)}
                  className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-primary-50 transition-colors"
                  aria-label="Open sources in panel"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">View in panel</span>
                </button>
              )}
            </div>
            {isExpanded && (
              <div className="mt-2 space-y-2 pl-10">
                {message.citations!.map((source) => (
                  <SourceItem key={source.chunk_id} source={source} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage