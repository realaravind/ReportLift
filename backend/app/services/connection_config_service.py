"""Connection Configuration Service - Manages encrypted service configurations."""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.connection_config import ConnectionConfig
from app.services.credential_store import get_credential_store, CredentialStoreError

logger = logging.getLogger(__name__)

# Sensitive fields that should be encrypted for each service type
SENSITIVE_FIELDS = {
    "ssrs": ["password"],
    "snowflake": ["password", "private_key"],
    "ollama": [],  # Ollama typically doesn't need credentials
}


class ConnectionConfigError(Exception):
    """Exception raised for connection config errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def save_connection_config(
    db: Session,
    service_type: str,
    config: dict[str, Any],
) -> ConnectionConfig:
    """Save a connection configuration with encrypted sensitive fields.

    Args:
        db: Database session
        service_type: Type of service ('ssrs', 'snowflake', 'ollama')
        config: Configuration dictionary with service settings

    Returns:
        The saved ConnectionConfig model

    Raises:
        ConnectionConfigError: If encryption or database operation fails
    """
    try:
        credential_store = get_credential_store()
    except CredentialStoreError as e:
        raise ConnectionConfigError(f"Credential store not available: {e.message}")

    # Get sensitive fields for this service type
    sensitive_keys = SENSITIVE_FIELDS.get(service_type, [])

    # Encrypt sensitive fields
    encrypted_config = config.copy()
    for key in sensitive_keys:
        if key in encrypted_config and encrypted_config[key]:
            encrypted_config[key] = credential_store.encrypt(str(encrypted_config[key]))
            # Log that we encrypted, but NEVER log the value
            logger.debug("Encrypted field '%s' for service '%s'", key, service_type)

    # Convert to JSON string
    config_json = json.dumps(encrypted_config)

    # Check if config already exists
    existing = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == service_type
    ).first()

    if existing:
        existing.encrypted_config = config_json
        db.commit()
        db.refresh(existing)
        logger.info("Updated connection config for service: %s", service_type)
        return existing
    else:
        new_config = ConnectionConfig(
            service_type=service_type,
            encrypted_config=config_json,
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        logger.info("Created connection config for service: %s", service_type)
        return new_config


def get_connection_config(
    db: Session,
    service_type: str,
    decrypt: bool = True,
) -> dict[str, Any] | None:
    """Retrieve a connection configuration, optionally decrypting sensitive fields.

    Args:
        db: Database session
        service_type: Type of service ('ssrs', 'snowflake', 'ollama')
        decrypt: Whether to decrypt sensitive fields (default True)

    Returns:
        Configuration dictionary with decrypted values, or None if not found

    Raises:
        ConnectionConfigError: If decryption fails
    """
    config_record = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == service_type
    ).first()

    if not config_record:
        return None

    try:
        config = json.loads(config_record.encrypted_config)
    except json.JSONDecodeError:
        raise ConnectionConfigError(
            f"Invalid configuration format for service: {service_type}"
        )

    if not decrypt:
        return config

    # Decrypt sensitive fields
    try:
        credential_store = get_credential_store()
    except CredentialStoreError as e:
        raise ConnectionConfigError(f"Credential store not available: {e.message}")

    sensitive_keys = SENSITIVE_FIELDS.get(service_type, [])
    for key in sensitive_keys:
        if key in config and config[key]:
            try:
                config[key] = credential_store.decrypt(str(config[key]))
                # NEVER log decrypted values
                logger.debug("Decrypted field '%s' for service '%s'", key, service_type)
            except CredentialStoreError:
                # If decryption fails, the value might not be encrypted
                # (e.g., from before encryption was enabled)
                logger.warning(
                    "Failed to decrypt field '%s' for service '%s'", key, service_type
                )

    return config


def delete_connection_config(db: Session, service_type: str) -> bool:
    """Delete a connection configuration.

    Args:
        db: Database session
        service_type: Type of service to delete

    Returns:
        True if deleted, False if not found
    """
    config_record = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == service_type
    ).first()

    if not config_record:
        return False

    db.delete(config_record)
    db.commit()
    logger.info("Deleted connection config for service: %s", service_type)
    return True


def list_connection_configs(db: Session) -> list[str]:
    """List all configured service types.

    Args:
        db: Database session

    Returns:
        List of configured service type names
    """
    configs = db.query(ConnectionConfig.service_type).all()
    return [c.service_type for c in configs]
