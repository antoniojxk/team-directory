from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

SCOPES = {
    "directory:read": "Read public profiles, employment and compliance",
    "records:write": "Create and update directory records",
    "confidential:read": "Read confidential details (audited)",
    "confidential:write": "Update private notes and salaries",
    "audit:read": "Read confidential-access audit history",
}
ROLE_PERMISSIONS = {"viewer": ["directory:read"], "hr": list(SCOPES)}
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token", scopes=SCOPES)
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummy-password-never-used-for-login")
DB = Annotated[Session, Depends(get_db)]


def permissions_for(user: User) -> list[str]:
    """Combine role grants; unrecognized roles and empty assignments grant nothing."""
    grants = {scope for role in user.roles for scope in ROLE_PERMISSIONS.get(role.name, [])}
    return [scope for scope in SCOPES if scope in grants]


def create_token(user: User, lifetime: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now
            + (
                lifetime
                if lifetime is not None
                else timedelta(minutes=settings.access_token_minutes)
            ),
            "iss": "team-directory",
            "aud": "team-directory-api",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(
    security_scopes: SecurityScopes,
    db: DB,
    token: Annotated[str, Depends(oauth2)],
) -> User:
    user = authenticate(db, token)
    permissions = permissions_for(user)
    if any(scope not in permissions for scope in security_scopes.scopes):
        raise HTTPException(status_code=403, detail="You do not have permission for this action.")
    return user


def authenticate(db: Session, token: str) -> User:
    error = HTTPException(
        status_code=401,
        detail="Your session has expired or is invalid. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="team-directory",
            audience="team-directory-api",
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        user_id = int(claims["sub"])
        if not 0 < user_id <= 2147483647:
            raise ValueError("Invalid subject")
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise error from None
    user = db.get(User, user_id)
    if user is None:
        raise error
    # Always use current database assignments, never client-supplied roles or JWT scopes.
    return user
