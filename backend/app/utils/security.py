"""Security utilities for password hashing, JWT tokens, and token encryption."""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from ..settings import settings

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise e


# ── Token encryption (Fernet) ──────────────────────────────────────
# Derives a 32-byte Fernet key from SECRET_KEY via SHA-256 so we don't
# need a separate ENCRYPTION_KEY config value.
def _fernet_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_token(plaintext: str) -> str:
    """Encrypt a string (e.g. an OAuth access token) and return base64 ciphertext."""
    from cryptography.fernet import Fernet
    f = Fernet(_fernet_key())
    return f.encrypt(plaintext.encode()).decode()

def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token back to plaintext."""
    from cryptography.fernet import Fernet
    f = Fernet(_fernet_key())
    return f.decrypt(ciphertext.encode()).decode()
