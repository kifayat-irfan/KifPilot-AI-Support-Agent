from app.database.base import Base, BaseModel
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, Table, Column, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from uuid import uuid4
import enum


class DocumentStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(str, enum.Enum):
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    CHAT = "chat"
    VIEW_SESSIONS = "view_sessions"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


# Association table for user-role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


# Association table for role-permission many-to-many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# Association table for organization-members many-to-many relationship
organization_members = Table(
    "organization_members",
    Base.metadata,
    Column("organization_id", String(36), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role", SQLEnum(OrganizationRole), nullable=False, default=OrganizationRole.MEMBER),
    Column("joined_at", DateTime, default=datetime.utcnow, nullable=False),
)


class Organization(Base, BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    members: Mapped[list["User"]] = relationship(
        secondary=organization_members, back_populates="organizations", lazy="selectin"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("slug", name="uq_organizations_slug"),
    )


class OrganizationSettings(Base, BaseModel):
    __tablename__ = "organization_settings"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # RAG settings
    default_top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    default_min_score: Mapped[float] = mapped_column(default=0.65, nullable=False)
    default_max_context: Mapped[int] = mapped_column(Integer, default=8000, nullable=False)
    # Chat settings
    max_message_history: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    max_tokens_context: Mapped[int] = mapped_column(Integer, default=8000, nullable=False)
    # Vector store settings
    embedding_model: Mapped[str] = mapped_column(String(100), default="nomic-embed-text", nullable=False)
    # Feature flags
    enable_streaming: Mapped[bool] = mapped_column(default=True, nullable=False)
    enable_citations: Mapped[bool] = mapped_column(default=True, nullable=False)
    enable_conversation_memory: Mapped[bool] = mapped_column(default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="settings")


# Add settings relationship to Organization
Organization.settings = relationship(
    "OrganizationSettings", back_populates="organization", cascade="all, delete-orphan", uselist=False, lazy="selectin"
)


class Document(Base, BaseModel):
    __tablename__ = "documents"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADING, nullable=False
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embeddings_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base, BaseModel):
    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class User(Base, BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )
    organizations: Mapped[list["Organization"]] = relationship(
        secondary=organization_members, back_populates="members", lazy="selectin"
    )


class Role(Base, BaseModel):
    __tablename__ = "roles"

    name: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles, back_populates="roles", lazy="selectin"
    )
    permissions: Mapped[list["PermissionModel"]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )


class PermissionModel(Base, BaseModel):
    __tablename__ = "permissions"

    name: Mapped[Permission] = mapped_column(SQLEnum(Permission), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions, back_populates="permissions", lazy="selectin"
    )


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base, BaseModel):
    __tablename__ = "chat_sessions"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )


class ChatMessage(Base, BaseModel):
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")