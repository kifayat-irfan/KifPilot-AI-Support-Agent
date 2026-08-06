from typing import Optional


class MultiTenantError(Exception):
    """Base exception for multi-tenant errors."""

    def __init__(self, message: str, code: str = "MULTITENANT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class OrganizationNotFoundError(MultiTenantError):
    """Raised when an organization is not found."""

    def __init__(self, organization_id: str):
        super().__init__(
            f"Organization not found: {organization_id}",
            "ORGANIZATION_NOT_FOUND"
        )
        self.organization_id = organization_id


class OrganizationAlreadyExistsError(MultiTenantError):
    """Raised when an organization already exists."""

    def __init__(self, field: str, value: str):
        super().__init__(
            f"Organization with {field} '{value}' already exists",
            "ORGANIZATION_ALREADY_EXISTS"
        )
        self.field = field
        self.value = value


class OrganizationCreationError(MultiTenantError):
    """Raised when organization creation fails."""

    def __init__(self, message: str = "Failed to create organization"):
        super().__init__(message, "ORGANIZATION_CREATION_FAILED")


class OrganizationDeletionError(MultiTenantError):
    """Raised when organization deletion fails."""

    def __init__(self, organization_id: str, message: str = "Failed to delete organization"):
        super().__init__(f"{message}: {organization_id}", "ORGANIZATION_DELETION_FAILED")
        self.organization_id = organization_id


class MemberNotFoundError(MultiTenantError):
    """Raised when a member is not found in an organization."""

    def __init__(self, organization_id: str, user_id: str):
        super().__init__(
            f"User {user_id} is not a member of organization {organization_id}",
            "MEMBER_NOT_FOUND"
        )
        self.organization_id = organization_id
        self.user_id = user_id


class MemberAlreadyExistsError(MultiTenantError):
    """Raised when a user is already a member of an organization."""

    def __init__(self, organization_id: str, user_id: str):
        super().__init__(
            f"User {user_id} is already a member of organization {organization_id}",
            "MEMBER_ALREADY_EXISTS"
        )
        self.organization_id = organization_id
        self.user_id = user_id


class MemberRoleError(MultiTenantError):
    """Raised when member role operation fails."""

    def __init__(self, message: str):
        super().__init__(message, "MEMBER_ROLE_ERROR")


class CrossTenantAccessError(MultiTenantError):
    """Raised when a cross-tenant access attempt is detected."""

    def __init__(self, organization_id: str, user_id: str, resource_type: str):
        super().__init__(
            f"Cross-tenant access denied: user {user_id} attempted to access {resource_type} in organization {organization_id}",
            "CROSS_TENANT_ACCESS_DENIED"
        )
        self.organization_id = organization_id
        self.user_id = user_id
        self.resource_type = resource_type


class OrganizationInactiveError(MultiTenantError):
    """Raised when an organization is inactive."""

    def __init__(self, organization_id: str):
        super().__init__(
            f"Organization {organization_id} is inactive",
            "ORGANIZATION_INACTIVE"
        )
        self.organization_id = organization_id


class SettingsNotFoundError(MultiTenantError):
    """Raised when organization settings are not found."""

    def __init__(self, organization_id: str):
        super().__init__(
            f"Settings not found for organization {organization_id}",
            "SETTINGS_NOT_FOUND"
        )
        self.organization_id = organization_id


class InvalidSlugError(MultiTenantError):
    """Raised when a slug is invalid."""

    def __init__(self, slug: str, reason: str = "Invalid slug format"):
        super().__init__(
            f"Invalid slug '{slug}': {reason}",
            "INVALID_SLUG"
        )
        self.slug = slug