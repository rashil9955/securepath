from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    """Main transaction model with all required fields"""

    # User relationship - each transaction belongs to a user
    # Using string reference since User is defined later
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)

    # Core transaction fields
    transaction_id = models.CharField(max_length=100, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(db_index=True)
    merchant = models.CharField(max_length=200)
    card_number = models.CharField(max_length=20)

    # Additional context fields
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=2, default='US')
    currency = models.CharField(max_length=3, default='USD')

    # Fraud detection fields
    fraud_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Rule-based risk score (0-100)")
    is_fraud = models.BooleanField(default=False, db_index=True)
    fraud_reasons = models.TextField(null=True, blank=True)
    reason_code = models.TextField(null=True, blank=True, help_text="Detailed fraud detection reasons")

    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'transaction_id']),
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_fraud']),
        ]
        # Unique constraint: transaction_id should be unique per user
        unique_together = [['user', 'transaction_id']]

    def __str__(self):
        return f"{self.transaction_id} - ${self.amount} - {self.status}"


class AuditLog(models.Model):
    """Audit log for tracking all system actions"""

    # User relationship - each audit log belongs to a user
    # Using string reference since User is defined later
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)

    # Action details
    action = models.CharField(max_length=100, db_index=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    details = models.TextField(null=True, blank=True)

    # User context (legacy - keeping for backward compatibility)
    user_string = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['user', 'transaction_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class SystemMetrics(models.Model):
    """System performance and health metrics"""

    # Performance metrics
    cpu_usage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    memory_usage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Transaction metrics
    active_transactions = models.IntegerField(default=0)
    total_transactions = models.IntegerField(default=0)
    fraud_detected = models.IntegerField(default=0)

    # Response time metrics
    avg_response_time = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "System Metrics"

    def __str__(self):
        return f"Metrics - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class User(models.Model):
    """User model for authentication"""
    email = models.EmailField(unique=True, db_index=True)
    hashed_password = models.CharField(max_length=255, null=True, blank=True)  # Nullable for OAuth-only users
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── 2FA fields ──────────────────────────────────────────────────────────
    # Secret is Fernet-encrypted at rest; never stored in plaintext.
    # We encrypt (not hash) because the server must reconstruct the secret
    # on every OTP verification — hashing is irreversible and cannot be used.
    totp_secret = models.CharField(max_length=500, null=True, blank=True)
    # Holds a newly generated secret during setup, before the user has
    # proved they can produce a valid OTP.  Promoted to totp_secret on enable.
    totp_pending_secret = models.CharField(max_length=500, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)
    # JSON array of bcrypt-hashed one-time backup codes.
    backup_codes = models.TextField(null=True, blank=True)
    # TOTP counter (unix_ts // 30) of the last accepted code — replay guard.
    last_otp_counter = models.IntegerField(null=True, blank=True)
    # Brute-force protection
    otp_failed_attempts = models.IntegerField(default=0)
    otp_lockout_until = models.DateTimeField(null=True, blank=True)
    # "Remember this device" — stores hashed device tokens (JSON list)
    trusted_device_tokens = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class OAuthAccount(models.Model):
    """OAuth account linking - connects OAuth providers to users"""
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('github', 'GitHub'),
        ('apple', 'Apple'),
    ]
    
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)  # User ID from OAuth provider
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oauth_accounts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['provider', 'provider_user_id']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.provider}"


class RefreshToken(models.Model):
    """Refresh token storage for JWT authentication"""
    token = models.CharField(max_length=500, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_revoked']),
        ]

    def __str__(self):
        return f"Refresh token for {self.user.email}"