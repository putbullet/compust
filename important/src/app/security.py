from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

settings = get_settings()
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash plaintext password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


def get_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    token: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> User:
    """Dependency: require a valid authenticated user via Bearer token or query token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    jwt_token = auth.credentials if (auth and auth.credentials) else token
    if not jwt_token:
        raise credentials_exception

    payload = decode_access_token(jwt_token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_sub = str(user_id)
    if user_sub.isdigit():
        user = db.scalar(select(User).where(User.id == int(user_sub)))
    else:
        user = db.scalar(select(User).where(User.email == user_sub))

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    return user


def get_optional_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    token: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> User | None:
    """Dependency: optionally return authenticated user if token present and valid."""
    jwt_token = auth.credentials if (auth and auth.credentials) else token
    if not jwt_token:
        return None

    payload = decode_access_token(jwt_token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_sub = str(user_id)
        if user_sub.isdigit():
            user = db.scalar(select(User).where(User.id == int(user_sub)))
        else:
            user = db.scalar(select(User).where(User.email == user_sub))
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None
