import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.core.config import get_settings
from app.core.database import init_database, close_database, get_db_session
from app.database.models import User, Organization, UserRole, Permission
from app.services.auth.service import AuthService
from app.services.auth.repository import AuthRepository
from app.core.security import hash_password
import uuid


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def app():
    settings = get_settings()
    settings.APP_ENV = "test"
    settings.DEBUG = True
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    app = create_app()
    await init_database()
    yield app
    await close_database()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async for session in get_db_session():
        yield session


@pytest.fixture
async def test_organization(db_session):
    org = Organization(
        name="Test Organization",
        slug="test-org",
        description="Test organization for integration tests",
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_user(db_session, test_organization):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    auth_repo = AuthRepository(db_session)
    admin_role = await auth_repo.get_role_by_name(UserRole.ADMIN)
    if admin_role:
        await auth_repo.assign_role_to_user(user.id, admin_role.id)
    
    return user


@pytest.fixture
async def auth_headers(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_admin(db_session, test_organization):
    admin = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    
    auth_repo = AuthRepository(db_session)
    admin_role = await auth_repo.get_role_by_name(UserRole.ADMIN)
    if admin_role:
        await auth_repo.assign_role_to_user(admin.id, admin_role.id)
    
    return admin


@pytest.fixture
async def admin_headers(client, test_admin):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}