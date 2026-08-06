# Multi-Tenant Architecture

## Overview

Complete organization isolation with shared infrastructure, row-level security, and per-tenant quotas.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
                        SHARED INFRASTRUCTURE
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
  │  FastAPI App    │  │  PostgreSQL     │  │  ChromaDB Cluster       │
  │  (Stateless)    │  │  (Multi-tenant) │  │  (Namespaced Collections)│
  └─────────────────┘  └─────────────────┘  └─────────────────────────┘
         │                      │                       │
         └──────────────────────┼───────────────────────┘
                                │
         ┌──────────────────────┼───────────────────────┐
         ▼                      ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Organization A │    │  Organization B │    │  Organization N │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ Users     │  │    │  │ Users     │  │    │  │ Users     │  │
│  │ Documents │  │    │  │ Documents │  │    │  │ Documents │  │
│  │ KBs       │  │    │  │ KBs       │  │    │  │ KBs       │  │
│  │ Vectors   │  │    │  │ Vectors   │  │    │  │ Vectors   │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Database Isolation

### Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on all tenant tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Policy: users only see their organization's data
CREATE POLICY org_isolation ON documents
    FOR ALL TO application_role
    USING (organization_id = current_setting('app.current_org_id')::uuid)
    WITH CHECK (organization_id = current_setting('app.current_org_id')::uuid);

-- Application sets org context per request
SET LOCAL app.current_org_id = 'org-uuid-here';
```

### Application-Level Filtering

```python
# All repository queries auto-filter by organization
class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _org_filter(self, stmt: Select, org_id: str) -> Select:
        return stmt.where(Document.organization_id == org_id)
    
    async def list(self, org_id: str, filters: DocumentFilters) -> List[Document]:
        stmt = select(Document)
        stmt = self._org_filter(stmt, org_id)
        if filters.category:
            stmt = stmt.where(Document.category == filters.category)
        return await self.session.execute(stmt)
```

## Vector Store Isolation

### Namespaced Collections

```python
# services/vectorstore/service.py
class VectorStoreService:
    def _get_collection_name(self, kb_id: str, org_id: str) -> str:
        """Generate unique collection name per KB per organization"""
        return f"org_{org_id}_kb_{kb_id}"
    
    async def add_documents(self, kb_id: str, org_id: str, documents: List[VectorDoc]):
        collection_name = self._get_collection_name(kb_id, org_id)
        collection = await self.client.get_or_create_collection(collection_name)
        await collection.add(
            ids=[d.id for d in documents],
            embeddings=[d.embedding for d in documents],
            metadatas=[d.metadata for d in documents],
            documents=[d.text for d in documents]
        )
    
    async def search(self, kb_id: str, org_id: str, query_vector: List[float], top_k: int):
        collection_name = self._get_collection_name(kb_id, org_id)
        collection = await self.client.get_collection(collection_name)
        return await collection.query(query_embeddings=[query_vector], n_results=top_k)
```

### Collection Management

```python
# One collection per Knowledge Base per Organization
# Naming: org_{org_id}_kb_{kb_id}
# Metadata includes: org_id, kb_id, document_id, chunk_index

async def create_kb_collection(self, kb_id: str, org_id: str) -> str:
    name = self._get_collection_name(kb_id, org_id)
    collection = await self.client.create_collection(
        name=name,
        metadata={
            "organization_id": org_id,
            "knowledge_base_id": kb_id,
            "created_at": datetime.utcnow().isoformat()
        },
        embedding_function=None  # We provide embeddings
    )
    return collection.name

async def delete_kb_collection(self, kb_id: str, org_id: str):
    name = self._get_collection_name(kb_id, org_id)
    await self.client.delete_collection(name)
```

## Quota Management

### Per-Organization Limits

```python
# services/multitenant/schemas.py
class OrganizationQuotas:
    MAX_DOCUMENTS: int = 10_000
    MAX_KNOWLEDGE_BASES: int = 50
    MAX_CONVERSATIONS: int = 1_000
    MAX_STORAGE_BYTES: int = 10 * 1024 * 1024 * 1024  # 10 GB
    MAX_DAILY_QUERIES: int = 10_000
    MAX_FILE_SIZE_MB: int = 50
    MAX_CONCURRENT_STREAMS: int = 5

# Configurable per organization
class OrganizationSettings(BaseModel):
    quotas: OrganizationQuotas = OrganizationQuotas()
    default_embedding_model: str = "nomic-embed-text"
    default_chat_model: str = "qwen3.5:4b"
    retention_days: int = 365
    features: Dict[str, bool] = {
        "reranker": True,
        "query_expansion": True,
        "streaming": True
    }
```

### Quota Enforcement

```python
# services/multitenant/service.py
class MultitenantService:
    async def check_quota(self, org_id: str, resource: str, amount: int = 1) -> bool:
        quotas = await self.get_quotas(org_id)
        current = await self.get_usage(org_id, resource)
        
        if current + amount > getattr(quotas, f"MAX_{resource.upper()}"):
            raise QuotaExceededError(f"Quota exceeded for {resource}")
        return True
    
    async def increment_usage(self, org_id: str, resource: str, amount: int = 1):
        # Atomic increment in Redis or DB
        await self.redis.hincrby(f"org:{org_id}:usage", resource, amount)
    
    async def get_usage(self, org_id: str, resource: str) -> int:
        val = await self.redis.hget(f"org:{org_id}:usage", resource)
        return int(val) if val else 0
```

## Organization Context

### Request-Scoped Organization

```python
# presentation/api/v1/dependencies.py
async def get_current_organization_id(
    current_user: User = Depends(get_current_active_user)
) -> str:
    if not current_user.organization_id:
        raise HTTPException(403, "User not associated with any organization")
    return current_user.organization_id

# Usage in routes
@router.post("/documents/upload")
async def upload(
    file: UploadFile = File(...),
    org_id: str = Depends(get_current_organization_id),
    service: DocumentService = Depends(get_document_service)
):
    # Quota check
    await multitenant_service.check_quota(org_id, "documents")
    await multitenant_service.check_quota(org_id, "storage", file_size)
    
    doc = await service.upload(file, org_id)
    
    # Increment usage
    await multitenant_service.increment_usage(org_id, "documents")
    await multitenant_service.increment_usage(org_id, "storage", file_size)
    
    return doc
```

## User Membership

### Organization Members

```python
# database/models.py
class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    user_id = Column(UUID, ForeignKey("users.id"), primary_key=True)
    organization_id = Column(UUID, ForeignKey("organizations.id"), primary_key=True)
    role_id = Column(UUID, ForeignKey("roles.id"))
    invited_by = Column(UUID, ForeignKey("users.id"))
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)
    status = Column(Enum(MemberStatus), default=MemberStatus.PENDING)
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    role = relationship("Role")

class MemberStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
```

### Member Management

```python
# services/multitenant/service.py
class MultitenantService:
    async def invite_member(
        self,
        org_id: str,
        email: str,
        role: UserRole,
        invited_by: str
    ) -> OrganizationMember:
        # Check inviter has MANAGE_USERS
        # Find or create user
        # Create membership with PENDING status
        # Send invitation email
        # Audit log
        ...
    
    async def accept_invitation(self, user_id: str, org_id: str):
        # Update status to ACTIVE
        # Set joined_at
        # Assign role
        # Audit log
        ...
    
    async def remove_member(self, org_id: str, user_id: str, removed_by: str):
        # Check remover has MANAGE_USERS
        # Soft delete membership
        # Revoke roles
        # Audit log
        ...
    
    async def change_member_role(self, org_id: str, user_id: str, new_role: UserRole, changed_by: str):
        # Check changer has MANAGE_USERS
        # Update role in user_roles
        # Audit log (role_change)
        ...
```

## Cross-Organization Operations Prevention

```python
# Middleware to prevent cross-org access
class MultiTenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract org_id from authenticated user
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            org_id = await self.get_user_org(user_id)
            request.state.organization_id = org_id
            
            # Set RLS context for database
            async with get_db_session() as session:
                await session.execute(
                    text("SET LOCAL app.current_org_id = :org_id"),
                    {"org_id": org_id}
                )
        
        return await call_next(request)

# Validation in services
class DocumentService:
    async def get_document(self, doc_id: str, org_id: str) -> Document:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.organization_id != org_id:
            raise DocumentNotFoundError(doc_id)
        return doc
```

## Admin Cross-Org Access (System Admin Only)

```python
# System admins can manage all organizations
@router.get("/admin/organizations")
async def list_all_organizations(
    current_user: User = Depends(require_admin),
    multitenant: MultitenantService = Depends(get_multitenant_service)
):
    return await multitenant.list_all_organizations()

@router.get("/admin/organizations/{org_id}/usage")
async def get_org_usage(
    org_id: str,
    current_user: User = Depends(require_admin),
    multitenant: MultitenantService = Depends(get_multitenant_service)
):
    return await multitenant.get_usage_stats(org_id)
```

## Testing Multi-Tenancy

```python
# tests/integration/test_multitenant.py
class TestMultiTenancy:
    @pytest.mark.asyncio
    async def test_org_isolation(self, client, auth_headers_a, auth_headers_b):
        # User A uploads doc
        doc_a = await upload(client, auth_headers_a, "doc_a.txt")
        
        # User B cannot see User A's doc
        resp = await client.get(f"/documents/{doc_a['id']}", headers=auth_headers_b)
        assert resp.status_code == 404
    
    @pytest.mark.asyncio
    async def test_quota_enforcement(self, client, auth_headers):
        # Fill quota
        for i in range(10000):
            resp = await upload(client, auth_headers, f"doc_{i}.txt")
            if resp.status_code == 429:  # Quota exceeded
                break
        else:
            pytest.fail("Quota not enforced")
    
    @pytest.mark.asyncio
    async def test_vector_isolation(self, vector_service, org_a, org_b):
        await vector_service.add_documents("kb1", org_a, [...])
        await vector_service.add_documents("kb1", org_b, [...])
        
        # Search org_a
        results_a = await vector_service.search("kb1", org_a, query_vec, 5)
        assert all(r.metadata["organization_id"] == org_a for r in results_a)
        
        # Search org_b
        results_b = await vector_service.search("kb1", org_b, query_vec, 5)
        assert all(r.metadata["organization_id"] == org_b for r in results_b)
```