# Frontend Architecture

## Overview

React 18 + TypeScript + Vite single-page application with component-driven architecture.

```
src/
├── main.tsx                 # App entry point
├── App.tsx                  # Root component with routing
├── vite-env.d.ts           # Vite types
├── components/
│   ├── ui/                  # Base reusable components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Table.tsx
│   │   ├── Card.tsx
│   │   └── ...
│   ├── layout/              # Layout components
│   │   ├── Layout.tsx
│   │   ├── DashboardLayout.tsx
│   │   ├── ChatLayout.tsx
│   │   └── PublicLayout.tsx
│   ├── auth/                # Authentication components
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── AuthLayout.tsx
│   └── chat/                # Chat-specific components
│       ├── ChatWindow.tsx
│       ├── ChatMessage.tsx
│       ├── MessageInput.tsx
│       ├── CitationPanel.tsx
│       └── ConversationSidebar.tsx
├── features/                # Feature modules (domain-driven)
│   ├── admin/
│   │   ├── components/
│   │   ├── AdminDashboardPage.tsx
│   │   └── UsersPage.tsx
│   ├── chat/
│   │   ├── components/
│   │   └── ChatPage.tsx
│   ├── documents/
│   │   ├── components/
│   │   └── DocumentsPage.tsx
│   └── knowledge-base/
│       ├── components/
│       └── KnowledgeBasePage.tsx
├── pages/                   # Route-level page components
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── DashboardPage.tsx
│   ├── SettingsPage.tsx
│   └── NotFoundPage.tsx
├── services/                # API layer
│   ├── api.ts              # Axios instance + interceptors
│   ├── auth.ts             # Auth endpoints
│   ├── chat.ts             # Chat/RAG endpoints
│   ├── documents.ts        # Document endpoints
│   ├── knowledgeBase.ts    # KB endpoints
│   └── admin.ts            # Admin endpoints
├── stores/                  # Global state (Zustand)
│   ├── authStore.ts        # User, tokens, permissions
│   ├── chatStore.ts        # Messages, streaming state
│   ├── documentStore.ts    # Document list, filters
│   ├── organizationStore.ts # Org data, members
│   └── settingsStore.ts    # User preferences
├── types/                   # TypeScript definitions
│   ├── api.ts              # API request/response types
│   ├── auth.ts             # User, role, permission types
│   ├── chat.ts             # Message, conversation types
│   ├── document.ts         # Document, chunk types
│   └── index.ts            # Re-exports
├── utils/                   # Utilities
│   ├── cn.ts               # clsx + tailwind-merge
│   ├── auth.ts             # Token helpers
│   └── format.ts           # Date, file size formatting
└── styles/
    └── index.css           # Tailwind imports + globals
```

## Component Architecture

### Component Hierarchy

```
App
├── Router
│   ├── PublicLayout
│   │   ├── LoginPage
│   │   │   └── LoginForm
│   │   └── RegisterPage
│   │       └── RegisterForm
│   └── ProtectedRoute (auth check)
│       ├── DashboardLayout
│       │   ├── Sidebar (navigation)
│       │   ├── Header (user menu, notifications)
│       │   └── Outlet
│       │       ├── DashboardPage
│       │       │   └── StatisticsCards, QuickActions
│       │       ├── DocumentsPage
│       │       │   ├── FilterPanel
│       │       │   ├── DocumentTable
│       │       │   └── UploadDrawer
│       │       ├── KnowledgeBasePage
│       │       │   ├── KBList
│       │       │   └── KBDetailsDrawer
│       │       ├── ChatPage
│       │       │   ├── ConversationSidebar
│       │       │   ├── ChatWindow
│       │       │   │   ├── ChatMessage[]
│       │       │   │   ├── TypingIndicator
│       │       │   │   └── EmptyState
│       │       │   ├── MessageInput
│       │       │   └── CitationPanel
│       │       └── SettingsPage
│       └── AdminLayout (role check)
│           ├── AdminDashboardPage
│           │   ├── OverviewCards
│           │   ├── ChartsGrid
│           │   ├── SystemHealthPanel
│           │   └── RecentActivityPanel
│           ├── UsersPage
│           │   └── UsersTable
│           └── OrganizationsPage
│               └── OrganizationsTable
```

## State Management (Zustand)

### Store Structure

```typescript
// authStore.ts - Authentication state
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  permissions: Permission[];
  isAuthenticated: boolean;
  login: (credentials) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
}

// chatStore.ts - Chat/conversation state
interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  citations: Citation[];
  createConversation: (title) => Promise<void>;
  sendMessage: (content) => Promise<void>;
  streamMessage: (content) => AsyncGenerator<ChatEvent>;
  switchConversation: (id) => void;
  deleteConversation: (id) => Promise<void>;
}

// documentStore.ts - Document management
interface DocumentState {
  documents: Document[];
  filters: DocumentFilters;
  pagination: Pagination;
  loading: boolean;
  fetchDocuments: () => Promise<void>;
  uploadDocument: (file, metadata) => Promise<Document>;
  deleteDocument: (id) => Promise<void>;
  restoreDocument: (id) => Promise<void>;
}

// organizationStore.ts - Organization data
interface OrganizationState {
  organizations: Organization[];
  currentOrganization: Organization | null;
  members: Member[];
  fetchOrganizations: () => Promise<void>;
  createOrganization: (data) => Promise<void>;
  updateMemberRole: (userId, role) => Promise<void>;
}
```

### State Flow

```
User Action → Component → Store Action → API Service → Backend
                                          ↓
Response → Store Update → Component Re-render → UI Update
```

## API Layer (Axios)

### Configuration

```typescript
// services/api.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

// Request interceptor - attach token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor - handle 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await useAuthStore.getState().refreshAccessToken();
      return api.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

### Service Pattern

```typescript
// services/chat.ts
export const chatService = {
  async ask(question: string, options: ChatOptions): Promise<ChatResponse> {
    const { data } = await api.post('/chat/ask', { question, ...options });
    return data;
  },

  async *stream(question: string, options: ChatOptions): AsyncGenerator<ChatEvent> {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, ...options })
    });
    
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value);
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('event:') || line.startsWith('data:')) {
          yield parseSSEEvent(line);
        }
      }
    }
  }
};
```

## Routing & Navigation

### Route Structure

```typescript
// App.tsx
<Routes>
  {/* Public routes */}
  <Route path="/login" element={<PublicLayout><LoginPage /></PublicLayout>} />
  <Route path="/register" element={<PublicLayout><RegisterPage /></PublicLayout>} />
  <Route path="/forgot-password" element={<PublicLayout><ForgotPasswordPage /></PublicLayout>} />
  
  {/* Protected routes */}
  <Route element={<ProtectedRoute><DashboardLayout><Outlet /></DashboardLayout></ProtectedRoute>}>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/documents" element={<DocumentsPage />} />
    <Route path="/documents/:id" element={<DocumentDetails />} />
    <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
    <Route path="/knowledge-base/:id" element={<KnowledgeBaseDetails />} />
    <Route path="/chat" element={<ChatPage />} />
    <Route path="/chat/:conversationId" element={<ChatPage />} />
    <Route path="/settings" element={<SettingsPage />} />
  </Route>
  
  {/* Admin routes */}
  <Route element={<ProtectedRoute requiredRole="admin"><DashboardLayout><Outlet /></DashboardLayout></ProtectedRoute>}>
    <Route path="/admin" element={<AdminDashboardPage />} />
    <Route path="/admin/users" element={<UsersPage />} />
    <Route path="/admin/organizations" element={<OrganizationsPage />} />
  </Route>
  
  <Route path="*" element={<NotFoundPage />} />
</Routes>
```

### Protected Route Component

```typescript
// components/auth/ProtectedRoute.tsx
interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: UserRole;
  requiredPermission?: Permission;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission
}) => {
  const { isAuthenticated, user, permissions } = useAuthStore();
  const location = useLocation();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  if (requiredRole && !hasRole(user, requiredRole)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  if (requiredPermission && !permissions.includes(requiredPermission)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};
```

## Streaming Implementation

### SSE Event Parsing

```typescript
// utils/sse.ts
type ChatEvent = 
  | { event: 'start'; data: { session_id: string } }
  | { event: 'token'; data: { text: string; token_id: number } }
  | { event: 'retrieval'; data: { chunks_found: number; time_ms: number } }
  | { event: 'citations'; data: { citations: Citation[] } }
  | { event: 'complete'; data: { confidence: number; sources: number; time_ms: number } }
  | { event: 'error'; data: { message: string; code: string } };

export function parseSSEEvent(line: string): ChatEvent | null {
  if (line.startsWith('event: ')) {
    currentEvent = line.slice(7).trim();
    return null;
  }
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));
    return { event: currentEvent, data };
  }
  return null;
}
```

### Streaming Hook

```typescript
// hooks/useStreamChat.ts
export function useStreamChat() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const addMessage = useChatStore((s) => s.addMessage);
  
  const streamMessage = useCallback(async (question: string) => {
    setIsStreaming(true);
    setStreamingContent('');
    
    const messageId = `msg-${Date.now()}`;
    addMessage({ id: messageId, role: 'assistant', content: '', streaming: true });
    
    try {
      for await (const event of chatService.stream(question, { top_k: 5 })) {
        switch (event.event) {
          case 'token':
            setStreamingContent(prev => prev + event.data.text);
            updateMessageContent(messageId, event.data.text);
            break;
          case 'citations':
            updateMessageCitations(messageId, event.data.citations);
            break;
          case 'complete':
            finalizeMessage(messageId, event.data);
            break;
          case 'error':
            handleStreamError(messageId, event.data);
            break;
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }, [addMessage]);
  
  return { streamMessage, isStreaming, streamingContent };
}
```

## Performance Optimizations

### Code Splitting

```typescript
// Lazy load feature pages
const DocumentsPage = lazy(() => import('./features/documents/DocumentsPage'));
const KnowledgeBasePage = lazy(() => import('./features/knowledge-base/KnowledgeBasePage'));
const ChatPage = lazy(() => import('./features/chat/ChatPage'));
const AdminDashboardPage = lazy(() => import('./features/admin/AdminDashboardPage'));

// Suspense boundary
<Suspense fallback={<PageLoader />}>
  <Routes>...</Routes>
</Suspense>
```

### Memoization

```typescript
// Expensive list rendering
const DocumentRow = memo(({ document, onDelete }: DocumentRowProps) => (
  <tr>...</tr>
));

// Virtualized lists for large datasets
import { FixedSizeList } from 'react-window';
```

### Bundle Analysis

```bash
npm run build -- --mode analyze
# Generates stats.html for webpack-bundle-analyzer
```

## Testing Architecture

### Unit Tests (Vitest)

```typescript
// components/ui/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

test('renders and handles click', () => {
  const handleClick = vi.fn();
  render(<Button onClick={handleClick}>Click me</Button>);
  fireEvent.click(screen.getByRole('button'));
  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

### Integration Tests

```typescript
// services/chat.test.ts
import { chatService } from './chat';
import { server } from '../test/msw-server';

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('streamMessage yields tokens', async () => {
  const tokens: string[] = [];
  for await (const event of chatService.stream('Hello', {})) {
    if (event.event === 'token') tokens.push(event.data.text);
  }
  expect(tokens.length).toBeGreaterThan(0);
});
```

### E2E Tests (Playwright)

```typescript
// tests/e2e/chat.spec.ts
test('user can send message and receive streaming response', async ({ page }) => {
  await page.goto('/chat');
  await page.fill('textarea[placeholder*="Message"]', 'Hello');
  await page.click('button:has-text("Send")');
  await expect(page.locator('[data-role="assistant"]')).toBeVisible({ timeout: 30000 });
});
```

## Accessibility

### ARIA Patterns

```tsx
// Chat message with proper roles
<div role="log" aria-live="polite" aria-atomic="false">
  <div role="article" aria-label="User message">
    <div role="heading" aria-level="3">You</div>
    <p>{content}</p>
  </div>
  <div role="article" aria-label="Assistant response">
    <div role="heading" aria-level="3">Assistant</div>
    <p>{content}</p>
    <CitationPanel citations={citations} />
  </div>
</div>
```

### Keyboard Navigation

- `Tab`/`Shift+Tab`: Navigate interactive elements
- `Enter`/`Space`: Activate buttons/links
- `Escape`: Close modals/drawers
- `Ctrl/Cmd + K`: Focus search
- `Ctrl/Cmd + Enter`: Send message

## Internationalization Ready

```typescript
// All user-facing strings extracted
import { t } from '@/utils/i18n';

<Button>{t('chat.send')}</Button>
<EmptyState title={t('chat.no_messages')} description={t('chat.start_conversation')} />
```

## Build & Deployment

### Development

```bash
npm run dev        # Vite dev server with HMR
npm run lint       # ESLint + Prettier
npm run typecheck  # tsc --noEmit
npm test           # Vitest
```

### Production Build

```bash
npm run build      # Vite production build
# Output: dist/ with hashed assets, gzip/brotli
```

### Docker

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```