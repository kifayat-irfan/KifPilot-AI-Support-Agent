# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints require authentication unless noted. Include `Authorization: Bearer <token>` header.

## Authentication

### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "securepassword123",
  "full_name": "Full Name"
}
```
**Response:** `201 Created` - User object (no token)

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```
**Response:** `200 OK` - `{ access_token, token_type, user }`

### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
```
**Response:** `200 OK`

### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer <token>
```
**Response:** `200 OK` - `{ access_token, token_type }`

### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>
```
**Response:** `200 OK` - User object

### Change Password
```http
POST /auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "oldpass",
  "new_password": "newpass123"
}
```

### Forgot Password
```http
POST /auth/forgot-password
Content-Type: application/json

{ "email": "user@example.com" }
```

### Reset Password
```http
POST /auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "newpass123"
}
```

## Organizations

### Create Organization
```http
POST /organizations
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Organization",
  "slug": "my-org",
  "description": "Optional description"
}
```

### List Organizations
```http
GET /organizations
Authorization: Bearer <token>
```
**Query Params:** `page`, `page_size`

### Get Organization
```http
GET /organizations/{org_id}
Authorization: Bearer <token>
```

### Update Organization
```http
PATCH /organizations/{org_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Name",
  "description": "New description"
}
```

### Delete Organization
```http
DELETE /organizations/{org_id}
Authorization: Bearer <token>
```

### List Members
```http
GET /organizations/{org_id}/members
Authorization: Bearer <token>
```

### Add Member
```http
POST /organizations/{org_id}/members
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "newmember@example.com",
  "role": "editor"
}
```

### Update Member Role
```http
PATCH /organizations/{org_id}/members/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{ "role": "manager" }
```

### Remove Member
```http
DELETE /organizations/{org_id}/members/{user_id}
Authorization: Bearer <token>
```

## Users

### List Users
```http
GET /users
Authorization: Bearer <token>
```
**Query Params:** `page`, `page_size`, `search`, `is_active`

### Get User
```http
GET /users/{user_id}
Authorization: Bearer <token>
```

### Update User
```http
PATCH /users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "New Name",
  "is_active": true
}
```

### Delete User
```http
DELETE /users/{user_id}
Authorization: Bearer <token>
```

### Get User Roles
```http
GET /users/{user_id}/roles
Authorization: Bearer <token>
```

### Assign Role
```http
POST /users/{user_id}/roles
Authorization: Bearer <token>
Content-Type: application/json

{ "role": "editor" }
```

### Revoke Role
```http
DELETE /users/{user_id}/roles/{role_name}
Authorization: Bearer <token>
```

### Get User Permissions
```http
GET /users/{user_id}/permissions
Authorization: Bearer <token>
```

## Documents

### Upload Document
```http
POST /documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <file>
title: "Optional Title" (form field)
description: "Optional description" (form field)
category: "Optional category" (form field)
tags: "tag1,tag2,tag3" (form field)
language: "en" (form field)
force_reindex: false (form field)
```

**Response:** `201 Created` - `{ document_id, filename, pages, chunks_created, embeddings_created, processing_time_ms }`

**Duplicate Response:** `200 OK` - `{ duplicate: true, existing_document_id, filename, message }`

**Errors:** `400` (validation), `413` (too large), `415` (unsupported type), `409` (duplicate)

### List Documents
```http
GET /documents
Authorization: Bearer <token>
```
**Query Params:** `category`, `language`, `status`, `search`, `sort_by`, `sort_order`, `page`, `page_size`

### Get Document
```http
GET /documents/{document_id}
Authorization: Bearer <token>
```

### Update Document Metadata
```http
PATCH /documents/{document_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "New Title",
  "description": "New description",
  "category": "new-category",
  "tags": ["tag1", "tag2"],
  "language": "en"
}
```

### Delete Document
```http
DELETE /documents/{document_id}
Authorization: Bearer <token>
```
**Query Params:** `hard=false` (soft delete by default)

### Restore Document
```http
POST /documents/{document_id}/restore
Authorization: Bearer <token>
```

### Get Document Chunks
```http
GET /documents/{document_id}/chunks
Authorization: Bearer <token>
```

## Knowledge Bases

### Create Knowledge Base
```http
POST /knowledge-bases
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My KB",
  "description": "Description",
  "embedding_model": "nomic-embed-text"
}
```

### List Knowledge Bases
```http
GET /knowledge-bases
Authorization: Bearer <token>
```

### Get Knowledge Base
```http
GET /knowledge-bases/{kb_id}
Authorization: Bearer <token>
```

### Update Knowledge Base
```http
PATCH /knowledge-bases/{kb_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Name",
  "description": "New description"
}
```

### Delete Knowledge Base
```http
DELETE /knowledge-bases/{kb_id}
Authorization: Bearer <token>
```

### Add Documents to KB
```http
POST /knowledge-bases/{kb_id}/documents
Authorization: Bearer <token>
Content-Type: application/json

{ "document_ids": ["doc-id-1", "doc-id-2"] }
```

### Remove Document from KB
```http
DELETE /knowledge-bases/{kb_id}/documents/{doc_id}
Authorization: Bearer <token>
```

### Get KB Stats
```http
GET /knowledge-bases/{kb_id}/stats
Authorization: Bearer <token>
```

## Retrieval

### Vector Search
```http
POST /retrieval/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "search query",
  "top_k": 10,
  "minimum_score": 0.3,
  "filters": { "category": "technical" }
}
```

### Hybrid Search
```http
POST /retrieval/hybrid-search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "search query",
  "top_k": 10,
  "alpha": 0.5,
  "use_rrf": true,
  "rrf_k": 60
}
```

### Cross-Encoder Reranking
```http
POST /retrieval/rerank
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "search query",
  "documents": [
    { "id": "1", "text": "Document 1 text" },
    { "id": "2", "text": "Document 2 text" }
  ],
  "top_k": 5
}
```

### Query Expansion
```http
POST /retrieval/expand-query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "original query",
  "max_expansions": 3
}
```

### Context Compression
```http
POST /retrieval/compress-context
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "query for context",
  "documents": [
    { "id": "1", "text": "Long document text..." }
  ],
  "max_tokens": 8000
}
```

## RAG (Retrieval-Augmented Generation)

### Non-Streaming Query
```http
POST /rag/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "What is the return policy?",
  "top_k": 5,
  "minimum_score": 0.3,
  "conversation_id": "optional-conv-id",
  "filters": { "category": "policy" }
}
```

**Response:**
```json
{
  "answer": "The return policy allows returns within 30 days...",
  "citations": [
    {
      "document_id": "doc-id",
      "chunk_id": "chunk-id",
      "text": "Returns within 30 days...",
      "score": 0.92
    }
  ],
  "confidence": 0.89,
  "sources_found": 3,
  "response_time_ms": 1250
}
```

### Streaming Query (SSE)
```http
POST /rag/stream
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "What is the return policy?",
  "top_k": 5
}
```

**Events:**
- `start` - Streaming started
- `retrieval` - Retrieval completed
- `token` - Individual tokens
- `citations` - Citation data
- `complete` - Final response with metadata
- `error` - Error event

## Chat

### Non-Streaming Chat
```http
POST /chat/ask
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "Hello, how can you help?",
  "top_k": 5,
  "minimum_score": 0.3
}
```

### Streaming Chat (SSE)
```http
POST /chat/stream
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "Hello, how can you help?",
  "top_k": 5
}
```

### Streaming Health Check
```http
GET /chat/stream/health
Authorization: Bearer <token>
```

## Conversations

### Create Conversation
```http
POST /conversations
Authorization: Bearer <token>
Content-Type: application/json

{ "title": "Conversation Title" }
```

### List Conversations
```http
GET /conversations
Authorization: Bearer <token>
```

### Get Conversation
```http
GET /conversations/{conversation_id}
Authorization: Bearer <token>
```

### Send Message
```http
POST /conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "user",
  "content": "Message content"
}
```

### Get Messages
```http
GET /conversations/{conversation_id}/messages
Authorization: Bearer <token>
```

### Delete Conversation
```http
DELETE /conversations/{conversation_id}
Authorization: Bearer <token>
```

## Health & Monitoring

### Health Check (Public)
```http
GET /health
```

### Detailed Health
```http
GET /api/v1/health
Authorization: Bearer <token>
```

### Ollama Health
```http
GET /api/v1/ollama/health
Authorization: Bearer <token>
```

### List Models
```http
GET /api/v1/ollama/models
Authorization: Bearer <token>
```

## Error Responses

All errors follow this format:
```json
{
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}
```

### Common Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request / Validation Error
- `401` - Unauthorized
- `403` - Forbidden (permission denied)
- `404` - Not Found
- `409` - Conflict (duplicate)
- `413` - Payload Too Large
- `415` - Unsupported Media Type
- `422` - Unprocessable Entity
- `429` - Rate Limited
- `500` - Internal Server Error
- `503` - Service Unavailable

### Rate Limit Headers
- `X-RateLimit-Limit` - Request limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Unix timestamp when limit resets
- `Retry-After` - Seconds until retry allowed

## Permissions Reference

| Permission | Description | Roles |
|------------|-------------|-------|
| `UPLOAD_DOCUMENTS` | Upload documents | Editor, Manager, Admin |
| `DELETE_DOCUMENTS` | Delete documents | Manager, Admin |
| `CHAT` | Use chat/RAG | Viewer, Editor, Manager, Admin |
| `VIEW_SESSIONS` | View conversation history | Viewer, Editor, Manager, Admin |
| `MANAGE_USERS` | Manage organization users | Manager, Admin |
| `MANAGE_SETTINGS` | Manage organization settings | Admin |

## Roles Hierarchy

```
Admin (all permissions)
  └── Manager (manage users + all editor permissions)
       └── Editor (upload, delete docs, chat, view sessions)
            └── Viewer (chat, view sessions only)
```