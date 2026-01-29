"""Credential Store Service - Encrypts and decrypts sensitive credentials."""

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class CredentialStoreError(Exception):
    """Exception raised for credential store errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CredentialStore:
    """Service for encrypting and decrypting credentials using Fernet (AES-128-CBC).

    Fernet guarantees that a message encrypted using it cannot be manipulated
    or read without the key. It uses AES-128-CBC for encryption and
    HMAC-SHA256 for authentication.
    """

    def __init__(self, encryption_key: str):
        """Initialize the credential store with an encryption key.

        Args:
            encryption_key: A valid Fernet key (32-byte base64-encoded string)

        Raises:
            CredentialStoreError: If the key is invalid
        """
        try:
            self._fernet = Fernet(encryption_key.encode())
            logger.info("Credential store initialized successfully")
        except Exception as e:
            # Never log the actual key
            logger.error("Failed to initialize credential store: invalid encryption key")
            raise CredentialStoreError(
                "Invalid encryption key format. Must be a valid 32-byte base64-encoded Fernet key."
            ) from e

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a credential string.

        Args:
            plaintext: The credential value to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            CredentialStoreError: If encryption fails
        """
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            # Log that encryption occurred, but never log the value
            logger.debug("Credential encrypted successfully")
            return encrypted.decode()
        except Exception as e:
            logger.error("Encryption failed: %s", type(e).__name__)
            raise CredentialStoreError("Failed to encrypt credential") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a credential string.

        Args:
            ciphertext: The base64-encoded encrypted string

        Returns:
            The decrypted plaintext credential

        Raises:
            CredentialStoreError: If decryption fails (invalid token or corrupted data)
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            # Log that decryption occurred, but NEVER log the decrypted value
            logger.debug("Credential decrypted successfully")
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token or corrupted data")
            raise CredentialStoreError(
                "Failed to decrypt credential: invalid token or encryption key mismatch"
            )
        except Exception as e:
            logger.error("Decryption failed: %s", type(e).__name__)
            raise CredentialStoreError("Failed to decrypt credential") from e

    def encrypt_dict(self, data: dict[str, Any], sensitive_keys: list[str]) -> dict[str, Any]:
        """Encrypt specific keys in a dictionary.

        Args:
            data: Dictionary containing data to encrypt
            sensitive_keys: List of keys whose values should be encrypted

        Returns:
            Dictionary with sensitive values encrypted
        """
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                result[key] = self.encrypt(str(result[key]))
        return result

    def decrypt_dict(self, data: dict[str, Any], sensitive_keys: list[str]) -> dict[str, Any]:
        """Decrypt specific keys in a dictionary.

        Args:
            data: Dictionary containing encrypted data
            sensitive_keys: List of keys whose values should be decrypted

        Returns:
            Dictionary with sensitive values decrypted
        """
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                result[key] = self.decrypt(str(result[key]))
        return result


def validate_encryption_key(key: str | None) -> None:
    """Validate that an encryption key is present and valid.

    Args:
        key: The encryption key to validate

    Raises:
        CredentialStoreError: If the key is missing or invalid
    """
    if not key:
        raise CredentialStoreError(
            "ENCRYPTION_KEY environment variable is required but not set. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    try:
        # Attempt to create a Fernet instance to validate the key
        Fernet(key.encode())
    except Exception:
        raise CredentialStoreError(
            "ENCRYPTION_KEY is invalid. Must be a valid 32-byte base64-encoded Fernet key. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )


# Singleton instance - initialized lazily
_credential_store: CredentialStore | None = None


def get_credential_store() -> CredentialStore:
    """Get the global credential store instance.

    Returns:
        The credential store singleton

    Raises:
        CredentialStoreError: If the store hasn't been initialized
    """
    global _credential_store
    if _credential_store is None:
        raise CredentialStoreError(
            "Credential store not initialized. Call init_credential_store() first."
        )
    return _credential_store


def init_credential_store(encryption_key: str) -> CredentialStore:
    """Initialize the global credential store.

    Args:
        encryption_key: A valid Fernet encryption key

    Returns:
        The initialized credential store
    """
    global _credential_store
    validate_encryption_key(encryption_key)
    _credential_store = CredentialStore(encryption_key)
    return _credential_store
