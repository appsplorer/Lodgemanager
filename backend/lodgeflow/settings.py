import os
from pathlib import Path
from urllib.parse import urlsplit
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY','dev-only-change-me')
DEBUG=os.getenv('DEBUG','false').lower()=='true'
ALLOWED_HOSTS=[x.strip() for x in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if x.strip()]

if not DEBUG:
 if len(SECRET_KEY)<50 or SECRET_KEY in {'dev-only-change-me','replace-with-64-plus-random-characters'}:
  raise RuntimeError('DJANGO_SECRET_KEY must be a strong non-placeholder secret in production')
 if not os.getenv('POSTGRES_PASSWORD','').strip(): raise RuntimeError('POSTGRES_PASSWORD is required in production')
 if not os.getenv('CREDENTIAL_ENCRYPTION_KEYS','').strip() or os.getenv('CREDENTIAL_ENCRYPTION_KEYS','').startswith('replace-'):
  raise RuntimeError('CREDENTIAL_ENCRYPTION_KEYS is required in production')
 if not os.getenv('CSRF_TRUSTED_ORIGINS','').strip(): raise RuntimeError('CSRF_TRUSTED_ORIGINS is required in production')
 public_hosts=[h for h in ALLOWED_HOSTS if h not in {'backend','localhost','127.0.0.1'}]
 if not public_hosts or any(h.endswith('.example.com') for h in public_hosts): raise RuntimeError('Set a real public ALLOWED_HOSTS value in production')

FRONTEND_BASE_URL=os.getenv('FRONTEND_BASE_URL','http://localhost:3000' if DEBUG else '').strip().rstrip('/')
if not FRONTEND_BASE_URL:
 raise RuntimeError('FRONTEND_BASE_URL is required')
frontend_url=urlsplit(FRONTEND_BASE_URL)
if frontend_url.scheme not in ({'http','https'} if DEBUG else {'https'}) or not frontend_url.netloc or frontend_url.path not in ('','/') or frontend_url.query or frontend_url.fragment:
 raise RuntimeError('FRONTEND_BASE_URL must be an origin-only URL and use HTTPS outside DEBUG')
INVITATION_TOKEN_TTL_SECONDS=max(300,min(int(os.getenv('INVITATION_TOKEN_TTL_SECONDS','604800')),2592000))
PASSWORD_RESET_TOKEN_TTL_SECONDS=max(300,min(int(os.getenv('PASSWORD_RESET_TOKEN_TTL_SECONDS','3600')),86400))
CREDENTIAL_ENCRYPTION_KEYS=os.getenv('CREDENTIAL_ENCRYPTION_KEYS','').strip()

INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','platform_core']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','platform_core.middleware.RequestSecurityHeadersMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','platform_core.middleware.ImpersonationMiddleware','django.contrib.messages.middleware.MessageMiddleware','platform_core.middleware.TenantMiddleware','platform_core.security_policy.SecurityPolicyMiddleware','platform_core.read_cache.ApiReadCacheMiddleware','platform_core.idempotency.IdempotencyMiddleware','platform_core.cache_control.ApiCacheControlMiddleware']
ROOT_URLCONF='lodgeflow.urls';WSGI_APPLICATION='lodgeflow.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('POSTGRES_DB','lodgeflow'),'USER':os.getenv('POSTGRES_USER','lodgeflow'),'PASSWORD':os.getenv('POSTGRES_PASSWORD',''),'HOST':os.getenv('POSTGRES_HOST','db'),'PORT':os.getenv('POSTGRES_PORT','5432')}}
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
STATIC_URL='/static/';STATIC_ROOT=BASE_DIR/'staticfiles';DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
AUTH_PASSWORD_VALIDATORS=[
 {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
CSRF_COOKIE_SECURE=not DEBUG;SESSION_COOKIE_SECURE=not DEBUG;SESSION_COOKIE_HTTPONLY=True;CSRF_COOKIE_SAMESITE='Lax';SESSION_COOKIE_SAMESITE='Lax';SECURE_CONTENT_TYPE_NOSNIFF=True;SECURE_REFERRER_POLICY='strict-origin-when-cross-origin'

REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0')
CACHES={'default':{'BACKEND':'django_redis.cache.RedisCache','LOCATION':REDIS_URL,'OPTIONS':{'CLIENT_CLASS':'django_redis.client.DefaultClient'}}}
CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL',REDIS_URL)
CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND',REDIS_URL.replace('/0','/1'))
CELERY_TASK_ACKS_LATE=True
CELERY_TASK_REJECT_ON_WORKER_LOST=True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True
CELERY_BEAT_SCHEDULE={
 'operational-health-watch':{'task':'platform_core.tasks.monitor_operational_health','schedule':300.0},
 'recurring-meeting-generation':{'task':'platform_core.tasks.generate_recurring_meetings','schedule':3600.0},
 'report-schedule-dispatch':{'task':'platform_core.tasks.dispatch_due_report_schedules','schedule':60.0},
 'retention-policy-enforcement':{'task':'platform_core.tasks.enforce_retention_policies','schedule':86400.0},
 'campaign-schedule-dispatch':{'task':'platform_core.tasks.dispatch_due_campaigns','schedule':60.0},
}

MEDIA_ROOT=BASE_DIR/'media';MEDIA_URL='/media/'
AWS_STORAGE_BUCKET_NAME=os.getenv('AWS_STORAGE_BUCKET_NAME','').strip()
if AWS_STORAGE_BUCKET_NAME:
 STORAGES={'default':{'BACKEND':'storages.backends.s3.S3Storage','OPTIONS':{'bucket_name':AWS_STORAGE_BUCKET_NAME,'region_name':os.getenv('AWS_S3_REGION_NAME') or None,'endpoint_url':os.getenv('AWS_S3_ENDPOINT_URL') or None,'querystring_auth':True,'default_acl':'private','file_overwrite':False}},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}
SECURE_SSL_REDIRECT=os.getenv('SECURE_SSL_REDIRECT','true').lower()=='true' and not DEBUG
SECURE_HSTS_SECONDS=int(os.getenv('SECURE_HSTS_SECONDS','31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG
SECURE_HSTS_PRELOAD=not DEBUG
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https') if os.getenv('TRUST_PROXY_HEADERS','true').lower()=='true' else None

TRUST_PROXY_HEADERS=os.getenv('TRUST_PROXY_HEADERS','true').lower()=='true'
TRUSTED_PROXY_CIDRS=[x.strip() for x in os.getenv('TRUSTED_PROXY_CIDRS','').split(',') if x.strip()]
if TRUST_PROXY_HEADERS and not DEBUG and not TRUSTED_PROXY_CIDRS:
 raise RuntimeError('TRUSTED_PROXY_CIDRS is required when TRUST_PROXY_HEADERS=true')

EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST=os.getenv('EMAIL_HOST','')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS=os.getenv('EMAIL_USE_TLS','true').lower()=='true'
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','LodgeFlow <noreply@localhost>')
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.getenv('CSRF_TRUSTED_ORIGINS','').split(',') if x.strip()]
SESSION_COOKIE_AGE=60*60*24
SESSION_SAVE_EVERY_REQUEST=True

# Explicit browser/integration security policy. CORS is deny-by-default.
CORS_ALLOWED_ORIGINS=[x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','').split(',') if x.strip()]
CONTENT_SECURITY_POLICY=os.getenv('CONTENT_SECURITY_POLICY',"default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https: https://www.google-analytics.com https://analytics.google.com https://www.facebook.com; style-src 'self' 'unsafe-inline'; script-src 'self' https://www.googletagmanager.com https://connect.facebook.net; form-action 'self'")

# Structured operational logging. Request ids are supplied as response headers and
# included by application audit records; secret-bearing request bodies are never logged.
LOGGING={
 'version':1,'disable_existing_loggers':False,
 'formatters':{'json':{'()':'platform_core.logging.JsonFormatter'}},
 'handlers':{'console':{'class':'logging.StreamHandler','formatter':'json'}},
 'root':{'handlers':['console'],'level':os.getenv('LOG_LEVEL','INFO')},
}


# Optional production error tracking. PII is disabled by default; configure the DSN only
# in staging/production secret stores, never in the repository.
SENTRY_DSN=os.getenv('SENTRY_DSN','').strip()
if SENTRY_DSN:
 import sentry_sdk
 sentry_sdk.init(
  dsn=SENTRY_DSN,
  environment=os.getenv('SENTRY_ENVIRONMENT','production' if not DEBUG else 'development'),
  release=os.getenv('SENTRY_RELEASE') or None,
  send_default_pii=False,
  traces_sample_rate=max(0.0,min(float(os.getenv('SENTRY_TRACES_SAMPLE_RATE','0.05')),1.0)),
  profiles_sample_rate=0.0,
 )

MEETING_PACK_ATTACHMENT_MAX_BYTES=int(os.getenv('MEETING_PACK_ATTACHMENT_MAX_BYTES',str(15*1024*1024)))
MEETING_PACK_MAX_TOTAL_BYTES=int(os.getenv('MEETING_PACK_MAX_TOTAL_BYTES',str(40*1024*1024)))
MEETING_PACK_MAX_PAGES=int(os.getenv('MEETING_PACK_MAX_PAGES','250'))
