"""File upload security for KifPilot."""

import os
import io
import hashlib
import zipfile
import tarfile
from typing import Optional, List, Set, Tuple, BinaryIO
from dataclasses import dataclass, field
from pathlib import Path
import uuid
from datetime import datetime

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Try to import python-magic for MIME detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logger.warning("python-magic not available, using fallback MIME detection")
except Exception as e:
    HAS_MAGIC = False
    logger.warning(f"python-magic initialization failed: {e}, using fallback MIME detection")


@dataclass
class UploadSecurityConfig:
    """Configuration for upload security."""
    # File size limits
    max_file_size: int = 50 * 1024 * 1024  # 50 MB
    max_total_upload_size: int = 500 * 1024 * 1024  # 500 MB
    
    # Allowed MIME types
    allowed_mime_types: Set[str] = field(default_factory=lambda: {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/msword",  # .doc
        "text/plain",  # .txt
        "text/markdown",  # .md
        "text/csv",  # .csv
        "application/json",  # .json
        "text/xml",  # .xml
        "application/xml",  # .xml
        "text/html",  # .html
        "text/x-python",  # .py
        "text/x-shellscript",  # .sh
        "text/javascript",  # .js
        "application/javascript",  # .js
        "text/css",  # .css
        "application/x-yaml",  # .yaml, .yml
        "text/yaml",  # .yaml
    })
    
    # Allowed extensions
    allowed_extensions: Set[str] = field(default_factory=lambda: {
        ".pdf", ".docx", ".doc", ".txt", ".md", ".csv", 
        ".json", ".xml", ".html", ".py", ".sh", ".js", 
        ".css", ".yaml", ".yml"
    })
    
    # Blocked MIME types (executables, scripts, etc.)
    blocked_mime_types: Set[str] = field(default_factory=lambda: {
        "application/x-executable",
        "application/x-dosexec",
        "application/x-msdownload",
        "application/x-shockwave-flash",
        "application/x-java-applet",
        "application/x-php",
        "application/x-httpd-php",
        "text/x-php",
        "application/x-perl",
        "application/x-python-code",
        "application/x-sh",
        "application/x-csh",
        "application/x-msdos-program",
        "application/vnd.microsoft.portable-executable",
    })
    
    # Blocked extensions
    blocked_extensions: Set[str] = field(default_factory=lambda: {
        ".exe", ".dll", ".so", ".dylib", ".bin", ".out", ".app",
        ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".jar",
        ".php", ".phtml", ".php3", ".php4", ".php5", ".phps",
        ".asp", ".aspx", ".asax", ".ascx", ".ashx", ".asmx",
        ".jsp", ".jspx", ".jsw", ".jsv", ".jspf",
        ".pyc", ".pyo", ".pyd",
        ".bash", ".csh", ".ksh", ".zsh",
        ".pl", ".pm", ".cgi",
        ".rb", ".rbw",
        ".ps1", ".psm1", ".psd1",
        ".msi", ".msp", ".mst",
        ".reg", ".inf",
    })
    
    # Archive handling
    allow_archives: bool = False
    max_archive_size: int = 100 * 1024 * 1024  # 100 MB
    max_archive_files: int = 1000
    max_archive_depth: int = 3
    
    # Zip bomb detection
    zip_bomb_ratio: float = 100.0  # compression ratio threshold
    max_decompressed_size: int = 1024 * 1024 * 1024  # 1 GB
    
    # Filename sanitization
    max_filename_length: int = 255
    allow_unicode_filenames: bool = False
    
    # Virus scanning (placeholder for integration)
    enable_virus_scan: bool = False
    virus_scan_timeout: int = 30


def get_upload_security_config() -> UploadSecurityConfig:
    """Get upload security configuration."""
    config = UploadSecurityConfig()
    config.max_file_size = settings.max_file_size_bytes
    config.allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
    return config


class SecureFilenameGenerator:
    """Generates secure filenames for uploaded files."""
    
    def __init__(self, config: Optional[UploadSecurityConfig] = None):
        self.config = config or get_upload_security_config()
    
    def generate(self, original_filename: str, user_id: str = "") -> str:
        """Generate a secure filename."""
        # Extract extension
        path = Path(original_filename)
        extension = path.suffix.lower()
        
        # Validate extension
        if extension not in self.config.allowed_extensions:
            raise ValueError(f"Extension {extension} not allowed")
        
        # Generate unique name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        user_part = f"_{user_id[:8]}" if user_id else ""
        
        # Sanitize stem
        stem = self._sanitize_stem(path.stem)
        
        # Construct new filename
        new_filename = f"{timestamp}{user_part}_{unique_id}_{stem}{extension}"
        
        # Ensure length limit
        if len(new_filename) > self.config.max_filename_length:
            # Truncate stem
            max_stem_len = self.config.max_filename_length - len(f"{timestamp}{user_part}_{unique_id}{extension}")
            if max_stem_len > 0:
                stem = stem[:max_stem_len]
                new_filename = f"{timestamp}{user_part}_{unique_id}_{stem}{extension}"
            else:
                new_filename = f"{timestamp}{user_part}_{unique_id}{extension}"
        
        return new_filename
    
    def _sanitize_stem(self, stem: str) -> str:
        """Sanitize filename stem."""
        # Remove path separators and dangerous characters
        stem = stem.replace("/", "_").replace("\\", "_")
        stem = "".join(c for c in stem if c.isalnum() or c in "._- ")
        stem = stem.strip("._- ")
        
        # Limit length
        if len(stem) > 100:
            stem = stem[:100]
        
        # Ensure not empty
        if not stem:
            stem = "file"
        
        return stem


class UploadSecurityValidator:
    """Validates file uploads for security."""
    
    def __init__(self, config: Optional[UploadSecurityConfig] = None):
        self.config = config or get_upload_security_config()
        self.filename_generator = SecureFilenameGenerator(config)
        
        # Initialize MIME detector
        if HAS_MAGIC:
            try:
                self._magic = magic.Magic(mime=True)
            except Exception as e:
                logger.warning(f"Failed to initialize python-magic: {e}, using fallback")
                self._magic = None
        else:
            self._magic = None
    
    def validate_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (secure_filename, metadata)
        """
        metadata = {
            "original_filename": filename,
            "content_type": content_type,
            "size": len(file_content),
        }
        
        # Check file size
        if len(file_content) > self.config.max_file_size:
            raise ValueError(f"File too large: {len(file_content)} bytes (max {self.config.max_file_size})")
        
        # Check empty file
        if len(file_content) == 0:
            raise ValueError("Empty file not allowed")
        
        # Validate extension
        path = Path(filename)
        extension = path.suffix.lower()
        
        if extension in self.config.blocked_extensions:
            raise ValueError(f"File extension {extension} is blocked")
        
        if extension not in self.config.allowed_extensions:
            raise ValueError(f"File extension {extension} not allowed")
        
        metadata["extension"] = extension
        
        # Detect MIME type from content
        detected_mime = self._detect_mime_type(file_content)
        metadata["detected_mime_type"] = detected_mime
        
        # Validate MIME type
        if detected_mime in self.config.blocked_mime_types:
            raise ValueError(f"File type {detected_mime} is blocked")
        
        if detected_mime not in self.config.allowed_mime_types:
            raise ValueError(f"File type {detected_mime} not allowed")
        
        # Check content-type header matches
        if content_type and content_type != detected_mime:
            # Allow some common mismatches
            if not self._is_acceptable_mismatch(content_type, detected_mime):
                logger.warning(
                    "MIME type mismatch",
                    declared=content_type,
                    detected=detected_mime,
                    filename=filename,
                )
        
        # Check for zip bombs (for archives)
        if extension in {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"}:
            self._check_zip_bomb(file_content, extension)
        
        # Check for embedded executables
        self._check_embedded_executables(file_content)
        
        # Check for polyglot files
        self._check_polyglot(file_content, extension)
        
        # Generate secure filename
        secure_filename = self.filename_generator.generate(filename)
        metadata["secure_filename"] = secure_filename
        
        # Calculate hashes
        metadata["sha256"] = hashlib.sha256(file_content).hexdigest()
        metadata["md5"] = hashlib.md5(file_content).hexdigest()  # For deduplication only
        
        logger.info(
            "File upload validated",
            filename=filename,
            secure_filename=secure_filename,
            size=len(file_content),
            mime_type=detected_mime,
        )
        
        return secure_filename, metadata
    
    def _detect_mime_type(self, content: bytes) -> str:
        """Detect MIME type from file content using python-magic or fallback."""
        # Try python-magic first
        if self._magic is not None:
            try:
                sample = content[:8192]
                return self._magic.from_buffer(sample)
            except Exception as e:
                logger.warning("python-magic MIME detection failed", error=str(e))
        
        # Fallback: basic MIME detection by file signature
        return self._fallback_mime_detection(content)
    
    def _fallback_mime_detection(self, content: bytes) -> str:
        """Basic MIME detection by file signatures (magic bytes)."""
        if len(content) < 4:
            return "application/octet-stream"
        
        # Check file signatures (magic bytes)
        header = content[:16]
        
        # PDF
        if header.startswith(b"%PDF"):
            return "application/pdf"
        
        # ZIP / DOCX / XLSX / PPTX / JAR / APK
        if header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06") or header.startswith(b"PK\x07\x08"):
            # Could be DOCX, XLSX, etc. - check internal structure if needed
            return "application/zip"
        
        # Microsoft Office (OLE)
        if header.startswith(b"\xd0\xcf\x11\xe0"):
            return "application/msword"
        
        # JPEG
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        
        # PNG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        
        # GIF
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
        
        # Text files (UTF-8, ASCII)
        try:
            # Check if it's valid UTF-8 text
            content[:1024].decode("utf-8")
            # Heuristic: if it contains common text patterns
            text_sample = content[:1024].decode("utf-8", errors="ignore")
            if any(kw in text_sample.lower() for kw in ["import ", "def ", "function ", "class ", "<?xml", "<html", "<!doctype"]):
                if "import " in text_sample or "def " in text_sample:
                    return "text/x-python"
                if "function " in text_sample:
                    return "text/javascript"
                if "<?xml" in text_sample:
                    return "application/xml"
                if "<html" in text_sample or "<!doctype" in text_sample:
                    return "text/html"
            return "text/plain"
        except UnicodeDecodeError:
            pass
        
        # Default
        return "application/octet-stream"
    
    def _is_acceptable_mismatch(self, declared: str, detected: str) -> bool:
        """Check if MIME type mismatch is acceptable."""
        acceptable_pairs = [
            ("text/plain", "text/markdown"),
            ("text/plain", "text/x-python"),
            ("application/json", "text/plain"),
            ("application/xml", "text/xml"),
            ("text/csv", "text/plain"),
        ]
        
        for a, b in acceptable_pairs:
            if (declared == a and detected == b) or (declared == b and detected == a):
                return True
        
        return False
    
    def _check_zip_bomb(self, content: bytes, extension: str):
        """Check for zip bombs in archive files."""
        if not self.config.allow_archives:
            raise ValueError(f"Archive files ({extension}) are not allowed")
        
        if len(content) > self.config.max_archive_size:
            raise ValueError(f"Archive too large: {len(content)} bytes")
        
        try:
            if extension == ".zip":
                with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                    self._check_zip_file(zf)
            elif extension in {".tar", ".gz", ".tgz"}:
                with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as tf:
                    self._check_tar_file(tf)
        except Exception as e:
            logger.warning("Archive validation failed", error=str(e))
            raise ValueError(f"Invalid or corrupted archive: {e}")
    
    def _check_zip_file(self, zf: zipfile.ZipFile):
        """Check zip file for zip bombs."""
        total_size = 0
        file_count = 0
        
        for info in zf.infolist():
            file_count += 1
            if file_count > self.config.max_archive_files:
                raise ValueError(f"Too many files in archive: {file_count}")
            
            total_size += info.file_size
            if total_size > self.config.max_decompressed_size:
                raise ValueError(f"Decompressed size too large: {total_size}")
            
            # Check compression ratio
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > self.config.zip_bomb_ratio:
                    raise ValueError(f"Suspicious compression ratio: {ratio:.1f}")
            
            # Check for path traversal in archive
            if info.filename.startswith("/") or ".." in info.filename:
                raise ValueError(f"Path traversal in archive: {info.filename}")
    
    def _check_tar_file(self, tf: tarfile.TarFile):
        """Check tar file for issues."""
        total_size = 0
        file_count = 0
        
        for member in tf.getmembers():
            file_count += 1
            if file_count > self.config.max_archive_files:
                raise ValueError(f"Too many files in archive: {file_count}")
            
            total_size += member.size
            if total_size > self.config.max_decompressed_size:
                raise ValueError(f"Decompressed size too large: {total_size}")
            
            # Check for path traversal
            if member.name.startswith("/") or ".." in member.name:
                raise ValueError(f"Path traversal in archive: {member.name}")
            
            # Check for absolute paths or symlinks outside archive
            if member.issym() or member.islnk():
                linkpath = member.linkname
                if linkpath.startswith("/") or ".." in linkpath:
                    raise ValueError(f"Suspicious link in archive: {linkpath}")
    
    def _check_embedded_executables(self, content: bytes):
        """Check for embedded executables in files."""
        # Check for PE headers (Windows executables)
        if content[:2] == b"MZ":
            # Check for PE signature
            pe_offset = int.from_bytes(content[0x3C:0x40], "little") if len(content) > 0x40 else 0
            if pe_offset > 0 and pe_offset + 4 < len(content):
                if content[pe_offset:pe_offset+4] == b"PE\0\0":
                    raise ValueError("Windows executable embedded in file")
        
        # Check for ELF headers (Linux executables)
        if content[:4] == b"\x7fELF":
            raise ValueError("ELF executable embedded in file")
        
        # Check for Mach-O headers (macOS executables)
        if content[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", 
                           b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe"):
            raise ValueError("Mach-O executable embedded in file")
        
        # Check for shell scripts with shebang
        if content.startswith(b"#!"):
            # Allow certain shebangs for text files
            shebang = content[:128].decode("ascii", errors="ignore").lower()
            dangerous_interpreters = ["/bin/bash", "/bin/sh", "/bin/zsh", "/usr/bin/python", 
                                     "/usr/bin/perl", "/usr/bin/ruby", "/usr/bin/php"]
            for interp in dangerous_interpreters:
                if interp in shebang:
                    raise ValueError(f"Script with dangerous interpreter: {interp}")
    
    def _check_polyglot(self, content: bytes, extension: str):
        """Check for polyglot files (valid as multiple file types)."""
        # Check for JPEG + other content
        if extension in {".jpg", ".jpeg", ".png", ".gif"}:
            # JPEG should end with FF D9
            if not content.endswith(b"\xff\xd9") and not content.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"):
                logger.warning("Image file may have appended data", filename=extension)
        
        # Check for PDF with embedded content
        if extension == ".pdf":
            if content.count(b"%EOF") > 1:
                logger.warning("PDF may have multiple EOF markers")
            if b"/JavaScript" in content or b"/JS" in content:
                raise ValueError("PDF contains JavaScript")
            if b"/Launch" in content or b"/EmbeddedFile" in content:
                logger.warning("PDF contains embedded files or launch actions")
    
    async def validate_upload_file(self, upload_file: "UploadFile") -> Tuple[str, dict]:
        """Validate FastAPI UploadFile."""
        # Read file content
        content = await upload_file.read()
        await upload_file.seek(0)  # Reset for later reading
        
        return self.validate_file(
            file_content=content,
            filename=upload_file.filename or "unknown",
            content_type=upload_file.content_type,
        )


_upload_validator: Optional[UploadSecurityValidator] = None


def get_upload_validator() -> UploadSecurityValidator:
    """Get or create the global upload validator."""
    global _upload_validator
    if _upload_validator is None:
        _upload_validator = UploadSecurityValidator()
    return _upload_validator


async def validate_file_upload(upload_file: "UploadFile") -> Tuple[str, dict]:
    """FastAPI dependency for file upload validation."""
    validator = get_upload_validator()
    return await validator.validate_upload_file(upload_file)