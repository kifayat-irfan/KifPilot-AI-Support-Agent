from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from app.database.models import OrganizationRole


class OrganizationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Organization description")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0


class OrganizationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizations: List[OrganizationResponse]
    total: int
    page: int
    page_size: int


class OrganizationMemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="User ID to add")
    role: OrganizationRole = Field(default=OrganizationRole.MEMBER, description="Member role")


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    user_id: str
    username: str
    email: EmailStr
    role: OrganizationRole
    joined_at: datetime


class OrganizationSettingsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_top_k: int = Field(default=5, ge=1, le=20)
    default_min_score: float = Field(default=0.65, ge=0.0, le=1.0)
    default_max_context: int = Field(default=8000, ge=500, le=32000)
    max_message_history: int = Field(default=20, ge=1, le=100)
    max_tokens_context: int = Field(default=8000, ge=1000, le=32000)
    embedding_model: str = Field(default="nomic-embed-text", max_length=100)
    enable_streaming: bool = Field(default=True)
    enable_citations: bool = Field(default=True)
    enable_conversation_memory: bool = Field(default=True)


class OrganizationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_top_k: Optional[int] = Field(None, ge=1, le=20)
    default_min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    default_max_context: Optional[int] = Field(None, ge=500, le=32000)
    max_message_history: Optional[int] = Field(None, ge=1, le=100)
    max_tokens_context: Optional[int] = Field(None, ge=1000, le=32000)
    embedding_model: Optional[str] = Field(None, max_length=100)
    enable_streaming: Optional[bool] = None
    enable_citations: Optional[bool] = None
    enable_conversation_memory: Optional[bool] = None


class OrganizationSettingsResponse(OrganizationSettingsBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class OrganizationWithMembers(OrganizationResponse):
    model_config = ConfigDict(extra="forbid")

    members: List[OrganizationMemberResponse] = []
    settings: Optional[OrganizationSettingsResponse] = None