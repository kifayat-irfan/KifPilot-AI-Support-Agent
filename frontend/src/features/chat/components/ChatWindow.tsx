import { useState, useRef, useEffect, useCallback, FormEvent } from 'react'
import { cn } from '@/utils/cn'
import { useChatStore } from '@/stores/chatStore'
import { useAuthStore } from '@/stores/authStore'
import { useOrganizationStore } from '@/stores/organizationStore'
import { chatService, StreamEvent, Citation } from '@/services/chat'
import { ChatHeader } from './ChatHeader'
import { ConversationSidebar } from './ConversationSidebar'
import { SessionList } from './SessionList'
import { ChatMessage } from './ChatMessage'
import { MessageInput } from './MessageInput'
import { TypingIndicator, StreamingTypingIndicator } from './TypingIndicator'
import { CitationPanel } from './CitationPanel'
import { EmptyState, WelcomeEmptyState, NoConversationsState } from './EmptyState'
import { X, RotateCcw, AlertCircle } from 'lucide-react'
import type { ChatSession, ChatMessage as ChatMessageType } from '@/types'
import type { Conversation, Message } from '@/services/chat'

interface ChatWindowProps {
  initialSessionId?: string
}

function conversationToChatSession(conv: Conversation): ChatSession {
  return {
    id: conv.id,
    organization_id: conv.session_id,
    title: conv.title || null,
    message_count: conv.message_count,
    last_activity: conv.updated_at,
    created_at: conv.created_at,
    updated_at: conv.updated_at,
  }
}

function messageToChatMessage(msg: Message, sessionId: string): ChatMessageType {
  return {
    id: msg.id,
    session_id: sessionId,
    role: msg.role,
    message: msg.content,
    citations: null,
    confidence: null,
    token_count: msg.tokens_used || null,
    response_time_ms: null,
    created_at: msg.created_at,
  }
}

export function ChatWindow({ initialSessionId }: ChatWindowProps) {
  const {
    sessions,
    currentSession,
    messages,
    isStreaming,
    isLoading,
    error,
    setSessions,
    setCurrentSession,
    addSession,
    updateSession,
    removeSession,
    setMessages,
    addMessage,
    updateMessage,
    clearMessages,
    setStreaming,
    setLoading,
    setError,
    abortStream,
  } = useChatStore()

  const { user } = useAuthStore()
  const { currentOrganization } = useOrganizationStore()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [citationPanelOpen, setCitationPanelOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set())
  const [inputValue, setInputValue] = useState('')
  const [citationMessageId, setCitationMessageId] = useState<string | null>(null)
  const [selectedCitations, setSelectedCitations] = useState<Citation[]>([])
  const [lastUserMessage, setLastUserMessage] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const response = await chatService.getConversations({ limit: 50 })
      setSessions(response.map(conversationToChatSession))
    } catch (err) {
      setError('Failed to load conversations')
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      setLoading(true)
      clearMessages()
      setSidebarOpen(false)
      
      const session = await chatService.getConversation(sessionId)
      setCurrentSession(conversationToChatSession(session))
      
      const msgs = await chatService.getMessages(sessionId)
      setMessages(msgs.map(m => messageToChatMessage(m, sessionId)))
    } catch (err) {
      setError('Failed to load conversation')
      console.error('Failed to load conversation:', err)
    } finally {
      setLoading(false)
    }
  }, [setCurrentSession, setMessages, clearMessages, setLoading, setError])

  const handleDeleteSession = useCallback(async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this conversation?')) return
    
    try {
      await chatService.deleteConversation(sessionId)
      removeSession(sessionId)
      if (currentSession?.id === sessionId) {
        setCurrentSession(null)
        clearMessages()
      }
    } catch (err) {
      setError('Failed to delete conversation')
      console.error('Failed to delete session:', err)
    }
  }, [removeSession, setCurrentSession, clearMessages, currentSession])

  const handleRenameSession = useCallback(async (sessionId: string, newTitle: string) => {
    try {
      await chatService.updateConversation(sessionId, { title: newTitle })
      updateSession({ ...currentSession!, title: newTitle })
    } catch (err) {
      setError('Failed to rename conversation')
      console.error('Failed to rename session:', err)
    }
  }, [updateSession, currentSession])

  const handleSendMessage = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    const messageText = inputValue.trim()
    if (!messageText || isStreaming) return

    const now = new Date().toISOString()
    const sessionId = currentSession?.id || ''

    const userMessage: ChatMessageType = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: 'user',
      message: messageText,
      citations: null,
      confidence: null,
      token_count: null,
      response_time_ms: null,
      created_at: now,
    }

    addMessage(userMessage)
    setInputValue('')
    setLastUserMessage(messageText)
    setStreaming(true)
    setError(null)

    abortControllerRef.current = new AbortController()

    try {
      const stream = chatService.sendMessageStream({
        message: userMessage.message,
        session_id: currentSession?.id,
        stream: true,
      })

      let assistantMessageId = crypto.randomUUID()
      let fullContent = ''
      let citations: Citation[] = []
      let confidence = 0

      // Add placeholder for streaming message
      const streamingMessage: ChatMessageType = {
        id: assistantMessageId,
        session_id: sessionId,
        role: 'assistant',
        message: '',
        citations: null,
        confidence: null,
        token_count: null,
        response_time_ms: null,
        created_at: new Date().toISOString(),
      }
      addMessage(streamingMessage)

      for await (const event of stream) {
        if (abortControllerRef.current?.signal.aborted) break

        switch (event.type) {
          case 'token':
            if (event.data.text) {
              fullContent += event.data.text
              updateMessage(assistantMessageId, { message: fullContent })
            }
            break

          case 'citations':
            if (event.data.citations) {
              citations = event.data.citations
            }
            break

          case 'complete':
            if (event.data.confidence !== undefined) confidence = event.data.confidence
            updateMessage(assistantMessageId, {
              message: fullContent,
              citations,
              confidence,
            })
            break

          case 'error':
            updateMessage(assistantMessageId, {
              message: `Error: ${event.data.error}`,
            })
            break
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Stream error:', err)
        setError('Failed to get response')
      }
    } finally {
      setStreaming(false)
      abortControllerRef.current = null
    }
  }, [addMessage, updateMessage, setStreaming, setError, currentSession, inputValue])

  const handleStopGeneration = useCallback(() => {
    abortControllerRef.current?.abort()
    setStreaming(false)
    abortControllerRef.current = null
  }, [setStreaming])

  const handleRetry = useCallback(async () => {
    if (!lastUserMessage.trim() || isStreaming) return
    await handleSendMessage({ preventDefault: () => {} } as FormEvent)
  }, [lastUserMessage, isStreaming, handleSendMessage])

  const handleCreateSession = useCallback(async (initialQuery?: string) => {
    try {
      setLoading(true)
      clearMessages()
      const session = await chatService.createConversation({
        session_id: currentOrganization?.id || '',
      })
      const chatSession = conversationToChatSession(session)
      addSession(chatSession)
      setCurrentSession(chatSession)
      setSidebarOpen(false)
      if (initialQuery) {
        setInputValue(initialQuery)
        // Trigger send after state updates
        setTimeout(() => {
          handleSendMessage({ preventDefault: () => {} } as FormEvent)
        }, 0)
      }
    } catch (err) {
      setError('Failed to create conversation')
      console.error('Failed to create session:', err)
    } finally {
      setLoading(false)
    }
  }, [addSession, setCurrentSession, setLoading, currentOrganization, setInputValue, handleSendMessage])

  const handleFeedback = useCallback((messageId: string, feedback: 'positive' | 'negative') => {
    updateMessage(messageId, { feedback })
  }, [updateMessage])

  const handleCopy = useCallback((content: string) => {
    navigator.clipboard.writeText(content)
  }, [])

  const handleToggleSources = useCallback((messageId: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }, [])

  const handleRegenerate = useCallback(async (messageId: string) => {
    // Find the message and its previous user message
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex <= 0) return

    const userMessage = messages[messageIndex - 1]
    if (userMessage.role !== 'user') return

    // Remove the assistant message and re-send
    setMessages((prev: ChatMessageType[]) => prev.filter((m: ChatMessageType) => m.id !== messageId))
    // Set input value to the user's message content and trigger send
    setInputValue(userMessage.message)
    // We need to trigger a form submit, but we can't easily do that here
    // Instead, we'll just set the input and let the user press Enter
  }, [messages, setMessages, setInputValue])

  const handleCitationToggle = useCallback((messageId: string) => {
    setCitationMessageId(prev => prev === messageId ? null : messageId)
  }, [])

  const handleOpenCitationPanel = useCallback((citations: Citation[]) => {
    setSelectedCitations(citations)
    setCitationPanelOpen(true)
  }, [])

  const handleCloseCitationPanel = useCallback(() => {
    setCitationPanelOpen(false)
    setSelectedCitations([])
  }, [])

  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query)
  }, [])

  const handleSidebarToggle = useCallback(() => {
    setSidebarOpen(prev => !prev)
  }, [])

  if (isLoading && sessions.length === 0) {
    return (
      <div className="flex h-screen">
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-600 border-t-transparent" />
        </div>
      </div>
    )
  }

return (
    <div className="flex h-screen bg-secondary-50">
      {/* Sidebar */}
      <ConversationSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        activeSessionId={currentSession?.id || null}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
      />

      {/* Main Chat Area */}
      <div className={cn('flex-1 flex flex-col min-w-0 lg:ml-0', sidebarOpen ? 'lg:ml-80' : 'lg:ml-20')}>
        <ChatHeader
          title={currentSession?.title || 'New Conversation'}
          subtitle={currentOrganization?.name}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          sidebarOpen={sidebarOpen}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          {currentSession ? (
            <>
              <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
                {messages.length === 0 ? (
                  <WelcomeEmptyState onNewChat={handleCreateSession} />
                ) : (
                  <>
                    <div className="max-w-4xl mx-auto w-full space-y-6 pb-4">
                      {messages.map((message) => (
                        <ChatMessage
                          key={message.id}
                          message={{
                            id: message.id,
                            role: message.role,
                            content: message.message,
                            timestamp: message.created_at,
                            citations: message.citations || undefined,
                            feedback: message.feedback,
                            isStreaming: message.isStreaming,
                          }}
                          onFeedback={handleFeedback}
                          onCopy={handleCopy}
                          onToggleSources={handleToggleSources}
                          expandedSources={expandedSources}
                          onRegenerate={handleRegenerate}
                          onOpenCitationPanel={handleOpenCitationPanel}
                        />
                      ))}
                      {isStreaming && (
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                            <svg className="w-5 h-5 text-primary-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                          </div>
                          <div className="bg-secondary-100 rounded-2xl px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className="flex gap-1">
                                <span className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                              </div>
                              <button
                                onClick={handleStopGeneration}
                                className="ml-2 p-1.5 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-200 transition-colors"
                                aria-label="Stop generation"
                              >
                                <X className="w-5 h-5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                      {error && (
                        <div className="flex items-center justify-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
                          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                          <span className="text-red-700 text-sm">{error}</span>
                          <button
                            onClick={handleRetry}
                            className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                          >
                            Retry
                          </button>
                        </div>
                      )}
                    </div>
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              <MessageInput
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSendMessage}
                disabled={isStreaming || isLoading || !currentSession}
              />
            </>
          ) : null}
</main>
      </div>

      {/* Citation Panel */}
      {citationPanelOpen && (
        <div className="fixed inset-0 z-40 lg:static lg:inset-auto lg:w-80 lg:border-l lg:border-secondary-200 lg:bg-white">
          <div
            className="fixed inset-0 bg-black/50 lg:hidden"
            onClick={handleCloseCitationPanel}
            aria-hidden="true"
          />
          <aside className="fixed lg:static inset-y-0 right-0 z-50 bg-white w-80 flex flex-col animate-slide-in-right lg:animate-none">
            <div className="flex items-center justify-between h-16 px-4 border-b border-secondary-200">
              <h2 className="font-semibold text-lg text-secondary-900">Sources</h2>
              <button
                onClick={handleCloseCitationPanel}
                className="p-2 rounded-lg text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 transition-colors"
                aria-label="Close citation panel"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <CitationPanel
              citations={selectedCitations}
              messageId={citationMessageId || ''}
              isOpen={true}
              onToggle={handleCloseCitationPanel}
              onClose={handleCloseCitationPanel}
            />
          </aside>
        </div>
      )}
    </div>
  )
}
 
export default ChatWindow