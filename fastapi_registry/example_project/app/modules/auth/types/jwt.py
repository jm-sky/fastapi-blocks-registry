"""JWT type definitions for authentication module."""

from typing import TypedDict


class JWTPayload(TypedDict, total=False):
    """JWT token payload structure.

    Attributes:
        sub: Subject (user ID)
        exp: Expiration time (Unix timestamp)
        iat: Issued at (Unix timestamp)
        type: Token type - "access", "refresh", or "reset"
    """
    sub: str
    exp: int
    iat: int
    type: str
