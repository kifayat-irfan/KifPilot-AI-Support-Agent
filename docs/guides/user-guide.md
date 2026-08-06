# User Guide

## Getting Started

### First Login

1. Navigate to your organization's KifPilot URL
2. Enter your email and password
3. Complete any required MFA steps
4. You'll land on the Dashboard

### Interface Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  KifPilot AI Support Agent                    [User Menu] [Bell] │
├────────────┬────────────────────────────────────────────────────┤
│            │                                                    │
│  Dashboard │  Main content area                                │
│  Documents │                                                    │
│  Knowledge │                                                    │
│  Chat      │                                                    │
│  Settings  │                                                    │
│            │                                                    │
│  Admin*    │  * Only for Admin/Manager roles                   │
└────────────┴────────────────────────────────────────────────────┘
```

## Dashboard

The dashboard provides an overview of your organization's activity:

- **Statistics Cards**: Document count, KB count, active conversations, queries today
- **Recent Activity**: Latest uploads, chats, user actions
- **Quick Actions**: Upload document, create KB, start chat

---

## Managing Documents

### Uploading Documents

1. Click **Documents** in the sidebar
2. Click **Upload Document**
3. Select file(s) - Supported formats:
   - **PDF** (.pdf)
   - **Word** (.docx, .doc)
   - **Text** (.txt, .md)
   - **Data** (.csv, .json, .xml)
   - **Web** (.html)
4. Add optional metadata:
   - **Title**: Document title
   - **Description**: Brief summary
   - **Category**: Organize by topic (e.g., "Policies", "Technical", "HR")
   - **Tags**: Comma-separated keywords
   - **Language**: ISO 639-1 code (en, es, fr, de, etc.)
5. Click **Upload**

### Document Processing

Documents are automatically processed:
1. Text extraction
2. Intelligent chunking (1000 tokens, 200 overlap)
3. Embedding generation
4. Vector storage in ChromaDB
5. BM25 index update

Processing typically takes a few seconds per document.

### Managing Documents

- **Search**: Filter by keyword, category, language, status
- **Sort**: By date, name, size, status
- **Actions**: View details, edit metadata, download, delete, restore

### Deleting & Restoring

- **Soft Delete**: Moves to trash (default)
- **Hard Delete**: Permanently removes document and vectors
- **Restore**: Recover from trash within 30 days

---

## Knowledge Bases

### Creating a Knowledge Base

1. Click **Knowledge Base** in sidebar
2. Click **Create Knowledge Base**
3. Enter:
   - **Name**: Descriptive name (e.g., "HR Policies", "Product Docs")
   - **Description**: Purpose and scope
   - **Embedding Model**: Usually `nomic-embed-text`
4. Click **Create**

### Managing KB Content

1. Open a Knowledge Base
2. Click **Add Documents**
3. Select documents from your organization
4. Documents are indexed specifically for this KB

### KB Statistics

View:
- Document count
- Chunk count
- Embedding model
- Last updated
- Storage size

---

## Chat & RAG

### Starting a Chat

1. Click **Chat** in sidebar
2. Click **New Conversation**
3. Enter a title
4. Start asking questions!

### Asking Questions

The AI uses RAG (Retrieval-Augmented Generation):
1. Your question is analyzed
2. Relevant documents are retrieved (hybrid search + reranking)
3. Context is compressed to fit token limits
4. Answer is generated with citations
5. Streaming response shows tokens in real-time

### Understanding Responses

Each response includes:
- **Answer**: The generated response
- **Citations**: Source documents with relevance scores
- **Confidence**: How confident the AI is (0-1)
- **Sources Found**: Number of documents used

### Using Citations

Click any citation to:
- View source text snippet
- Open full document
- Navigate to relevant chunk

### Streaming vs Non-Streaming

- **Streaming** (default): See tokens as they're generated
- **Non-Streaming**: Get complete response at once

---

## Conversations

### Managing Conversations

- **Create**: New conversation button
- **Switch**: Click conversation in sidebar
- **Rename**: Click title to edit
- **Delete**: Remove unwanted conversations
- **History**: All messages preserved

### Context Awareness

The AI remembers conversation context:
- Follow-up questions reference previous answers
- Previous context is automatically included
- Works across conversation sessions

---

## Settings

### Profile Settings

- **Full Name**: Display name
- **Email**: Login email (contact admin to change)
- **Password**: Change password
- **Notifications**: Email preferences

### Organization Settings (Admin/Manager)

- **General**: Name, description, timezone
- **Members**: Invite, remove, change roles
- **Integrations**: Webhooks, API keys
- **Security**: Password policies, session timeouts

---

## Tips & Best Practices

### Document Preparation

1. **Clean text**: Remove headers/footers, page numbers
2. **Structure**: Use headings, bullet points
3. **Metadata**: Add meaningful titles, categories, tags
4. **Size**: Optimal < 50MB per document

### Effective Questions

- Be specific: "What is the refund policy for digital products?"
- Provide context: "For enterprise customers in EU..."
- Ask follow-ups: "What about partial refunds?"

### Knowledge Base Organization

- Separate KBs by domain (HR, Technical, Legal)
- Use consistent naming conventions
- Regular cleanup of outdated documents

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No results found | Check document upload status, try broader query |
| Slow response | Reduce `top_k`, check KB size |
| Low confidence | Add more relevant documents |
| Citation missing | Verify document processing completed |
| Upload failed | Check file type, size (< 50MB) |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Focus search |
| `Ctrl/Cmd + N` | New conversation |
| `Ctrl/Cmd + Enter` | Send message |
| `Escape` | Close modal/cancel |

---

## Support

- **Documentation**: This guide + [API Reference](../api/reference.md)
- **Issues**: [GitHub Issues](https://github.com/kifpilot/ai-support-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kifpilot/ai-support-agent/discussions)
- **Admin Contact**: Your organization administrator