"""
TOTP (Time-based One-Time Password) utilities — RFC 6238
=========================================================

Security design decisions
--------------------------
* Secret storage — Fernet *encryption*, not hashing.
  The server must reconstruct the shared secret on every OTP verification,
  so hashing (one-way) cannot be used.  Fernet provides authenticated
  symmetric encryption; the TOTP_ENCRYPTION_KEY must be kept secret and
  rotated if compromised.

* OTP comparison — hmac.compare_digest (constant-time).
  Prevents timing-oracle attacks that could let an attacker brute-force
  the current OTP by measuring response latency.

* Clock drift — ±1 time step (30-second windows) accepted per RFC 6238 §5.2.
  Handles minor skew between the user's device clock and the server without
  opening a large replay window.

* Replay protection — last accepted TOTP counter stored per user.
  A code whose counter value ≤ the stored value is rejected even if it is
  cryptographically valid.

* Backup codes — bcrypt-hashed individually, consumed on first use.
  Plaintext codes are shown to the user exactly once; only hashes are stored.

* Brute-force guard — failed-attempt counter with DB-level lockout.
  After MAX_OTP_ATTEMPTS failures the account is locked for
  OTP_LOCKOUT_MINUTES.  For a production Redis-backed stack, replace with
  django-ratelimit or a cache-based counter for atomic increments.

* "Remember this device" — random 256-bit token, bcrypt-hashed and stored
  as a JSON list on the User.  Expires after DEVICE_TRUST_DAYS days (checked
  by the caller via a separate cookie max-age; the hash list itself has no
  expiry column — rotate by re-hashing on each use if desired).
"""

import hashlib
import hmac
import io
import json
import secrets
import time
import base64
from typing import List, Optional, Tuple

import bcrypt
import pyotp
import qrcode
from cryptography.fernet import Fernet
from django.conf import settings


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_OTP_ATTEMPTS = 5          # failed OTP attempts before lockout
OTP_LOCKOUT_MINUTES = 15      # how long the lockout lasts
BACKUP_CODE_COUNT = 8         # recovery codes generated per user
DEVICE_TRUST_DAYS = 30        # "remember this device" lifetime


# ─────────────────────────────────────────────────────────────────────────────
# Fernet encryption helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    """Return a Fernet cipher using TOTP_ENCRYPTION_KEY from settings."""
    key = getattr(settings, "TOTP_ENCRYPTION_KEY", None)
    if not key:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY is not configured. "
            "Generate one and add it to your .env:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_totp_secret(plaintext: str) -> str:
    """Encrypt the raw Base32 TOTP secret before writing to the database."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_totp_secret(ciphertext: str) -> str:
    """Decrypt a stored TOTP secret for OTP verification."""
    return _fernet().decrypt(ciphertext.encode()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# Secret & QR-code generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Return a cryptographically random Base32 TOTP secret (160 bits)."""
    return pyotp.random_base32()


def build_provisioning_uri(email: str, secret: str, issuer: str = "SecurePath") -> str:
    """Build the otpauth:// URI used by authenticator apps."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code_base64(email: str, secret: str, issuer: str = "SecurePath") -> str:
    """
    Generate a QR code for *secret* and return it as a base64-encoded PNG.
    Always pass the PLAINTEXT secret — never the encrypted form stored in DB.
    The frontend can embed this directly:
        <img src="data:image/png;base64,{qr_code}" />
    """
    uri = build_provisioning_uri(email, secret, issuer)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# OTP verification — RFC 6238, clock-drift tolerance, replay protection
# ─────────────────────────────────────────────────────────────────────────────

def verify_totp(
    plaintext_secret: str,
    otp: str,
    last_used_counter: Optional[int],
) -> Tuple[bool, Optional[int]]:
    """
    Verify a 6-digit TOTP code.

    Parameters
    ----------
    plaintext_secret : str
        The decrypted Base32 secret shared with the user's authenticator app.
    otp : str
        The 6-digit code supplied by the user.
    last_used_counter : int | None
        The TOTP counter (unix_timestamp // 30) of the most recently accepted
        code for this user, used to detect replays.  Pass None for the very
        first verification.

    Returns
    -------
    (True, counter)  — OTP is valid; persist *counter* to last_otp_counter.
    (False, None)    — OTP is invalid or replayed.

    Clock-drift policy
    ------------------
    We check the previous window (delta = -1), the current window (0), and
    the next window (+1).  This gives a ±30-second tolerance, sufficient for
    most NTP-synced devices without opening a meaningful replay window.

    Time-sync note
    --------------
    If users consistently get "invalid code" errors, the server's system clock
    may be drifting.  Ensure NTP is running (`timedatectl status` on Linux).
    Increasing valid_window beyond 1 is not recommended — it widens the replay
    window without addressing the root cause.
    """
    totp = pyotp.TOTP(plaintext_secret)
    now_counter = int(time.time()) // 30

    for delta in (-1, 0, 1):
        candidate = now_counter + delta
        expected = totp.at(candidate * 30)
        # constant-time string comparison — no timing oracle
        if hmac.compare_digest(otp.zfill(6), expected.zfill(6)):
            if last_used_counter is not None and candidate <= last_used_counter:
                return False, None  # replay detected
            return True, candidate

    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# Backup / recovery codes
# ─────────────────────────────────────────────────────────────────────────────

def generate_backup_codes() -> List[str]:
    """
    Generate BACKUP_CODE_COUNT one-time recovery codes in XXXXX-XXXXX format.
    Returns the *plaintext* list — the caller must hash before storing.
    Show these to the user exactly once; they cannot be recovered afterward.
    """
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        raw = secrets.token_hex(5)          # 5 bytes → 10 hex chars
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_backup_codes(codes: List[str]) -> str:
    """Bcrypt-hash each backup code and return a JSON string for DB storage."""
    hashed = [
        bcrypt.hashpw(c.replace("-", "").lower().encode(), bcrypt.gensalt()).decode()
        for c in codes
    ]
    return json.dumps(hashed)


def consume_backup_code(supplied: str, hashed_json: str) -> Tuple[bool, str]:
    """
    Attempt to use *supplied* as a backup code.
    On success, removes the matched hash (one-time use) and returns the
    updated JSON string.

    Returns
    -------
    (True, updated_json)   — code was valid and has been consumed.
    (False, original_json) — code not found; nothing changed.
    """
    normalized = supplied.replace("-", "").lower().encode()
    stored: List[str] = json.loads(hashed_json)

    for i, stored_hash in enumerate(stored):
        try:
            if bcrypt.checkpw(normalized, stored_hash.encode()):
                remaining = stored[:i] + stored[i + 1:]
                return True, json.dumps(remaining)
        except Exception:
            continue

    return False, hashed_json


# ─────────────────────────────────────────────────────────────────────────────
# Brute-force guard
# ─────────────────────────────────────────────────────────────────────────────

def check_otp_rate_limit(user) -> Tuple[bool, Optional[str]]:
    """
    Check whether the user is currently locked out of OTP attempts.

    Returns (True, None) if the attempt is allowed.
    Returns (False, error_message) if locked out.
    Automatically clears an expired lockout.
    """
    from django.utils import timezone

    if user.otp_lockout_until and user.otp_lockout_until > timezone.now():
        remaining = int((user.otp_lockout_until - timezone.now()).total_seconds() // 60) + 1
        return False, f"Too many failed attempts. Try again in {remaining} minute(s)."

    # Lockout has expired — clear it
    if user.otp_lockout_until and user.otp_lockout_until <= timezone.now():
        user.otp_failed_attempts = 0
        user.otp_lockout_until = None
        user.save(update_fields=["otp_failed_attempts", "otp_lockout_until"])

    return True, None


def record_otp_failure(user) -> None:
    """
    Increment the OTP failure counter.
    If MAX_OTP_ATTEMPTS is reached, apply a lockout and reset the counter.
    """
    from django.utils import timezone
    from datetime import timedelta

    user.otp_failed_attempts += 1
    if user.otp_failed_attempts >= MAX_OTP_ATTEMPTS:
        user.otp_lockout_until = timezone.now() + timedelta(minutes=OTP_LOCKOUT_MINUTES)
        user.otp_failed_attempts = 0

    user.save(update_fields=["otp_failed_attempts", "otp_lockout_until"])


def reset_otp_failures(user) -> None:
    """Clear the failure counter after a successful OTP verification."""
    user.otp_failed_attempts = 0
    user.otp_lockout_until = None
    user.save(update_fields=["otp_failed_attempts", "otp_lockout_until"])


# ─────────────────────────────────────────────────────────────────────────────
# "Remember this device" helpers
# ─────────────────────────────────────────────────────────────────────────────

def generate_device_token() -> str:
    """Return a random 256-bit hex device token (sent to the browser as a cookie)."""
    return secrets.token_hex(32)


def _hash_device_token(token: str) -> str:
    """SHA-256 hash of the device token (fast; tokens are already random)."""
    return hashlib.sha256(token.encode()).hexdigest()


def store_device_token(user, token: str) -> None:
    """Add a new device token hash to the user's trusted list (max 10 devices)."""
    existing: List[str] = json.loads(user.trusted_device_tokens or "[]")
    existing.append(_hash_device_token(token))
    # Keep only the most recent 10 trusted devices
    user.trusted_device_tokens = json.dumps(existing[-10:])
    user.save(update_fields=["trusted_device_tokens"])


def verify_device_token(user, token: str) -> bool:
    """Return True if *token* matches a stored trusted-device hash."""
    if not user.trusted_device_tokens:
        return False
    stored: List[str] = json.loads(user.trusted_device_tokens)
    token_hash = _hash_device_token(token)
    # constant-time comparison across the list
    return any(hmac.compare_digest(token_hash, h) for h in stored)
