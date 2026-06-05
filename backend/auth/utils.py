import logging
import bcrypt
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timedelta
from typing import Optional
from config.settings import settings
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Request
from models.schemas import TokenData

logger = logging.getLogger("nutritionvqa.auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/signin", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        if not plain_password or not hashed_password:
            return False
        pwd_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {type(e).__name__}: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with the given data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.info(f"Token created for: {data.get('sub', 'unknown')} (expires: {expire.isoformat()})")
    return encoded_jwt


async def get_current_user_email(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    """Extract and validate the user's email from a JWT Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        auth_header = request.headers.get("Authorization", "")
        logger.warning(f"Auth failed: No token extracted. Raw header: '{auth_header[:50]}...' | URL: {request.url.path}")
        raise credentials_exception

    if token.strip() in ("null", "undefined", ""):
        logger.warning(f"Auth failed: token is literal '{token}' (frontend has no valid token in localStorage)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid session. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Auth failed: token decoded OK but has no 'sub' claim")
            raise credentials_exception
        logger.debug(f"Auth OK: {email}")
        return email

    except ExpiredSignatureError:
        logger.warning(f"Auth failed: token EXPIRED for URL {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"Auth failed: JWT decode error — {type(e).__name__}: {e} | token prefix: {token[:20]}...")
        raise credentials_exception
