import { useState } from 'react'
import { cn } from '@/utils/cn'
import { FileText, ChevronDown, ChevronUp, ExternalLink, Copy, Eye } from 'lucide-react'
import { Citation } from '@/types'

interface CitationPanelProps {
  citations: Array<{
    document_id: string
    document_name: string
    page_number: number | null
    section: string | null
    chunk_id: string
    chunk_index: number
    similarity_score: number
  }>
  messageId: string
  isOpen: boolean
  onToggle: () => void
  onClose: () => void
}

interface SourceCardProps {
  source: {
    document_id: string
    document_name: string
    page_number: number | null
    section: string | null
    chunk_id: string
    chunk_index: number
    similarity_score: number
  }
  index: number
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="bg-secondary-50 rounded-lg p-3 border border-secondary-200 animate-slide-up">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
            #{index + 1}
          </span>
          <span className="text-xs font-medium text-secondary-700 truncate max-w-[200px]">
            {source.document_name}
          </span>
        </div>
        <span className="text-xs text-secondary-500">
          Relevance: {(source.similarity_score * 100).toFixed(0)}%
        </span>
      </div>
      
      <div className="space-y-1 text-xs text-secondary-600">
        {source.page_number && (
          <div className="flex items-center gap-1">
            <span className="text-secondary-400">Page:</span>
            <span className="font-mono">{source.page_number}</span>
          </div>
        )}
        {source.section && (
          <div className="flex items-center gap-1">
            <span className="text-secondary-400">Section:</span>
            <span className="truncate">{source.section}</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <span className="text-secondary-400">Chunk:</span>
          <span className="font-mono">{source.chunk_index}</span>
        </div>
      </div>
    </div>
  )
}

export function CitationPanel({
  citations,
  messageId,
  isOpen,
  onToggle,
  onClose,
}: CitationPanelProps) {
  if (citations.length === 0) return null

  return (
    <div className={`transition-all duration-200 ease-out ${isOpen ? 'animate-slide-down' : 'animate-slide-up'}`}>
      <button
        onClick={onToggle}
        className="w-full text-left text-sm text-secondary-500 hover:text-secondary-700 flex items-center gap-1 py-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
        </svg>
        <span>Sources ({citations.length})</span>
        {isOpen ? (
          <svg className="w-4 h-4 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        ) : (
          <svg className="w-4 h-4 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {isOpen && (
        <div className="mt-2 space-y-2 pl-10 border-l-2 border-primary-200">
          {citations.map((citation, index) => (
            <div key={citation.chunk_id} className="relative pl-4 pb-4 border-l-2 border-primary-100 last:border-l-0">
              <div className="absolute -left-3 top-0 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center text-white text-xs font-medium">
                {index + 1}
              </div>
              <div className="bg-secondary-50 rounded-lg p-3 border border-secondary-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-secondary-700 truncate max-w-[200px]">
                    {citation.document_name}
                  </span>
                  <span className="text-xs text-secondary-500">
                    Relevance: {(citation.similarity_score * 100).toFixed(0)}%
                  </span>
                </div>
                
                <div className="space-y-1 text-xs text-secondary-600">
                  {citation.page_number && (
                    <div className="flex items-center gap-1">
                      <span className="text-secondary-400">Page:</span>
                      <span className="font-mono">{citation.page_number}</span>
                    </div>
                  )}
                  {citation.section && (
                    <div className="flex items-center gap-1">
                      <span className="text-secondary-400">Section:</span>
                      <span className="truncate">{citation.section}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <span className="text-secondary-400">Chunk:</span>
                    <span className="font-mono">{citation.chunk_index}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-secondary-400">Score:</span>
                    <span className="font-mono text-primary-600">
                      {(citation.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function InlineCitation({ citation }: { citation: {
  document_id: string
  document_name: string
  page_number: number | null
  section: string | null
  similarity_score: number
} }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 rounded text-xs font-medium cursor-pointer hover:bg-primary-100 transition-colors"
      title={`Source: ${citation.document_name}${citation.page_number ? `, p.${citation.page_number}` : ''}`}
    >
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
      </svg>
      <span className="truncate max-w-[150px]">{citation.document_name}</span>
      {citation.page_number && (
        <span className="text-primary-600/80">p.{citation.page_number}</span>
      )}
    </span>
  )
}

export function CitationBadge({ citations, maxVisible = 3 }: { 
  citations: Array<{
    document_name: string
    similarity_score: number
  }>
  maxVisible?: number
}) {
  if (citations.length === 0) return null

  const visible = citations.slice(0, maxVisible)
  const remaining = citations.length - maxVisible

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((citation, index) => (
        <span key={index} className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 rounded text-xs font-medium">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
          </svg>
          <span className="truncate max-w-[120px]">{citation.document_name}</span>
        </span>
      ))}
      {remaining > 0 && (
        <span className="inline-flex items-center px-2 py-0.5 bg-secondary-100 text-secondary-600 rounded text-xs font-medium">
          +{remaining} more
        </span>
      )}
    </div>
  )
}