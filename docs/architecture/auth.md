# Authentication Flow

## Overview

JWT-based authentication with access/refresh token pattern, bcrypt password hashing, and role-based access control.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  /auth/login │────▶│  Validate   │────▶│  Generate   │
│             │     │   Endpoint   │     │  Credentials│     │  JWT Pair   │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                     │
                    ┌─────────────┐     ┌─────────────┐              │
                    │  Client     │◀────│  Return     │◀─────────────┘
                    │  Stores     │     │  Tokens     │
                    │  Tokens     │     └─────────────┘
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     ┌─────────────┐     ┌─────────────┐
                    │  Request    │────▶│  Extract    │────▶│  Verify     │
                    │  with Bearer│     │  Token      │     │  Signature  │
                    │  Token      │     └─────────────┘     └──────┬──────┘
                    └─────────────┘                                 │
                                                                     ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │  Access     │◀────│  Check      │◀────│  Load User  │
                    │  Granted    │     │  Expiry     │     │  & Perms    │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

## Token Structure

### Access Token (Short-lived: 30 min)

```json
{
  "header": { "alg": "HS256", "typ": "JWT" },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "username": "username",
    "org_id": "org-uuid",
    "roles": ["editor"],
    "permissions": ["UPLOAD_DOCUMENTS", "CHAT", "VIEW_SESSIONS"],
    "type": "access",
    "iat": 1699900000,
    "exp": 1699901800
  },
  "signature": "HMACSHA256(base64UrlEncode(header) + '.' + base64UrlEncode(payload), SECRET_KEY)"
}
```

### Refresh Token (Long-lived: 7 days)

```json
{
  "sub": "user-uuid",
  "type": "refresh",
  "iat": 1699900000,
  "exp": 1700504800
}
```

## Login Flow

```python
# services/auth/service.py
class AuthService:
    async def login(self, email: str, password: str) -> TokenPair:
        # 1. Get user by email
        user = await self.repo.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError()
        
        # 2. Verify password (bcrypt)
        if not verify_password(password, user.hashed_password):
            await self.audit.log_login_failed(email, user.organization_id)
            raise InvalidCredentialsError()
        
        # 3. Check user active
        if not user.is_active:
            raise InactiveUserError()
        
        # 4. Generate tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "org_id": str(user.organization_id),
            "roles": [r.name for r in user.roles],
            "permissions": [p.name for p in user.permissions]
        })
        
        refresh_token = create_refresh_token(str(user.id))
        
        # 5. Store refresh token hash (optional: for revocation)
        await self.repo.store_refresh_token_hash(user.id, hash_token(refresh_token))
        
        # 6. Audit log
        await self.audit.log_login(user.id, user.email, user.organization_id, success=True)
        
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
```

## Token Verification

```python
# core/security.py
def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True}
        )
        return payload
    except JWTError:
        return None

def get_token_type(token: str) -> Optional[str]:
    payload = verify_token(token)
    return payload.get("type") if payload else None
```

## Protected Endpoint Dependencies

```python
# services/auth/dependencies.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> str:
    credentials_exception = HTTPException(401, "Could not validate credentials")
    
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Verify user exists and active
    user = await auth_service.repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise credentials_exception
    
    return user_id

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    user = await auth_service.repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_permission(permission: Permission):
    async def checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_perm = await auth_service.repo.user_has_permission(current_user.id, permission)
        if not has_perm:
            raise HTTPException(403, f"Permission denied: {permission.value}")
        return current_user
    return checker

def require_role(role: UserRole):
    async def checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_role = await auth_service.repo.user_has_role(current_user.id, role)
        if not has_role:
            raise HTTPException(403, f"Role required: {role.value}")
        return current_user
    return checker
```

## Token Refresh Flow

```
Client                          Server
  │                                │
  ├─ POST /auth/refresh ─────────► │
  │  Authorization: Bearer <refresh>│
  │                                ├─ Verify refresh token
  │                                ├─ Check not revoked
  │                                ├─ Generate new access token
  │                                │
  │ ◄── 200 { access_token } ──────┤
  │                                │
```

```python
async def refresh_token(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    payload = verify_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    
    # Check revocation (if implemented)
    user_id = payload.get("sub")
    stored_hash = await auth_service.repo.get_refresh_token_hash(user_id)
    if stored_hash and not verify_token_hash(token, stored_hash):
        raise HTTPException(401, "Token revoked")
    
    user = await auth_service.repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    
    new_access = create_access_token(user)
    return TokenResponse(access_token=new_access, token_type="bearer")
```

## Password Security

```python
# core/security.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# Password requirements (configurable)
MIN_LENGTH = 12
REQUIRE_UPPER = True
REQUIRE_LOWER = True
REQUIRE_DIGIT = True
REQUIRE_SYMBOL = True
```

## Logout & Revocation

```python
# Optional: Token blacklist for immediate revocation
class TokenBlacklist:
    def __init__(self):
        self._blacklist: Dict[str, float] = {}  # token_hash -> expiry
    
    def add(self, token: str, expires_at: float):
        self._blacklist[hash_token(token)] = expires_at
    
    def is_blacklisted(self, token: str) -> bool:
        token_hash = hash_token(token)
        if token_hash in self._blacklist:
            if self._blacklist[token_hash] > time.time():
                return True
            del self._blacklist[token_hash]
        return False
```

## Audit Logging

```python
# Every auth event logged
await audit_logger.log_login(
    user_id=user.id,
    username=user.username,
    organization_id=user.organization_id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    success=True
)

await audit_logger.log_login_failed(
    email=email,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    error="Invalid credentials"
)

await audit_logger.log_logout(user_id, username, org_id, ip)
await audit_logger.log_token_refresh(user_id, ip)
await audit_logger.log_password_change(user_id, ip)
```

## Security Considerations

| Threat | Mitigation |
|--------|------------|
| Brute force | Rate limit (5/min login), account lockout |
| Token theft | Short access tokens (30min), HTTPS only, Secure/HttpOnly cookies optional |
| Replay attacks | JWT exp/iat validation, token blacklist for revocation |
| Password breach | bcrypt (12 rounds), password requirements, breach detection |
| Token leakage | No tokens in URLs, Authorization header only, short expiry |
| Privilege escalation | Permission checks on every request, role hierarchy validation |