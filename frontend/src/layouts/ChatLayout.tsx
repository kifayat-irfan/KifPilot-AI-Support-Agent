import { ReactNode } from 'react'
import { Outlet } from 'react-router-dom'
import { useChatStore } from '@/stores/chatStore'

export function ChatLayout({ children }: { children?: ReactNode }) {
  const { currentSession, isStreaming } = useChatStore()

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-hidden">
        {children || <Outlet />}
      </div>
      {isStreaming && (
        <div className="fixed bottom-4 right-4 z-50 animate-slide-up">
          <div className="bg-primary-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            <span className="text-sm font-medium">Generating response...</span>
          </div>
        </div>
      )}
    </div>
  )
}