import { forwardRef, InputHTMLAttributes, useState, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface SearchBarProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  onChange?: (value: string) => void
  placeholder?: string
  className?: string
  debounceMs?: number
  showClearButton?: boolean
}

export const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(
  ({ className, placeholder = 'Search...', onChange, debounceMs = 300, showClearButton = true, ...props }, ref) => {
    const [value, setValue] = useState('')
    const [debouncedValue, setDebouncedValue] = useState('')

    useEffect(() => {
      const timer = setTimeout(() => {
        setDebouncedValue(value)
        onChange?.(value)
      }, debounceMs)

      return () => clearTimeout(timer)
    }, [value, debounceMs, onChange])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setValue(e.target.value)
    }

    const handleClear = () => {
      setValue('')
      onChange?.('')
    }

    return (
      <div className={cn('relative', className)}>
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-secondary-400" aria-hidden="true" />
        <input
          ref={ref}
          type="search"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          className={cn(
            'w-full pl-10 pr-10 py-2 text-sm bg-white border border-secondary-300 rounded-lg',
            'placeholder:text-secondary-400',
            'focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20',
            'transition-colors'
          )}
          {...props}
        />
        {showClearButton && value && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 transition-colors"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
    )
  }
)

SearchBar.displayName = 'SearchBar'