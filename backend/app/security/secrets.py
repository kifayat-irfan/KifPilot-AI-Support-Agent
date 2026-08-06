"""Secrets management for KifPilot."""

import os
import base64
import hashlib
import hmac
import secrets
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import threading

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SecretType(str, Enum):
    """Types of secrets."""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"
    OAUTH_SECRET = "oauth_secret"
    CUSTOM = "custom"


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    secret_type: SecretType
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    version: int = 1
    expires_at: Optional[str] = None
    rotation_interval_days: Optional[int] = None
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    last_accessed: Optional[str] = None
    access_count: int = 0


class SecretsManager:
    """Manages application secrets securely."""
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._metadata: Dict[str, SecretMetadata] = {}
        self._lock = threading.RLock()
        self._initialized = False
        self._master_key: Optional[bytes] = None
    
    def initialize(self, master_key: Optional[str] = None):
        """Initialize the secrets manager."""
        with self._lock:
            if self._initialized:
                return
            
            # Generate or load master key
            if master_key:
                self._master_key = self._derive_key(master_key.encode())
            else:
                # Try to load from environment
                env_key = os.getenv("SECRETS_MASTER_KEY")
                if env_key:
                    self._master_key = self._derive_key(env_key.encode())
                else:
                    # Generate new key (in production, this should be persisted)
                    self._master_key = secrets.token_bytes(32)
                    logger.warning("Generated ephemeral master key - secrets will not persist across restarts")
            
            # Load secrets from environment
            self._load_from_environment()
            
            self._initialized = True
            logger.info("Secrets manager initialized")
    
    def _derive_key(self, password: bytes) -> bytes:
        """Derive encryption key from password."""
        import hashlib
        return hashlib.pbkdf2_hmac("sha256", password, b"kifpilot-salt", 100000, dklen=32)
    
    def _encrypt(self, value: str) -> str:
        """Encrypt a secret value."""
        if not self._master_key:
            raise RuntimeError("Secrets manager not initialized")
        
        # Simple encryption using AES-GCM (requires cryptography)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(self._master_key)
            encrypted = aesgcm.encrypt(nonce, value.encode(), None)
            
            # Return nonce + ciphertext as base64
            return base64.b64encode(nonce + encrypted).decode()
        except ImportError:
            # Fallback: just base64 encode (NOT SECURE - for dev only)
            logger.warning("cryptography not installed - using base64 encoding only")
            return base64.b64encode(value.encode()).decode()
    
    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        if not self._master_key:
            raise RuntimeError("Secrets manager not initialized")
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            data = base64.b64decode(encrypted_value)
            nonce = data[:12]
            ciphertext = data[12:]
            
            aesgcm = AESGCM(self._master_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            
            return decrypted.decode()
        except ImportError:
            # Fallback: just base64 decode
            return base64.b64decode(encrypted_value).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt secret: {e}")
    
    def _load_from_environment(self):
        """Load secrets from environment variables."""
        # Standard secrets
        env_mappings = {
            "SECRET_KEY": ("jwt_secret", SecretType.JWT_SECRET),
            "DATABASE_PASSWORD": ("database_password", SecretType.DATABASE_PASSWORD),
            "ENCRYPTION_KEY": ("encryption_key", SecretType.ENCRYPTION_KEY),
            "WEBHOOK_SECRET": ("webhook_secret", SecretType.WEBHOOK_SECRET),
            "OPENAI_API_KEY": ("openai_api_key", SecretType.API_KEY),
            "ANTHROPIC_API_KEY": ("anthropic_api_key", SecretType.API_KEY),
            "GOOGLE_API_KEY": ("google_api_key", SecretType.API_KEY),
            "HUGGINGFACE_API_KEY": ("huggingface_api_key", SecretType.API_KEY),
        }
        
        for env_var, (name, secret_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self.set_secret(name, value, secret_type, description=f"Loaded from {env_var}")
        
        # Load any KIFPILOT_SECRET_* variables
        for key, value in os.environ.items():
            if key.startswith("KIFPILOT_SECRET_") and value:
                name = key[16:].lower()
                self.set_secret(name, value, SecretType.CUSTOM, description=f"Loaded from {key}")
    
    def set_secret(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.CUSTOM,
        description: str = "",
        expires_in_days: Optional[int] = None,
        rotation_interval_days: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Set a secret."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            
            encrypted = self._encrypt(value)
            
            now = datetime.utcnow()
            expires_at = None
            if expires_in_days:
                expires_at = (now + timedelta(days=expires_in_days)).isoformat() + "Z"
            
            metadata = SecretMetadata(
                name=name,
                secret_type=secret_type,
                created_at=now.isoformat() + "Z",
                updated_at=now.isoformat() + "Z",
                version=self._metadata.get(name, SecretMetadata(name=name, secret_type=secret_type)).version + 1,
                expires_at=expires_at,
                rotation_interval_days=rotation_interval_days,
                description=description,
                tags=tags or {},
            )
            
            self._secrets[name] = encrypted
            self._metadata[name] = metadata
            
            logger.info("Secret set", name=name, type=secret_type.value, version=metadata.version)
    
    def get_secret(self, name: str) -> Optional[str]:
        """Get a secret value."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            
            encrypted = self._secrets.get(name)
            if encrypted is None:
                return None
            
            # Check expiration
            metadata = self._metadata.get(name)
            if metadata and metadata.expires_at:
                if datetime.fromisoformat(metadata.expires_at.replace("Z", "+00:00")) < datetime.utcnow():
                    logger.warning("Secret expired", name=name)
                    return None
            
            # Update access metadata
            if metadata:
                metadata.last_accessed = datetime.utcnow().isoformat() + "Z"
                metadata.access_count += 1
            
            return self._decrypt(encrypted)
    
    def get_secret_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get secret metadata (without the value)."""
        with self._lock:
            return self._metadata.get(name)
    
    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        with self._lock:
            if name in self._secrets:
                del self._secrets[name]
                del self._metadata[name]
                logger.info("Secret deleted", name=name)
                return True
            return False
    
    def rotate_secret(self, name: str, new_value: str) -> bool:
        """Rotate a secret to a new value."""
        with self._lock:
            if name not in self._secrets:
                return False
            
            encrypted = self._encrypt(new_value)
            self._secrets[name] = encrypted
            
            metadata = self._metadata[name]
            metadata.version += 1
            metadata.updated_at = datetime.utcnow().isoformat() + "Z"
            
            logger.info("Secret rotated", name=name, version=metadata.version)
            return True
    
    def list_secrets(self, secret_type: Optional[SecretType] = None) -> List[SecretMetadata]:
        """List all secrets (metadata only)."""
        with self._lock:
            result = list(self._metadata.values())
            if secret_type:
                result = [m for m in result if m.secret_type == secret_type]
            return result
    
    def check_rotation_needed(self) -> List[str]:
        """Check which secrets need rotation."""
        with self._lock:
            now = datetime.utcnow()
            needs_rotation = []
            
            for name, metadata in self._metadata.items():
                if metadata.rotation_interval_days:
                    updated = datetime.fromisoformat(metadata.updated_at.replace("Z", "+00:00"))
                    next_rotation = updated + timedelta(days=metadata.rotation_interval_days)
                    if now >= next_rotation:
                        needs_rotation.append(name)
                
                if metadata.expires_at:
                    expires = datetime.fromisoformat(metadata.expires_at.replace("Z", "+00:00"))
                    if now >= expires:
                        needs_rotation.append(name)
            
            return needs_rotation
    
    def generate_api_key(self, prefix: str = "kfp") -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"
    
    def generate_secret(self, length: int = 32) -> str:
        """Generate a cryptographically secure random secret."""
        return secrets.token_urlsafe(length)
    
    def hash_secret(self, secret: str, salt: Optional[str] = None) -> str:
        """Hash a secret for storage (e.g., API key hashes)."""
        if salt is None:
            salt = secrets.token_bytes(16)
        else:
            salt = salt.encode() if isinstance(salt, str) else salt
        
        hash_obj = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 100000)
        return base64.b64encode(salt + hash_obj).decode()
    
    def verify_secret_hash(self, secret: str, stored_hash: str) -> bool:
        """Verify a secret against a stored hash."""
        try:
            data = base64.b64decode(stored_hash)
            salt = data[:16]
            stored_key = data[16:]
            
            hash_obj = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 100000)
            return hmac.compare_digest(hash_obj, stored_key)
        except Exception:
            return False


_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
        _secrets_manager.initialize()
    return _secrets_manager


def load_secret(name: str) -> Optional[str]:
    """Load a secret by name."""
    manager = get_secrets_manager()
    return manager.get_secret(name)


def rotate_secret(name: str, new_value: str) -> bool:
    """Rotate a secret."""
    manager = get_secrets_manager()
    return manager.rotate_secret(name, new_value)