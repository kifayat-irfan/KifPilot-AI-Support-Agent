import os
import shutil
import aiofiles
from typing import Optional, BinaryIO, IO
from uuid import uuid4
from datetime import datetime
import io

from app.services.documents.validators import FileValidator, get_file_validator
from app.services.documents.exceptions import (
    FileValidationError,
    FileSizeError,
    UnsupportedFileTypeError,
    DuplicateFileError,
)
from app.core.config import get_settings

settings = get_settings()


class DocumentLoader:
    def __init__(self, validator: Optional[FileValidator] = None):
        self.validator = validator or get_file_validator()
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_upload(self, file: IO[bytes], filename: str, file_size: int) -> str:
        # Validate
        self.validator.validate_file_size(file_size)
        _, ext = os.path.splitext(filename.lower())
        self.validator.validate_extension(filename)

        # Generate unique filename to prevent conflicts
        unique_filename = self._generate_unique_filename(filename)
        file_path = os.path.join(self.upload_dir, unique_filename)

        # Save file - handle both sync and async file objects
        async with aiofiles.open(file_path, "wb") as f:
            # Check if file has async read method
            if hasattr(file, 'read') and callable(file.read):
                # Try async read first
                try:
                    content = await file.read()
                except TypeError:
                    # Fallback to sync read
                    content = file.read()
            else:
                content = file.read()
            await f.write(content)

        # Validate MIME type after saving
        self.validator.validate_mime_type(file_path, ext)

        return file_path

    def _generate_unique_filename(self, filename: str) -> str:
        name, ext = os.path.splitext(filename)
        unique_id = uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{name}_{timestamp}_{unique_id}{ext}"

    def delete_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def get_file_path(self, filename: str) -> str:
        return os.path.join(self.upload_dir, filename)

    def file_exists(self, filename: str) -> bool:
        return os.path.exists(os.path.join(self.upload_dir, filename))

    def get_file_size(self, file_path: str) -> int:
        return os.path.getsize(file_path) if os.path.exists(file_path) else 0


def get_document_loader() -> DocumentLoader:
    return DocumentLoader()