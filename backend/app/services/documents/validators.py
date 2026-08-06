import os
from typing import List, Optional
from app.core.config import get_settings
from app.services.documents.exceptions import (
    FileValidationError,
    FileSizeError,
    UnsupportedFileTypeError,
    DuplicateFileError,
)

settings = get_settings()


try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None


class FileValidator:
    def __init__(self):
        self.max_file_size = settings.max_file_size_bytes
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        self.upload_dir = settings.UPLOAD_DIR

    def validate_file_size(self, file_size: int) -> None:
        if file_size > self.max_file_size:
            raise FileSizeError(file_size, self.max_file_size)

    def validate_extension(self, filename: str) -> None:
        _, ext = os.path.splitext(filename.lower())
        if ext not in self.allowed_extensions:
            raise UnsupportedFileTypeError(ext, self.allowed_extensions)

    def validate_mime_type(self, file_path: str, expected_ext: str) -> None:
        if not HAS_MAGIC:
            # Skip MIME type validation if python-magic is not available (e.g., Windows without libmagic)
            return
        mime_type = magic.from_file(file_path, mime=True)
        expected_mimes = {
            ".pdf": ["application/pdf"],
            ".docx": [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ],
            ".txt": ["text/plain"],
            ".md": ["text/markdown", "text/plain"],
        }
        allowed = expected_mimes.get(expected_ext, [])
        if mime_type not in allowed:
            raise UnsupportedFileTypeError(
                f"{expected_ext} (MIME: {mime_type})", allowed
            )

    def check_duplicate(self, filename: str) -> None:
        file_path = os.path.join(self.upload_dir, filename)
        if os.path.exists(file_path):
            raise DuplicateFileError(filename)

    def validate(self, file_path: str, filename: str, file_size: int) -> str:
        self.validate_file_size(file_size)
        self.validate_extension(filename)
        _, ext = os.path.splitext(filename.lower())
        self.validate_mime_type(file_path, ext)
        self.check_duplicate(filename)
        return ext


def get_file_validator() -> FileValidator:
    return FileValidator()