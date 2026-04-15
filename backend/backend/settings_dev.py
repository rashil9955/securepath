# backend/settings_dev.py - Development-specific settings
from .settings_base import *

DEBUG = True

# Development-specific apps (optional - uncomment if you install django-extensions)
# INSTALLED_APPS += [
#     'django_extensions',
# ]

# Disable some security features for easier development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# More verbose logging in development
LOGGING['root']['level'] = 'DEBUG'

# Allow all hosts in development (not recommended for production)
ALLOWED_HOSTS = ['*']

# Email backend for development (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 2FA encryption key for development (hardcoded so .env is not required)
# In production, set TOTP_ENCRYPTION_KEY in your environment or .env
if not TOTP_ENCRYPTION_KEY:
    TOTP_ENCRYPTION_KEY = 'b3vqrjREHENAnZO1zxVXtmS-hg8u5RaYmaeuVUmMgl4='
