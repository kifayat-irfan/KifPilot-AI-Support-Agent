import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import { Send, Paperclip, Mic } from 'lucide-react'
import { cn } from '@/utils/cn'

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  disabled?: boolean
  maxLength?: number
}

const MessageInput = forwardRef<HTMLTextAreaElement, MessageInputProps>(
  ({ value, onChange, onSubmit, disabled = false, maxLength = 4000 }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    useImperativeHandle<HTMLTextAreaElement, HTMLTextAreaElement>(
      ref,
      () => textareaRef.current!,
      []
    )

    const handleSubmit = useCallback(
      (e: React.FormEvent) => {
        e.preventDefault()
        if (!disabled && value.trim()) {
          onSubmit(e)
        }
      },
      [value, disabled, onSubmit]
    )

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault()
          if (!disabled && value.trim()) {
            onSubmit(e)
          }
        }
      },
      [value, disabled, onSubmit]
    )

    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
      }
    }, [value])

    return (
      <form onSubmit={handleSubmit} className="p-4 border-t border-secondary-200 bg-white">
        <div className="flex items-end gap-3">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={disabled ? 'Waiting for response...' : 'Type a message...'}
              maxLength={maxLength}
              className={cn(
                'w-full px-4 py-3 pr-12 text-sm bg-secondary-50 border border-secondary-200 rounded-xl',
                'focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500',
                'disabled:bg-secondary-100 disabled:cursor-not-allowed',
                'resize-none transition-colors'
              )}
              rows={1}
              style={{ maxHeight: '200px' }}
              aria-label="Message input"
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-1">
              <button
                type="button"
                className={cn(
                  'p-2 transition-colors',
                  disabled
                    ? 'text-secondary-300 cursor-not-allowed'
                    : 'text-secondary-400 hover:text-secondary-600'
                )}
                aria-label="Attach file"
                disabled={disabled || true}
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <button
                type="button"
                className={cn(
                  'p-2 transition-colors',
                  disabled
                    ? 'text-secondary-300 cursor-not-allowed'
                    : 'text-secondary-400 hover:text-secondary-600'
                )}
                aria-label="Voice input"
                disabled={disabled || true}
              >
                <Mic className="w-5 h-5" />
              </button>
            </div>
            {/* Character counter */}
            <div className="absolute bottom-1 right-12 text-xs text-secondary-400">
              {value.length}/{maxLength}
            </div>
          </div>
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className={cn(
              'p-3 rounded-xl transition-colors flex-shrink-0',
              'bg-primary-600 text-white hover:bg-primary-700',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    )
  }
)

MessageInput.displayName = 'MessageInput'

export { MessageInput }
export default MessageInput