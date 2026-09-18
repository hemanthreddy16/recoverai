"""Authentication, JWT handling, password hashing and role-based access."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
)

Role = Literal["admin", "operator", "viewer"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, merchant_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "merchant_id": merchant_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


class AuthUser:
    """Lightweight authenticated principal used by dependencies."""

    def __init__(self, user_id: int, merchant_id: int, role: str, email: str):
        self.user_id = user_id
        self.merchant_id = merchant_id
        self.role = role
        self.email = email


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AuthUser:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exc

    user_id = payload.get("sub")
    merchant_id = payload.get("merchant_id")
    role = payload.get("role")
    if user_id is None or merchant_id is None:
        raise credentials_exc

    from app.models.users import User

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exc
    # Defensive: ensure token merchant matches the user's merchant.
    if user.merchant_id != int(merchant_id):
        raise credentials_exc

    return AuthUser(user.id, user.merchant_id, role or user.role, user.email)


def require_role(*roles: str):
    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return user

    return checker


def get_merchant_filter(user: AuthUser):
    """Return the merchant_id that all queries must be scoped to (isolation)."""
    return user.merchant_id
