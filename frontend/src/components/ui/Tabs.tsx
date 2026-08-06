import { cn } from '@/utils/cn'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface TabsContextType {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = createContext<TabsContextType | null>(null)

interface TabsProviderProps {
  children: ReactNode
  value?: string
  onValueChange?: (value: string) => void
  defaultValue?: string
}

function TabsProvider({ children, value, onValueChange, defaultValue }: TabsProviderProps) {
  const [internalValue, setInternalValue] = useState(value || defaultValue || '')

  useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value)
    }
  }, [value])

  const handleValueChange = (newValue: string) => {
    setInternalValue(newValue)
    onValueChange?.(newValue)
  }

  return (
    <TabsContext.Provider value={{ value: internalValue, onValueChange: handleValueChange }}>
      {children}
    </TabsContext.Provider>
  )
}

function useTabs() {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('Tabs components must be used within TabsProvider')
  }
  return context
}

interface TabsProps {
  value?: string
  onValueChange?: (value: string) => void
  defaultValue?: string
  children: ReactNode
  className?: string
}

export function Tabs({ value, onValueChange, defaultValue, children, className }: TabsProps) {
  return (
    <TabsProvider value={value} onValueChange={onValueChange} defaultValue={defaultValue}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsProvider>
  )
}

interface TabsListProps {
  children: ReactNode
  className?: string
  'aria-label'?: string
}

export function TabsList({ children, className, 'aria-label': ariaLabel }: TabsListProps) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-secondary-100 p-1 text-secondary-600',
        className
      )}
    >
      {children}
    </div>
  )
}

interface TabsTriggerProps {
  value: string
  children: ReactNode
  className?: string
  disabled?: boolean
}

export function TabsTrigger({ value, children, className, disabled }: TabsTriggerProps) {
  const { value: currentValue, onValueChange } = useTabs()
  const isActive = currentValue === value

  return (
    <button
      role="tab"
      aria-selected={isActive}
      aria-controls={`panel-${value}`}
      id={`tab-${value}`}
      data-state={isActive ? 'active' : 'inactive'}
      data-disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
        isActive
          ? 'bg-white text-secondary-900 shadow-sm'
          : 'text-secondary-600 hover:text-secondary-900 hover:bg-secondary-50',
        disabled && 'text-secondary-400',
        className
      )}
      disabled={disabled}
      onClick={() => !disabled && onValueChange(value)}
    >
      {children}
    </button>
  )
}

interface TabsContentProps {
  value: string
  children: ReactNode
  className?: string
  forceMount?: boolean
}

export function TabsContent({ value, children, className, forceMount }: TabsContentProps) {
  const { value: currentValue } = useTabs()
  const isActive = currentValue === value

  if (!forceMount && !isActive) {
    return null
  }

  return (
    <div
      role="tabpanel"
      aria-labelledby={`tab-${value}`}
      id={`panel-${value}`}
      data-state={isActive ? 'active' : 'inactive'}
      className={cn(
        'mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
        !isActive && !forceMount && 'hidden',
        className
      )}
    >
      {children}
    </div>
  )
}

export default Tabs