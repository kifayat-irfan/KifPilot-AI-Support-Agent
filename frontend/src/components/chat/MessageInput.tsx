import { useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Paperclip, Mic, Smile } from 'lucide-react'
import { cn } from '@/utils/cn'

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  disabled: boolean
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
}

export function MessageInput({ value, onChange, onSubmit, disabled, textareaRef }: MessageInputProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled) {
        onSubmit(e)
      }
    }
  }

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  return (
    <form onSubmit={onSubmit} className="border-t border-secondary-200 bg-white p-4">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={disabled ? 'AI is responding...' : 'Type your message (Shift+Enter for new line)'}
            className={cn(
              'w-full min-h-[52px] max-h-48 px-4 py-3 pr-12 rounded-xl border border-secondary-300 bg-white',
              'text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500',
              'placeholder:text-secondary-400 disabled:bg-secondary-50 disabled:cursor-not-allowed'
            )}
            rows={1}
            style={{ height: 'auto' }}
            aria-label="Message input"
          />
          <div className="absolute bottom-2 right-2 flex items-center gap-1">
            <button
              type="button"
              className="p-1.5 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 transition-colors"
              aria-label="Attach file"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <button
              type="button"
              className="p-1.5 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 transition-colors"
              aria-label="Voice input"
            >
              <Mic className="w-5 h-5" />
            </button>
            <button
              type="button"
              className="p-1.5 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 transition-colors"
              aria-label="Emojis"
            >
              <Smile className="w-5 h-5" />
            </button>
          </div>
        </div>
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className={cn(
            'p-3 rounded-xl transition-all duration-200 flex-shrink-0',
            'bg-primary-600 text-white hover:bg-primary-700',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
          )}
          aria-label="Send message"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
      <p className="text-xs text-secondary-400 text-center mt-2">
        Press <kbd className="px-1.5 py-0.5 bg-secondary-100 rounded text-secondary-600 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-secondary-100 rounded text-secondary-600 font-mono text-[10px]">Shift+Enter</kbd> for new line
      </p>
    </form>
  )
}