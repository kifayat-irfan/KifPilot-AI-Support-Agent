from typing import Optional


class AuthError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class UserNotFoundError(AuthError):
    """Raised when a user is not found."""

    def __init__(self, identifier: str):
        super().__init__(
            f"User not found: {identifier}",
            "USER_NOT_FOUND"
        )
        self.identifier = identifier


class UserAlreadyExistsError(AuthError):
    """Raised when a user already exists."""

    def __init__(self, field: str, value: str):
        super().__init__(
            f"User with {field} '{value}' already exists",
            "USER_ALREADY_EXISTS"
        )
        self.field = field
        self.value = value


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid."""

    def __init__(self):
        super().__init__(
            "Invalid username/email or password",
            "INVALID_CREDENTIALS"
        )


class InactiveUserError(AuthError):
    """Raised when a user is inactive."""

    def __init__(self):
        super().__init__(
            "User account is inactive",
            "INACTIVE_USER"
        )


class TokenExpiredError(AuthError):
    """Raised when a token is expired."""

    def __init__(self):
        super().__init__(
            "Token has expired",
            "TOKEN_EXPIRED"
        )


class InvalidTokenError(AuthError):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, "INVALID_TOKEN")


class PermissionDeniedError(AuthError):
    """Raised when permission is denied."""

    def __init__(self, permission: str):
        super().__init__(
            f"Permission denied: {permission}",
            "PERMISSION_DENIED"
        )
        self.permission = permission


class RoleNotFoundError(AuthError):
    """Raised when a role is not found."""

    def __init__(self, role_name: str):
        super().__init__(
            f"Role not found: {role_name}",
            "ROLE_NOT_FOUND"
        )
        self.role_name = role_name


class PermissionNotFoundError(AuthError):
    """Raised when a permission is not found."""

    def __init__(self, permission_name: str):
        super().__init__(
            f"Permission not found: {permission_name}",
            "PERMISSION_NOT_FOUND"
        )
        self.permission_name = permission_name


class RoleAssignmentError(AuthError):
    """Raised when role assignment fails."""

    def __init__(self, message: str = "Failed to assign role"):
        super().__init__(message, "ROLE_ASSIGNMENT_FAILED")