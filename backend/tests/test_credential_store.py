"""Tests for credential store service."""

import pytest
from cryptography.fernet import Fernet

from app.services.credential_store import (
    CredentialStore,
    CredentialStoreError,
    validate_encryption_key,
)


class TestCredentialStore:
    """Tests for CredentialStore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_key = Fernet.generate_key().decode()
        self.store = CredentialStore(self.valid_key)

    def test_encrypt_returns_different_value(self):
        """Test that encryption produces a different string."""
        plaintext = "my_secret_password"
        encrypted = self.store.encrypt(plaintext)
        assert encrypted != plaintext

    def test_decrypt_returns_original(self):
        """Test that decryption returns the original value."""
        plaintext = "my_secret_password"
        encrypted = self.store.encrypt(plaintext)
        decrypted = self.store.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string_returns_empty(self):
        """Test that encrypting empty string returns empty."""
        assert self.store.encrypt("") == ""

    def test_decrypt_empty_string_returns_empty(self):
        """Test that decrypting empty string returns empty."""
        assert self.store.decrypt("") == ""

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid token raises error."""
        with pytest.raises(CredentialStoreError) as exc_info:
            self.store.decrypt("invalid_ciphertext")
        assert "invalid token" in exc_info.value.message.lower()

    def test_encrypt_dict_encrypts_sensitive_keys(self):
        """Test that encrypt_dict only encrypts specified keys."""
        data = {
            "username": "admin",
            "password": "secret123",
            "host": "localhost",
        }
        encrypted = self.store.encrypt_dict(data, ["password"])

        assert encrypted["username"] == "admin"  # Not encrypted
        assert encrypted["host"] == "localhost"  # Not encrypted
        assert encrypted["password"] != "secret123"  # Encrypted

    def test_decrypt_dict_decrypts_sensitive_keys(self):
        """Test that decrypt_dict decrypts specified keys."""
        data = {
            "username": "admin",
            "password": "secret123",
            "host": "localhost",
        }
        encrypted = self.store.encrypt_dict(data, ["password"])
        decrypted = self.store.decrypt_dict(encrypted, ["password"])

        assert decrypted["username"] == "admin"
        assert decrypted["password"] == "secret123"
        assert decrypted["host"] == "localhost"


class TestValidateEncryptionKey:
    """Tests for validate_encryption_key function."""

    def test_valid_key_does_not_raise(self):
        """Test that valid key passes validation."""
        valid_key = Fernet.generate_key().decode()
        validate_encryption_key(valid_key)  # Should not raise

    def test_none_key_raises_error(self):
        """Test that None key raises error."""
        with pytest.raises(CredentialStoreError) as exc_info:
            validate_encryption_key(None)
        assert "required" in exc_info.value.message.lower()

    def test_empty_key_raises_error(self):
        """Test that empty key raises error."""
        with pytest.raises(CredentialStoreError) as exc_info:
            validate_encryption_key("")
        assert "required" in exc_info.value.message.lower()

    def test_invalid_key_format_raises_error(self):
        """Test that invalid key format raises error."""
        with pytest.raises(CredentialStoreError) as exc_info:
            validate_encryption_key("not_a_valid_fernet_key")
        assert "invalid" in exc_info.value.message.lower()


class TestCredentialStoreInitialization:
    """Tests for CredentialStore initialization."""

    def test_invalid_key_raises_error(self):
        """Test that invalid key raises error on initialization."""
        with pytest.raises(CredentialStoreError) as exc_info:
            CredentialStore("invalid_key")
        assert "invalid" in exc_info.value.message.lower()

    def test_valid_key_initializes_successfully(self):
        """Test that valid key initializes successfully."""
        valid_key = Fernet.generate_key().decode()
        store = CredentialStore(valid_key)
        assert store is not None
