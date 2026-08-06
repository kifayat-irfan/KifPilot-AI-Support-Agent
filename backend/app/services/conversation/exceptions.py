from typing import Optional


class ConversationError(Exception):
    """Base exception for conversation errors."""

    def __init__(self, message: str, code: str = "CONVERSATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SessionNotFoundError(ConversationError):
    """Raised when a session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Session not found: {session_id}",
            "SESSION_NOT_FOUND"
        )
        self.session_id = session_id


class MessageNotFoundError(ConversationError):
    """Raised when a message is not found."""

    def __init__(self, message_id: str):
        super().__init__(
            f"Message not found: {message_id}",
            "MESSAGE_NOT_FOUND"
        )
        self.message_id = message_id


class SessionCreationError(ConversationError):
    """Raised when session creation fails."""

    def __init__(self, message: str = "Failed to create session"):
        super().__init__(message, "SESSION_CREATION_FAILED")


class MessageSaveError(ConversationError):
    """Raised when saving a message fails."""

    def __init__(self, message: str = "Failed to save message"):
        super().__init__(message, "MESSAGE_SAVE_FAILED")


class SessionDeletionError(ConversationError):
    """Raised when session deletion fails."""

    def __init__(self, session_id: str, message: str = "Failed to delete session"):
        super().__init__(f"{message}: {session_id}", "SESSION_DELETION_FAILED")
        self.session_id = session_id


class InvalidSessionStateError(ConversationError):
    """Raised when session is in an invalid state."""

    def __init__(self, message: str):
        super().__init__(message, "INVALID_SESSION_STATE")


class MemoryConfigError(ConversationError):
    """Raised when memory configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(message, "MEMORY_CONFIG_ERROR")