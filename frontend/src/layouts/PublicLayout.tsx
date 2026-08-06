import { Outlet } from 'react-router-dom'

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-secondary-50">
      <main className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
        <Outlet />
      </main>
    </div>
  )
}