import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass

from core.config import get_settings
from core.errors import APIError


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    email: str

    def can_manage_members(self) -> bool:
        return self.role in {"owner", "admin"}


def issue_token(principal: Principal, expires_in_seconds: int = 60 * 60 * 8) -> str:
    payload = {
        "sub": str(principal.user_id),
        "tenant": str(principal.tenant_id),
        "role": principal.role,
        "email": principal.email,
        "exp": int(time.time()) + expires_in_seconds,
    }
    encoded = _encode(payload)
    signature = _sign(encoded)
    return f"{encoded}.{signature}"


def decode_token(token: str) -> Principal:
    try:
        encoded, signature = token.split(".", 1)
        expected = _sign(encoded)
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(_decode(encoded))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError
        return Principal(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant"]),
            role=str(payload["role"]),
            email=str(payload["email"]),
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise APIError(401, "invalid_token", "Authentication token is invalid") from None


def _encode(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()


def _sign(value: str) -> str:
    secret = get_settings().auth_secret.encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_value, digest_value = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.urlsafe_b64decode(salt_value),
            n=2**14,
            r=8,
            p=1,
        )
        expected = base64.urlsafe_b64decode(digest_value)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
