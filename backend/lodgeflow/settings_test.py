"""Fast local test settings only. Production/integration CI still uses PostgreSQL + Redis."""
from .settings import *  # noqa: F401,F403
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'test.sqlite3'}}
CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache','LOCATION':'lodgeflow-tests'}}
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
SECURE_SSL_REDIRECT=False
DEBUG=True
