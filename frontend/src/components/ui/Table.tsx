import { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface TableProps {
  children: ReactNode
  className?: string
  stickyHeader?: boolean
}

export function Table({ children, className, stickyHeader }: TableProps) {
  return (
    <div className={cn('w-full overflow-x-auto', className)}>
      <table className="w-full text-sm text-left">
        {children}
      </table>
    </div>
  )
}

interface TableHeaderProps {
  children: ReactNode
  className?: string
}

export function TableHeader({ children, className }: TableHeaderProps) {
  return (
    <thead className={cn('bg-secondary-50 border-b border-secondary-200', className)}>
      {children}
    </thead>
  )
}

interface TableBodyProps {
  children: ReactNode
  className?: string
}

export function TableBody({ children, className }: TableBodyProps) {
  return (
    <tbody className={cn('divide-y divide-secondary-200', className)}>
      {children}
    </tbody>
  )
}

interface TableRowProps {
  children: ReactNode
  className?: string
  hover?: boolean
  selected?: boolean
  onClick?: () => void
}

export function TableRow({ children, className, hover, selected, onClick }: TableRowProps) {
  return (
    <tr
      className={cn(
        'transition-colors',
        hover && 'hover:bg-secondary-50',
        selected && 'bg-primary-50',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  )
}

interface TableHeadProps {
  children: ReactNode
  className?: string
  width?: string
  onClick?: () => void
}

export function TableHead({ children, className, width, onClick }: TableHeadProps) {
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-3 text-xs font-semibold text-secondary-600 uppercase tracking-wider',
        className,
        onClick && 'cursor-pointer select-none hover:bg-secondary-100'
      )}
      style={{ width }}
      onClick={onClick}
    >
      {children}
    </th>
  )
}

interface TableCellProps {
  children: ReactNode
  className?: string
  colSpan?: number
}

export function TableCell({ children, className, colSpan }: TableCellProps) {
  return (
    <td className={cn('px-4 py-3 text-secondary-700', className)} colSpan={colSpan}>
      {children}
    </td>
  )
}

interface TableFooterProps {
  children: ReactNode
  className?: string
}

export function TableFooter({ children, className }: TableFooterProps) {
  return (
    <tfoot className={cn('bg-secondary-50 border-t border-secondary-200', className)}>
      {children}
    </tfoot>
  )
}

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  className?: string
  showPageSize?: boolean
  pageSize?: number
  onPageSizeChange?: (size: number) => void
  pageSizeOptions?: number[]
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  className,
  showPageSize = false,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
}: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className={cn('flex items-center justify-between px-4 py-3 border-t border-secondary-200', className)}>
      <div className="flex items-center gap-2">
        <span className="text-sm text-secondary-600">
          Page {currentPage} of {totalPages}
        </span>
        {showPageSize && pageSize && onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="ml-2 px-2 py-1 text-sm border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Page size"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} per page
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-2 rounded-lg text-secondary-600 hover:bg-secondary-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Previous page"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-2 rounded-lg text-secondary-600 hover:bg-secondary-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Next page"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  )
}