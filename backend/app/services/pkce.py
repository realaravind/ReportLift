"""PKCE (Proof Key for Code Exchange) utilities for OAuth2.

PKCE is an extension to OAuth2 that helps protect authorization codes
from interception attacks. It's especially important for public clients
(like SPAs or mobile apps) that can't securely store a client secret.

Flow:
1. Generate a random code_verifier (43-128 characters)
2. Generate code_challenge = base64url(sha256(code_verifier))
3. Send code_challenge with authorization request
4. Send code_verifier with token exchange request
5. IdP verifies: base64url(sha256(code_verifier)) == code_challenge
"""

import base64
import hashlib
import secrets
import string


def generate_code_verifier(length: int = 96) -> str:
    """Generate a cryptographically random code verifier.

    Per RFC 7636, the code verifier must be:
    - Between 43 and 128 characters
    - Using only unreserved characters: A-Z, a-z, 0-9, and -._~

    Args:
        length: Length of the verifier (default 96, between 43-128)

    Returns:
        Random code verifier string
    """
    if length < 43 or length > 128:
        raise ValueError("Code verifier length must be between 43 and 128")

    # Use secrets.token_urlsafe which generates base64url-safe characters
    # token_urlsafe(n) generates n bytes, then base64 encodes to ~4/3 * n chars
    # We need to generate enough bytes to get our desired length
    bytes_needed = (length * 3) // 4 + 1
    token = secrets.token_urlsafe(bytes_needed)

    # Truncate to exact length
    return token[:length]


def generate_code_challenge(code_verifier: str) -> str:
    """Generate code challenge from code verifier using SHA-256.

    The code challenge is the base64url-encoded SHA-256 hash of the
    code verifier. This is sent with the authorization request.

    Args:
        code_verifier: The code verifier string

    Returns:
        Base64url-encoded SHA-256 hash (without padding)
    """
    # Compute SHA-256 hash of the code verifier
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()

    # Base64url encode without padding
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return challenge


def generate_state(length: int = 32) -> str:
    """Generate a random state parameter for CSRF protection.

    The state parameter is sent with the authorization request and
    must be verified when receiving the callback to prevent CSRF attacks.

    Args:
        length: Length of the state parameter (default 32)

    Returns:
        Random state string
    """
    return secrets.token_urlsafe(length)[:length]


def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
    """Verify that a code challenge matches the code verifier.

    This is used for testing and validation. The IdP performs this
    verification during token exchange.

    Args:
        code_verifier: The original code verifier
        code_challenge: The code challenge to verify

    Returns:
        True if the challenge matches the verifier
    """
    expected_challenge = generate_code_challenge(code_verifier)
    return secrets.compare_digest(expected_challenge, code_challenge)
