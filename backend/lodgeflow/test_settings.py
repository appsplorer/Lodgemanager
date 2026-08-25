"""Fast dependency-backed test settings; production/CI still verify PostgreSQL."""

from .settings import *  # noqa: F403


DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "lodgeflow-tests"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECURE_SSL_REDIRECT = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# Deterministic test-only Fernet key. Production still requires an explicit key
# through the environment and fails closed during settings validation.
CREDENTIAL_ENCRYPTION_KEYS = "MZyOsUUsn6iTJGwiNAT9BSIy2DGGm7m9RSMGAxuy5yI="
