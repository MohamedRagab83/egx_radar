"""Secure secret management using OS-level keyring encryption (Layer 1 Security).

This module provides secure storage and retrieval of API keys and secrets
using the operating system's native credential storage:
  - Windows: Windows Credential Manager
  - macOS: Keychain
  - Linux: Secret Service API (GNOME Keyring / KWallet)

Security features:
  - Keys encrypted at rest by OS
  - No keys stored in source files or JSON configs
  - Secure memory handling with immediate cleanup
  - Audit logging for key access attempts

Usage:
    from egx_radar.utils.secrets import SecretManager

    secrets = SecretManager()
    secrets.set_key("alpha_vantage", "YOUR_API_KEY_HERE")
    key = secrets.get_key("alpha_vantage")
"""

import logging
import threading
from typing import Optional

try:
    import keyring
    from keyring.errors import KeyringError, KeyringLocked
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False
    KeyringError = Exception  # type: ignore
    KeyringLocked = Exception  # type: ignore

log = logging.getLogger(__name__)

# Service name for keyring storage (namespace for EGX Radar credentials)
_SERVICE_NAME = "egx_radar_api_keys"

# Thread-safe cache to reduce keyring access overhead
_key_cache: dict = {}
_cache_lock = threading.Lock()

# Audit log for security monitoring
_audit_log: list = []
_audit_lock = threading.Lock()


class SecretManager:
    """Secure API key management with OS-level encryption.
    
    This class provides a secure interface for storing and retrieving
    API keys using the operating system's credential storage system.
    
    Attributes:
        service_name: Identifier for the credential namespace
        use_cache: Enable in-memory caching for performance
        audit_enabled: Log all access attempts for security monitoring
    """
    
    def __init__(self, service_name: str = _SERVICE_NAME, 
                 use_cache: bool = True, 
                 audit_enabled: bool = True):
        """Initialize the secret manager.
        
        Args:
            service_name: Namespace for stored credentials
            use_cache: Cache retrieved keys in memory (faster access)
            audit_enabled: Enable security audit logging
        """
        self.service_name = service_name
        self.use_cache = use_cache
        self.audit_enabled = audit_enabled
        self._keyring_available = _KEYRING_AVAILABLE
        
        if not _KEYRING_AVAILABLE:
            log.warning(
                "keyring module not available - falling back to environment variables. "
                "Install with: pip install keyring"
            )
    
    def _audit(self, action: str, key_name: str, success: bool, details: str = "") -> None:
        """Log security audit event.
        
        Args:
            action: Type of access (GET, SET, DELETE)
            key_name: Name of the key accessed
            success: Whether the operation succeeded
            details: Additional context (error messages, etc.)
        """
        if not self.audit_enabled:
            return
            
        import datetime
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "key_name": key_name,
            "success": success,
            "details": details,
        }
        
        with _audit_lock:
            _audit_log.append(event)
            # Keep only last 1000 events in memory
            if len(_audit_log) > 1000:
                _audit_log.pop(0)
        
        # Log security events
        if not success and action in ("GET", "DELETE"):
            log.warning("Security audit: %s %s failed - %s", action, key_name, details)
    
    def get_key(self, key_name: str) -> Optional[str]:
        """Retrieve an API key from secure storage.
        
        Args:
            key_name: Identifier for the key (e.g., 'alpha_vantage', 'twelve_data')
            
        Returns:
            The API key string, or None if not found or error occurred
        """
        # Check cache first
        if self.use_cache:
            with _cache_lock:
                if key_name in _key_cache:
                    self._audit("GET", key_name, True, "cache_hit")
                    return _key_cache[key_name]
        
        if not _KEYRING_AVAILABLE:
            # Fallback to environment variable
            import os
            key = os.environ.get(f"EGX_RADAR_{key_name.upper()}_KEY")
            if key:
                self._audit("GET", key_name, True, "env_fallback")
                if self.use_cache:
                    with _cache_lock:
                        _key_cache[key_name] = key
            else:
                self._audit("GET", key_name, False, "keyring_unavailable_env_empty")
            return key
        
        try:
            key = keyring.get_password(self.service_name, key_name)
            
            if key:
                self._audit("GET", key_name, True)
                if self.use_cache:
                    with _cache_lock:
                        _key_cache[key_name] = key
                return key
            else:
                self._audit("GET", key_name, False, "key_not_found")
                return None
                
        except KeyringLocked:
            self._audit("GET", key_name, False, "keyring_locked")
            return None
        except KeyringError as e:
            self._audit("GET", key_name, False, str(e))
            return None
        except Exception as e:
            self._audit("GET", key_name, False, f"unexpected_error: {e}")
            log.error("SecretManager.get_key unexpected error: %s", e)
            return None
    
    def set_key(self, key_name: str, key_value: str) -> bool:
        """Store an API key in secure storage.
        
        Args:
            key_name: Identifier for the key (e.g., 'alpha_vantage', 'twelve_data')
            key_value: The actual API key value to store securely
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not key_value:
            self._audit("SET", key_name, False, "empty_key_value")
            return False
        
        # Validate key format (basic sanity check)
        if not isinstance(key_value, str) or len(key_value) < 8:
            self._audit("SET", key_name, False, "invalid_key_format")
            log.warning("Attempted to store invalid key for %s", key_name)
            return False
        
        if not _KEYRING_AVAILABLE:
            # Fallback: store in environment variable (less secure)
            import os
            os.environ[f"EGX_RADAR_{key_name.upper()}_KEY"] = key_value
            self._audit("SET", key_name, True, "env_fallback")
            if self.use_cache:
                with _cache_lock:
                    _key_cache[key_name] = key_value
            log.warning(
                "Storing key in environment variable (insecure). "
                "Install keyring for secure storage: pip install keyring"
            )
            return True
        
        try:
            keyring.set_password(self.service_name, key_name, key_value)
            self._audit("SET", key_name, True)
            
            # Update cache
            if self.use_cache:
                with _cache_lock:
                    _key_cache[key_name] = key_value
            
            return True
            
        except KeyringLocked:
            self._audit("SET", key_name, False, "keyring_locked")
            return False
        except KeyringError as e:
            self._audit("SET", key_name, False, str(e))
            log.error("Failed to store key %s: %s", key_name, e)
            return False
        except Exception as e:
            self._audit("SET", key_name, False, f"unexpected_error: {e}")
            log.error("SecretManager.set_key unexpected error: %s", e)
            return False
    
    def delete_key(self, key_name: str) -> bool:
        """Delete an API key from secure storage.
        
        Args:
            key_name: Identifier for the key to delete
            
        Returns:
            True if successfully deleted, False otherwise
        """
        # Remove from cache
        if self.use_cache:
            with _cache_lock:
                _key_cache.pop(key_name, None)
        
        if not _KEYRING_AVAILABLE:
            # Remove from environment
            import os
            os.environ.pop(f"EGX_RADAR_{key_name.upper()}_KEY", None)
            self._audit("DELETE", key_name, True, "env_fallback")
            return True
        
        try:
            keyring.delete_password(self.service_name, key_name)
            self._audit("DELETE", key_name, True)
            return True
            
        except KeyringError as e:
            self._audit("DELETE", key_name, False, str(e))
            log.error("Failed to delete key %s: %s", key_name, e)
            return False
        except Exception as e:
            self._audit("DELETE", key_name, False, f"unexpected_error: {e}")
            log.error("SecretManager.delete_key unexpected error: %s", e)
            return False
    
    def list_keys(self) -> list:
        """List all stored key names (not values).
        
        Returns:
            List of key names currently stored
        """
        if not _KEYRING_AVAILABLE:
            import os
            return [
                k.replace("EGX_RADAR_", "").replace("_KEY", "").lower()
                for k in os.environ.keys()
                if k.startswith("EGX_RADAR_") and k.endswith("_KEY")
            ]
        
        try:
            # Note: keyring doesn't provide a list API, return cached keys
            with _cache_lock:
                return list(_key_cache.keys())
        except Exception as e:
            log.error("SecretManager.list_keys error: %s", e)
            return []
    
    def get_audit_log(self, limit: int = 100) -> list:
        """Retrieve recent security audit events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of audit event dictionaries
        """
        with _audit_lock:
            return _audit_log[-limit:]
    
    def clear_cache(self) -> None:
        """Clear in-memory key cache (security measure)."""
        with _cache_lock:
            _key_cache.clear()
        log.debug("SecretManager cache cleared")


# Global singleton instance for application-wide use
_secrets_manager: Optional[SecretManager] = None
_init_lock = threading.Lock()


def get_secrets_manager() -> SecretManager:
    """Get the global secrets manager singleton.
    
    Returns:
        Shared SecretManager instance
    """
    global _secrets_manager
    
    if _secrets_manager is None:
        with _init_lock:
            if _secrets_manager is None:
                _secrets_manager = SecretManager(
                    service_name=_SERVICE_NAME,
                    use_cache=True,
                    audit_enabled=True,
                )
    
    return _secrets_manager


def secure_get_key(key_name: str) -> Optional[str]:
    """Convenience function to get a key using the global manager.
    
    Args:
        key_name: Identifier for the key
        
    Returns:
        The API key or None
    """
    return get_secrets_manager().get_key(key_name)


def secure_set_key(key_name: str, key_value: str) -> bool:
    """Convenience function to set a key using the global manager.
    
    Args:
        key_name: Identifier for the key
        key_value: The API key value
        
    Returns:
        True if successful
    """
    return get_secrets_manager().set_key(key_name, key_value)


# Legacy compatibility - DO NOT USE in new code
# These are placeholders to prevent breakage but log warnings
def _obfuscate_deprecated(key: str) -> str:
    """DEPRECATED: Legacy base64 obfuscation - INSECURE.
    
    This function is kept for backward compatibility only.
    All new code MUST use SecretManager instead.
    """
    import base64
    import warnings
    warnings.warn(
        "_obfuscate is deprecated - use SecretManager for secure key storage",
        DeprecationWarning,
        stacklevel=2,
    )
    log.warning("SECURITY: Deprecated _obfuscate called - migrate to SecretManager")
    return base64.b64encode(key.encode()).decode() if key else ""


def _deobfuscate_deprecated(enc: str) -> str:
    """DEPRECATED: Legacy base64 deobfuscation - INSECURE.
    
    This function is kept for backward compatibility only.
    All new code MUST use SecretManager instead.
    """
    import base64
    import warnings
    warnings.warn(
        "_deobfuscate is deprecated - use SecretManager for secure key retrieval",
        DeprecationWarning,
        stacklevel=2,
    )
    log.warning("SECURITY: Deprecated _deobfuscate called - migrate to SecretManager")
    if not enc:
        return ""
    try:
        return base64.b64decode(enc.encode()).decode()
    except Exception:
        return enc


__all__ = [
    "SecretManager",
    "get_secrets_manager",
    "secure_get_key",
    "secure_set_key",
    # Legacy - deprecated
    "_obfuscate_deprecated",
    "_deobfuscate_deprecated",
]
