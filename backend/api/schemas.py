# api/schemas.py
from ninja import Schema
from pydantic import EmailStr, Field
from typing import Optional

class UploadResponse(Schema):
    status: str
    message: str
    records_uploaded: int
    duplicates_removed: int
    duration_seconds: float

class TransactionOut(Schema):
    id: int
    transaction_id: str
    amount: float = None
    merchant: str = None
    date: str = None
    risk_score: float = None
    reason_code: str = None
    status: str
    risk_level: str

class DashboardStats(Schema):
    total_transactions: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    pending_count: int
    approved_count: int
    rejected_count: int
    avg_risk_score: float
    total_amount: float

class DecisionIn(Schema):
    transaction_id: str
    decision: str
    reason: str = ""

class FraudDetectionResult(Schema):
    total_processed: int
    flagged_count: int
    duration_seconds: float
    results: list

class PlaidExchangeRequest(Schema):
    public_token: str

# Authentication Schemas
class UserRegister(Schema):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

class UserLogin(Schema):
    email: EmailStr
    password: str

class UserResponse(Schema):
    id: int
    email: str
    is_active: bool
    created_at: str

class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── 2FA Schemas ──────────────────────────────────────────────────────────────

class TwoFASetupResponse(Schema):
    """Returned by POST /2fa/setup. Show the QR code and manual key to the user."""
    qr_code: str     # base64-encoded PNG — embed as <img src="data:image/png;base64,{qr_code}">
    manual_key: str  # plaintext Base32 secret for manual entry in authenticator apps
    message: str


class TwoFAEnableRequest(Schema):
    """Body for POST /2fa/enable — user proves authenticator is working."""
    otp: str = Field(..., min_length=6, max_length=6)


class TwoFAEnableResponse(Schema):
    """
    Returned on successful 2FA enable.
    backup_codes is shown ONCE — the user must save them before closing the page.
    """
    message: str
    backup_codes: list  # 8 plaintext codes in XXXXX-XXXXX format


class TwoFADisableRequest(Schema):
    """Body for POST /2fa/disable — requires password plus OTP or a backup code."""
    password: str
    otp: str = ""          # current TOTP code
    backup_code: str = ""  # alternative to otp


class TwoFALoginVerifyRequest(Schema):
    """
    Body for POST /2fa/login-verify.
    two_fa_token is the short-lived token returned by POST /auth/login when
    the account has 2FA enabled. Supply either otp or backup_code.
    """
    two_fa_token: str
    otp: str = ""
    backup_code: str = ""
    remember_device: bool = False  # if True, a 30-day device cookie is set


class TwoFAStatusResponse(Schema):
    """Returned by GET /2fa/status."""
    is_2fa_enabled: bool
    backup_codes_remaining: Optional[int] = None


class TwoFABackupCodesResponse(Schema):
    """Returned when backup codes are regenerated."""
    message: str
    backup_codes: list