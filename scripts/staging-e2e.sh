#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.staging}"; export ENV_FILE
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.prod.yml:docker-compose.staging.yml}"; export COMPOSE_FILES
[[ -f "$ENV_FILE" ]] || { echo "Create $ENV_FILE from .env.staging.example with staging-only credentials." >&2; exit 2; }

./scripts/deploy-production.sh
C=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml -f docker-compose.staging.yml)

"${C[@]}" exec -T backend python manage.py test platform_core --verbosity 1
"${C[@]}" exec -T backend python - <<'PYCHECKS'
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
import uuid

token='lf-'+str(uuid.uuid4())
cache.set('staging-probe',token,30); assert cache.get('staging-probe')==token
print('Redis cache probe: ok')

name=f'_staging_probe/{token}.txt'
path=default_storage.save(name,ContentFile(b'lodgeflow-storage-probe'))
assert default_storage.open(path,'rb').read()==b'lodgeflow-storage-probe'
default_storage.delete(path)
print('S3-compatible storage probe: ok')

sent=send_mail('LodgeFlow staging SMTP probe','SMTP integration is operational.',None,['qa@example.test'],fail_silently=False)
assert sent==1
print('SMTP probe: ok')
PYCHECKS

"${C[@]}" exec -T backend python - <<'PYCLAM'
from django.core.files.uploadedfile import SimpleUploadedFile
from platform_core.services.file_security import validate_upload
f=SimpleUploadedFile('probe.txt',b'lodgeflow clean staging probe',content_type='text/plain')
validate_upload(f)
print('ClamAV upload probe: ok')
PYCLAM

"${C[@]}" exec -T worker celery -A lodgeflow inspect ping --timeout=10 | grep -qi pong
echo "Celery worker probe: ok"

# Mailpit's HTTP API confirms that Django reached the SMTP service.
curl -fsS "http://127.0.0.1:${MAILPIT_UI_PORT:-8025}/api/v1/messages" | grep -q 'LodgeFlow staging SMTP probe'
echo "Mailpit delivery probe: ok"

echo "Core staging integrations passed. Run the configured Stripe/PayMongo/Xendit sandbox callback suite before production promotion."
