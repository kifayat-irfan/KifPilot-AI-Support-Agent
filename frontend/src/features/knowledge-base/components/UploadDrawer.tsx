import { useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/utils/cn'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileText, ArrowUpDown, RotateCcw } from 'lucide-react'
import { Document } from '@/types'

interface UploadItem {
  file: File
  id: string
  progress: number
  status: 'pending' | 'uploading' | 'completed' | 'failed'
  error?: string
  document?: Document
}

interface UploadDrawerProps {
  isOpen: boolean
  onClose: () => void
  knowledgeBaseId: string
  onUploadComplete: (documents: Document[]) => void
  acceptedTypes?: string[]
  maxFileSize?: number
  maxFiles?: number
}

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
]

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function UploadDrawer({
  isOpen,
  onClose,
  knowledgeBaseId,
  onUploadComplete,
  acceptedTypes = ACCEPTED_TYPES,
  maxFileSize = MAX_FILE_SIZE,
  maxFiles = 10,
}: UploadDrawerProps) {
  const [items, setItems] = useState<UploadItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map())

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newItems: UploadItem[] = acceptedFiles
      .filter(file => {
        if (items.length >= maxFiles) return false
        if (file.size > maxFileSize) return false
        return true
      })
      .map(file => ({
        file,
        id: crypto.randomUUID(),
        progress: 0,
        status: 'pending' as const,
      }))

    setItems(prev => [...prev, ...newItems].slice(0, maxFiles))
  }, [items.length, maxFiles, maxFileSize])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: maxFileSize,
    maxFiles,
    disabled: isUploading,
  })

  const removeItem = (id: string) => {
    const controller = abortControllersRef.current.get(id)
    if (controller) {
      controller.abort()
      abortControllersRef.current.delete(id)
    }
    setItems(prev => prev.filter(item => item.id !== id))
  }

  const retryItem = async (id: string, uploadFn: (file: File, onProgress: (p: number) => void, signal: AbortSignal) => Promise<Document>) => {
    const item = items.find(i => i.id === id)
    if (!item) return

    const controller = new AbortController()
    abortControllersRef.current.set(id, controller)

    setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'uploading', progress: 0, error: undefined } : i))

    try {
      const document = await uploadFn(item.file, (progress) => {
        setItems(prev => prev.map(i => i.id === id ? { ...i, progress } : i))
      }, controller.signal)

      setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'completed', progress: 100, document } : i))
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' } : i))
    } finally {
      abortControllersRef.current.delete(id)
    }
  }

  const handleUploadAll = async (uploadFn: (file: File, onProgress: (p: number) => void, signal: AbortSignal) => Promise<Document>) => {
    const pendingItems = items.filter(i => i.status === 'pending' || i.status === 'failed')
    if (pendingItems.length === 0) return

    setIsUploading(true)

    const results: Document[] = []
    for (const item of pendingItems) {
      const controller = new AbortController()
      abortControllersRef.current.set(item.id, controller)

      setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'uploading', progress: 0, error: undefined } : i))

      try {
        const document = await uploadFn(item.file, (progress) => {
          setItems(prev => prev.map(i => i.id === item.id ? { ...i, progress } : i))
        }, controller.signal)

        setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'completed', progress: 100, document } : i))
        results.push(document)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') continue
        setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' } : i))
      } finally {
        abortControllersRef.current.delete(item.id)
      }
    }

    setIsUploading(false)
    if (results.length > 0) {
      onUploadComplete(results)
    }
  }

  const cancelAll = () => {
    abortControllersRef.current.forEach(controller => controller.abort())
    abortControllersRef.current.clear()
    setItems(prev => prev.map(i => i.status === 'uploading' ? { ...i, status: 'pending', progress: 0 } : i))
    setIsUploading(false)
  }

  const completedCount = items.filter(i => i.status === 'completed').length
  const failedCount = items.filter(i => i.status === 'failed').length
  const pendingCount = items.filter(i => i.status === 'pending' || i.status === 'uploading').length

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/50 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col animate-slide-up">
        <CardHeader className="border-b border-secondary-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Upload className="h-5 w-5 text-primary-600" />
              </div>
              <div>
                <CardTitle className="text-lg">Upload Documents</CardTitle>
                <p className="text-sm text-secondary-500">Drag & drop files or click to browse</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={isUploading}
              aria-label="Close upload drawer"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto p-0">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={cn(
              'p-8 border-b border-secondary-200 transition-colors',
              isDragActive && 'bg-primary-50 border-primary-200',
              isDragReject && 'bg-red-50 border-red-200'
            )}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center justify-center gap-4">
              {isDragActive ? (
                <div className="flex flex-col items-center gap-2 text-primary-600">
                  <ArrowUpDown className="h-12 w-12 animate-bounce" />
                  <p className="text-lg font-medium">Drop files here</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4 text-center">
                  <div className="p-4 bg-secondary-100 rounded-full">
                    <Upload className="h-8 w-8 text-secondary-500" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-secondary-900">Drag & drop files here</p>
                    <p className="text-sm text-secondary-500 mt-1">or click to browse</p>
                  </div>
                  <p className="text-xs text-secondary-400 max-w-sm">
                    Accepted: PDF, DOCX, TXT, Markdown • Max 50MB per file • Up to 10 files
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* File List */}
          {items.length > 0 && (
            <div className="divide-y divide-secondary-200 max-h-[50vh] overflow-y-auto">
              {items.map((item) => (
                <div key={item.id} className="p-4 hover:bg-secondary-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-secondary-100 rounded-lg">
                      <FileText className="h-5 w-5 text-secondary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-secondary-900 truncate">{item.file.name}</p>
                      <p className="text-sm text-secondary-500">{formatFileSize(item.file.size)}</p>
                      <div className="mt-2 h-2 bg-secondary-200 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all duration-300',
                            item.status === 'completed' && 'bg-green-500',
                            item.status === 'failed' && 'bg-red-500',
                            item.status === 'uploading' && 'bg-primary-500 animate-pulse'
                          )}
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          item.status === 'completed' ? 'success' :
                          item.status === 'failed' ? 'destructive' :
                          item.status === 'uploading' ? 'primary' : 'secondary'
                        }
                        size="sm"
                        dot
                        dotColor={
                          item.status === 'completed' ? '#10b981' :
                          item.status === 'failed' ? '#ef4444' :
                          item.status === 'uploading' ? '#3b82f6' : '#6b7280'
                        }
                      >
                        {item.status === 'uploading' ? 'Uploading...' :
                         item.status === 'completed' ? 'Completed' :
                         item.status === 'failed' ? 'Failed' : 'Pending'}
                      </Badge>
                      {(item.status === 'pending' || item.status === 'failed') && !isUploading && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => retryItem(item.id, uploadDocument)}
                          aria-label={item.status === 'failed' ? 'Retry upload' : 'Start upload'}
                        >
                          {item.status === 'failed' ? <RotateCcw className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
                        </Button>
                      )}
                      {(item.status === 'uploading' || isUploading) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const controller = abortControllersRef.current.get(item.id)
                            if (controller) controller.abort()
                          }}
                          aria-label="Cancel upload"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                      {(item.status === 'completed' || item.status === 'failed') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeItem(item.id)}
                          aria-label="Remove from list"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                  {item.error && (
                    <div className="mt-2 flex items-center gap-2 text-red-600 text-sm">
                      <AlertCircle className="h-4 w-4 flex-shrink-0" />
                      <span className="truncate">{item.error}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Summary */}
          {items.length > 0 && (
            <div className="p-4 border-t border-secondary-200 bg-secondary-50">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-secondary-600">Total: {items.length}</span>
                  <Badge variant="success" size="sm" dot>Completed: {completedCount}</Badge>
                  <Badge variant="destructive" size="sm" dot>Failed: {failedCount}</Badge>
                  <Badge variant="warning" size="sm" dot>Pending: {pendingCount}</Badge>
                </div>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="border-t border-secondary-200 flex-wrap gap-3">
          <div className="flex-1 flex items-center gap-3">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={isUploading || items.some(i => i.status === 'uploading')}
            >
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={cancelAll}
              disabled={!isUploading && pendingCount === 0}
            >
              Cancel All
            </Button>
            <Button
              variant="primary"
              onClick={() => handleUploadAll(uploadDocument)}
              disabled={isUploading || pendingCount === 0}
              loading={isUploading}
            >
              {isUploading ? 'Uploading...' : `Upload ${pendingCount} File${pendingCount !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </CardFooter>
      </div>
    </div>
  )
}

// Mock upload function - replace with actual API call
async function uploadDocument(
  file: File,
  onProgress: (progress: number) => void,
  signal: AbortSignal
): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)

  // Simulate upload with progress
  return new Promise((resolve, reject) => {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 15
      if (progress >= 100) {
        progress = 100
        clearInterval(interval)
        resolve({
          id: crypto.randomUUID(),
          filename: file.name,
          original_filename: file.name,
          title: file.name.replace(/\.[^/.]+$/, ''),
          description: null,
          category: null,
          tags: null,
          language: 'en',
          file_type: file.type,
          mime_type: file.type,
          file_size: file.size,
          status: 'completed',
          page_count: Math.floor(Math.random() * 50) + 1,
          chunk_count: Math.floor(Math.random() * 100) + 10,
          embeddings_created: Math.floor(Math.random() * 100) + 10,
          error_message: null,
          processing_time_ms: Math.floor(Math.random() * 10000) + 1000,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          knowledge_base_id: '',
        } as Document)
      }
      onProgress(Math.min(progress, 99))
    }, 200)

    signal.addEventListener('abort', () => {
      clearInterval(interval)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })
}

export default UploadDrawer