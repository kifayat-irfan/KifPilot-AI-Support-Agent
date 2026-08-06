import os
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import pytest
import asyncio


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    context = await browser.new_context()
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext):
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def authenticated_page(page: Page):
    """Login and return authenticated page"""
    await page.goto(f"{BASE_URL}/login")
    await page.fill('input[name="email"]', "test@example.com")
    await page.fill('input[name="password"]', "testpassword123")
    await page.click('button[type="submit"]')
    await page.wait_for_url(f"{BASE_URL}/dashboard")
    return page


class TestUserRegistration:
    @pytest.mark.asyncio
    async def test_register_new_user(self, page: Page):
        await page.goto(f"{BASE_URL}/register")
        
        await page.fill('input[name="email"]', "e2etest@example.com")
        await page.fill('input[name="username"]', "e2etestuser")
        await page.fill('input[name="password"]', "password123")
        await page.fill('input[name="confirmPassword"]', "password123")
        await page.fill('input[name="fullName"]', "E2E Test User")
        
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        
        # Verify logged in
        await page.goto(f"{BASE_URL}/dashboard")
        assert await page.is_visible("text=Dashboard")


class TestLoginLogout:
    @pytest.mark.asyncio
    async def test_login_success(self, page: Page):
        await page.goto(f"{BASE_URL}/login")
        
        await page.fill('input[name="email"]', "test@example.com")
        await page.fill('input[name="password"]', "testpassword123")
        await page.click('button[type="submit"]')
        
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        assert await page.is_visible("text=Dashboard")

    @pytest.mark.asyncio
    async def test_login_failure(self, page: Page):
        await page.goto(f"{BASE_URL}/login")
        
        await page.fill('input[name="email"]', "test@example.com")
        await page.fill('input[name="password"]', "wrongpassword")
        await page.click('button[type="submit"]')
        
        # Should show error
        await page.wait_for_selector("text=Invalid credentials")

    @pytest.mark.asyncio
    async def test_logout(self, authenticated_page: Page):
        # Click user menu
        await authenticated_page.click('[data-testid="user-menu"]')
        await authenticated_page.click('text=Logout')
        
        await authenticated_page.wait_for_url(f"{BASE_URL}/login")
        assert await authenticated_page.is_visible('input[name="email"]')


class TestProtectedRoutes:
    @pytest.mark.asyncio
    async def test_redirect_to_login(self, page: Page):
        await page.goto(f"{BASE_URL}/dashboard")
        await page.wait_for_url(f"{BASE_URL}/login")

    @pytest.mark.asyncio
    async def test_access_with_token(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/dashboard")
        assert await authenticated_page.is_visible("text=Dashboard")
        
        await authenticated_page.goto(f"{BASE_URL}/documents")
        assert await authenticated_page.is_visible("text=Documents")


class TestOrganizationCreation:
    @pytest.mark.asyncio
    async def test_create_organization(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/organizations")
        
        await authenticated_page.click('text=Create Organization')
        await authenticated_page.fill('input[name="name"]', "E2E Test Org")
        await authenticated_page.fill('input[name="slug"]', "e2e-test-org")
        await authenticated_page.fill('textarea[name="description"]', "Created via E2E test")
        await authenticated_page.click('button[type="submit"]')
        
        await authenticated_page.wait_for_selector("text=E2E Test Org")
        assert await authenticated_page.is_visible("text=E2E Test Org")


class TestDocumentUpload:
    @pytest.mark.asyncio
    async def test_upload_document(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/documents")
        
        await authenticated_page.click('text=Upload Document')
        
        # Create a test file
        await authenticated_page.set_input_files('input[type="file"]', {
            "name": "test.txt",
            "mimeType": "text/plain",
            "buffer": b"E2E test document content"
        })
        
        await authenticated_page.fill('input[name="title"]', "E2E Test Document")
        await authenticated_page.click('button[type="submit"]')
        
        await authenticated_page.wait_for_selector("text=E2E Test Document")
        assert await authenticated_page.is_visible("text=E2E Test Document")

    @pytest.mark.asyncio
    async def test_upload_invalid_file(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/documents")
        
        await authenticated_page.click('text=Upload Document')
        
        # Try to upload an executable
        await authenticated_page.set_input_files('input[type="file"]', {
            "name": "test.exe",
            "mimeType": "application/x-msdownload",
            "buffer": b"MZ\x90\x00"
        })
        
        await authenticated_page.click('button[type="submit"]')
        
        # Should show error
        await authenticated_page.wait_for_selector("text=not allowed")


class TestKnowledgeBase:
    @pytest.mark.asyncio
    async def test_create_knowledge_base(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/knowledge-base")
        
        await authenticated_page.click('text=Create Knowledge Base')
        await authenticated_page.fill('input[name="name"]', "E2E Knowledge Base")
        await authenticated_page.fill('textarea[name="description"]', "Test KB")
        await authenticated_page.click('button[type="submit"]')
        
        await authenticated_page.wait_for_selector("text=E2E Knowledge Base")
        assert await authenticated_page.is_visible("text=E2E Knowledge Base")


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_documents(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/documents")
        
        await authenticated_page.fill('input[placeholder*="Search"]', "test")
        await authenticated_page.press('input[placeholder*="Search"]', "Enter")
        
        await authenticated_page.wait_for_load_state("networkidle")
        # Results should be filtered


class TestChat:
    @pytest.mark.asyncio
    async def test_send_chat_message(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/chat")
        
        await authenticated_page.fill('textarea[placeholder*="Message"]', "Hello, this is an E2E test")
        await authenticated_page.click('button:has-text("Send")')
        
        # Wait for response
        await authenticated_page.wait_for_selector("text=Hello, this is an E2E test")
        
        # Should have assistant response
        await authenticated_page.wait_for_selector('[data-role="assistant"]', timeout=30000)


class TestStreaming:
    @pytest.mark.asyncio
    async def test_streaming_chat(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/chat")
        
        await authenticated_page.fill('textarea[placeholder*="Message"]', "Stream this response")
        await authenticated_page.click('button:has-text("Send")')
        
        # Check for streaming indicator
        await authenticated_page.wait_for_selector('[data-streaming="true"]', timeout=5000)
        
        # Wait for completion
        await authenticated_page.wait_for_selector('[data-streaming="false"]', timeout=30000)


class TestCitationPanel:
    @pytest.mark.asyncio
    async def test_citation_panel_display(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/chat")
        
        await authenticated_page.fill('textarea[placeholder*="Message"]', "What is in the knowledge base?")
        await authenticated_page.click('button:has-text("Send")')
        
        await authenticated_page.wait_for_selector('[data-role="assistant"]', timeout=30000)
        
        # Click on citation
        citation_button = authenticated_page.locator('[data-testid="citation"]').first
        if await citation_button.count() > 0:
            await citation_button.click()
            await authenticated_page.wait_for_selector('[data-testid="citation-panel"]')


class TestConversationSwitching:
    @pytest.mark.asyncio
    async def test_switch_conversations(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/chat")
        
        # Create first conversation
        await authenticated_page.click('text=New Conversation')
        await authenticated_page.fill('input[name="title"]', "First Conversation")
        await authenticated_page.click('button[type="submit"]')
        
        await authenticated_page.fill('textarea[placeholder*="Message"]', "First message")
        await authenticated_page.click('button:has-text("Send")')
        await authenticated_page.wait_for_selector('[data-role="assistant"]', timeout=30000)
        
        # Create second conversation
        await authenticated_page.click('text=New Conversation')
        await authenticated_page.fill('input[name="title"]', "Second Conversation")
        await authenticated_page.click('button[type="submit"]')
        
        await authenticated_page.fill('textarea[placeholder*="Message"]', "Second message")
        await authenticated_page.click('button:has-text("Send")')
        await authenticated_page.wait_for_selector('[data-role="assistant"]', timeout=30000)
        
        # Switch back to first
        await authenticated_page.click('text=First Conversation')
        await authenticated_page.wait_for_selector("text=First message")


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_delete_conversation(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/chat")
        
        # Create a conversation to delete
        await authenticated_page.click('text=New Conversation')
        await authenticated_page.fill('input[name="title"]', "To Delete")
        await authenticated_page.click('button[type="submit"]')
        
        # Delete it
        await authenticated_page.click('[data-testid="conversation-menu"]')
        await authenticated_page.click('text=Delete')
        await authenticated_page.click('text=Confirm')
        
        await authenticated_page.wait_for_selector("text=To Delete", state="hidden")


class TestRestoreDocument:
    @pytest.mark.asyncio
    async def test_restore_deleted_document(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/documents")
        
        # Upload a document
        await authenticated_page.click('text=Upload Document')
        await authenticated_page.set_input_files('input[type="file"]', {
            "name": "torestore.txt",
            "mimeType": "text/plain",
            "buffer": b"Document to restore"
        })
        await authenticated_page.click('button[type="submit"]')
        await authenticated_page.wait_for_selector("text=torestore.txt")
        
        # Delete it
        await authenticated_page.click('[data-testid="document-menu"]')
        await authenticated_page.click('text=Delete')
        await authenticated_page.click('text=Confirm')
        
        # Go to trash
        await authenticated_page.click('text=Trash')
        await authenticated_page.wait_for_selector("text=torestore.txt")
        
        # Restore
        await authenticated_page.click('[data-testid="document-menu"]')
        await authenticated_page.click('text=Restore')
        
        # Verify restored
        await authenticated_page.click('text=All Documents')
        await authenticated_page.wait_for_selector("text=torestore.txt")


class TestSettings:
    @pytest.mark.asyncio
    async def test_update_settings(self, authenticated_page: Page):
        await authenticated_page.goto(f"{BASE_URL}/settings")
        
        await authenticated_page.fill('input[name="fullName"]', "Updated Name")
        await authenticated_page.click('button:has-text("Save")')
        
        await authenticated_page.wait_for_selector("text=Settings saved")
        
        # Verify persisted
        await authenticated_page.reload()
        await authenticated_page.wait_for_selector('input[name="fullName"][value="Updated Name"]')