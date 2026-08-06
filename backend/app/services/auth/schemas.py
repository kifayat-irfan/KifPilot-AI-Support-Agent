from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from app.database.models import UserRole, Permission


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=100, description="Username")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Password")


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = Field(None, description="User email")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Username")
    is_active: Optional[bool] = Field(None, description="User active status")


class UserResponse(UserBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    roles: List["RoleResponse"] = []


class RoleBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: UserRole
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = None


class RoleResponse(RoleBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    permissions: List["PermissionResponse"] = []


class PermissionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Permission
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str
    exp: int
    type: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class RegisterRequest(UserCreate):
    pass


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


UserResponse.model_rebuild()
RoleResponse.model_rebuild()
PermissionResponse.model_rebuild()