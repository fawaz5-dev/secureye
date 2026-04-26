"""
signer.py — stateless token signing for Secureye

Token payload:
  {
    "mode":     "eye" | "key",
    "hostname": "example.com",
    "jti":      "<uuid>",      -- unique nonce, prevents replay within TTL window
    "iat":      1234567890,    -- issued at (unix)
    "exp":      1234567950,    -- expires at (iat + 60s)
  }

No sitekey. No secret per integrator. One shared signing secret on the server.
The signature is the proof. Stateless by design.
"""

import os
import json
import hmac
import hashlib
import base64
import time
import uuid

SIGNING_SECRET = os.getenv(
    "SECUREYE_SIGNING_SECRET",
    "CHANGE_ME_BEFORE_DEPLOY_use_a_32char_secret_minimum"
)

TOKEN_TTL = 60  # seconds


class TokenError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code    = code
        self.message = message
        super().__init__(message or code)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def sign_token(mode: str, hostname: str) -> str:
    """Sign a human-proof token. Returns a compact token string."""
    header  = {"alg": "HS256", "typ": "SEY"}
    payload = {
        "mode":     mode,
        "hostname": hostname,
        "jti":      str(uuid.uuid4()),
        "iat":      int(time.time()),
        "exp":      int(time.time()) + TOKEN_TTL,
    }
    h = _b64url_encode(json.dumps(header,  separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}"
    sig = hmac.new(
        SIGNING_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


# In-memory nonce set — prevents replay within server lifetime.
# Tokens only live 60s so this stays tiny. Prune at 10k entries.
_used_nonces: set[str] = set()


def verify_token(token: str) -> dict:
    """
    Verify a Secureye token. Returns payload on success.
    Raises TokenError on any failure.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("invalid-input-token", "Malformed token")

    h, p, sig = parts
    signing_input = f"{h}.{p}"

    # 1. Verify HMAC signature
    expected_sig = hmac.new(
        SIGNING_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(expected_sig, _b64url_decode(sig)):
        raise TokenError("invalid-input-token", "Signature mismatch")

    # 2. Decode payload
    try:
        payload = json.loads(_b64url_decode(p))
    except Exception:
        raise TokenError("invalid-input-token", "Cannot decode payload")

    # 3. Check expiry
    if int(time.time()) > payload.get("exp", 0):
        raise TokenError("token-expired")

    # 4. Replay prevention
    jti = payload.get("jti", "")
    if jti in _used_nonces:
        raise TokenError("token-already-used")
    _used_nonces.add(jti)
    if len(_used_nonces) > 10_000:
        _used_nonces.clear()

    return payload
