import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User, Copy, ThumbsUp, ThumbsDown, Flag } from 'lucide-react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
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

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null as HTMLDivElement | null)
  const textareaRef = useRef<HTMLTextAreaElement>(null as HTMLTextAreaElement | null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))

    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `This is a simulated response to: "${inputValue.trim()}". In Phase 2, this will connect to the backend API with RAG capabilities.`,
      timestamp: new Date(),
      sources: [
        { id: '1', content: 'Sample source content...', score: 0.95, documentName: 'FAQ.pdf' },
        { id: '2', content: 'Another source...', score: 0.87, documentName: 'Manual.docx' },
      ],
    }

    setMessages(prev => [...prev, assistantMessage])
    setIsLoading(false)
  }

  const handleFeedback = (messageId: string, feedback: 'positive' | 'negative') => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === messageId ? { ...msg, feedback } : msg
      )
    )
  }

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content)
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-secondary-900">AI Support Assistant</h2>
        <p className="text-secondary-500 mt-1">Ask me anything about our products and services</p>
      </div>

      <MessageList
        messages={messages}
        onFeedback={handleFeedback}
        onCopy={handleCopy}
        messagesEndRef={messagesEndRef}
        isLoading={isLoading}
      />

      <MessageInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSendMessage}
        disabled={isLoading}
        textareaRef={textareaRef}
      />
    </div>
  )
}