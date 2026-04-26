"""
Secureye API — stateless FastAPI backend
One job: issue and verify signed human-proof tokens.

No database. No sitekeys. No user accounts.
The signing secret lives in an env var. That's the entire state of this service.
"""

import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from signer import sign_token, verify_token, TokenError

app = FastAPI(title="Secureye API", version="0.2.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── SCHEMAS ────────────────────────────────────────────────────────────────

class IssueRequest(BaseModel):
    mode:     str   # "eye" | "key"
    hostname: str   # origin the widget is on

class VerifyRequest(BaseModel):
    token: str      # token from the client widget


# ── HEALTH ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Secureye API", "version": "0.2.0"}

@app.get("/health")
def health():
    return {"status": "ok", "ts": int(time.time())}


# ── ISSUE — called by verify.html after liveness passes ────────────────────
# Browser sends mode + hostname. Backend signs and returns a token.
# No sitekey, no lookup, no state.

@app.post("/v1/issue")
async def issue_token(req: IssueRequest):
    if req.mode not in ("eye", "key"):
        return JSONResponse(
            {"success": False, "error-codes": ["invalid-mode"]},
            status_code=400
        )
    token = sign_token(mode=req.mode, hostname=req.hostname)
    return {"success": True, "token": token}


# ── VERIFY — called by integrator's backend to validate a token ─────────────
# No secret key needed from integrators. The shared signing secret
# is what proves a token came from Secureye. Just send the token.

@app.post("/v1/verify")
async def verify(req: VerifyRequest):
    if not req.token:
        return JSONResponse({
            "success":     False,
            "error-codes": ["missing-input-token"],
        })
    try:
        claims = verify_token(req.token)
    except TokenError as e:
        return JSONResponse({
            "success":     False,
            "error-codes": [e.code],
        })
    return {
        "success":   True,
        "mode":      claims["mode"],
        "hostname":  claims["hostname"],
        "issued_at": claims["iat"],
    }
