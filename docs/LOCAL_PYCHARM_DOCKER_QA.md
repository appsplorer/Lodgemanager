# LodgeFlow — Local PyCharm + Docker QA Guide

This guide is for a Windows workstation running Docker Desktop and PyCharm. The application itself runs inside Docker, so a local Python or Node installation is optional for normal QA.

## 1. Prerequisites

Install and start:

- Docker Desktop with Linux containers and Docker Compose v2.
- PyCharm (Professional is ideal for Docker integration, but Community can still edit the project while Docker commands run in the built-in terminal).
- Git is recommended for local version control.
- Chrome or Edge for PWA/offline QA.

Verify in PowerShell:

```powershell
docker --version
docker compose version
git --version
```

Docker Desktop should report that its engine is running before continuing.

## 2. Extract and open the project

Extract the LodgeFlow ZIP to a short path, for example:

```text
C:\Projects\LodgeFlow
```

In PyCharm choose **File → Open** and select that folder.

Do not open only the `backend` or `frontend` subfolder; open the repository root so the Docker Compose, scripts, backend and frontend are all visible together.

## 3. Create the local environment file

From the PyCharm terminal at the repository root:

```powershell
Copy-Item .env.local.example .env.local
```

The checked-in `.env.local.example` contains deliberately local-only passwords and secrets. They are suitable for a private workstation QA environment only. Never reuse them on staging or production.

## 4. Start LodgeFlow locally

Recommended Windows command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-up.ps1
```

Equivalent raw Docker command:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml up --build -d
```

The first run downloads images and installs frontend packages, so it takes longer than later starts.

Check container state:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml ps
```

Useful logs:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml logs -f backend
docker compose --env-file .env.local -f docker-compose.local.yml logs -f frontend
docker compose --env-file .env.local -f docker-compose.local.yml logs -f worker
docker compose --env-file .env.local -f docker-compose.local.yml logs -f beat
```

## 5. Local URLs

- Public landing page: http://localhost:3000
- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard
- Platform admin: http://localhost:3000/platform-admin
- Django health endpoint: http://localhost:8000/api/health/
- Django admin: http://localhost:8000/admin/
- Mailpit email inbox: http://localhost:8025
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- ClamAV INSTREAM: localhost:3310

## 6. Local demo login

The `seed` Docker service runs `python manage.py seed_local_demo` after migrations.

Default local credentials:

```text
Email:    admin@lodgeflow.local
Username: admin
Password: LodgeFlowLocal123!
```

This account is a local-only superuser, Lodge owner and platform super-admin so you can QA every part of the application.

The seed command also creates synthetic members, officers, a candidate, a meeting, annual PHP dues, a CMS homepage, navigation and a sample lead form. Running it again is idempotent for its fixed demo records.

## 7. PyCharm setup

### A. Use Docker for application execution

For the simplest and most reproducible setup, do not run Django or Next directly from the Windows Python interpreter. Keep the services in Docker and use PyCharm for editing, terminal access, Git and debugging support.

### B. Docker connection in PyCharm Professional

Open:

**File → Settings → Build, Execution, Deployment → Docker**

Add Docker Desktop. On current Windows Docker Desktop installations, PyCharm normally detects the Docker engine automatically.

Then open:

**Run → Edit Configurations → + → Docker Compose**

Use:

```text
Compose files: docker-compose.local.yml
Environment variables file: .env.local
Services: backend, frontend, worker, beat, db, redis, mailpit, clamav
```

You can still use the supplied PowerShell scripts even if you configure this UI integration.

### C. Optional Python interpreter for code intelligence

If PyCharm Professional offers a Docker Compose interpreter, select the `backend` service and `/usr/local/bin/python`.

If not, create a normal local virtualenv only for IDE inspections. Docker remains the source of truth for runtime QA.

### D. Frontend editing

The local frontend service bind-mounts `./frontend` and runs Next development mode. Saving TS/TSX/CSS files in PyCharm should therefore trigger Next hot reload automatically.

The backend service similarly bind-mounts `./backend` and Django `runserver` reloads Python changes.

## 8. Run the automated local QA gate

After the stack is healthy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-qa.ps1
```

This validates:

1. Docker Compose configuration.
2. Django system checks.
3. Django migration drift (`makemigrations --check --dry-run`).
4. Django/PostgreSQL integration tests.
5. TypeScript/TSX syntax.
6. TypeScript typechecking.
7. A real Next.js production build.

No deployment should proceed if any of these commands fail.

You can also run individual checks:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py check
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py test platform_core --verbosity 2
docker compose --env-file .env.local -f docker-compose.local.yml run --rm frontend sh -lc "npm install && npm run check:syntax && npm run typecheck && npm run build"
```

## 9. Manual functional QA checklist

Use at least two browsers or one normal and one Incognito window where appropriate.

### Public website and CMS

- Open the public landing page and verify reveal/parallax animation is smooth.
- Verify keyboard focus states and reduced-motion behaviour.
- Open Platform Admin → CMS and edit/publish the homepage.
- Verify the landing page reflects the published content after revalidation.
- Test navigation, lead form, SEO fields, redirects and announcements.

### Authentication and tenant access

- Sign in with the local demo user.
- Test logout/login.
- Test Lodge switcher if you create a second tenant.
- Test MFA enrollment with an authenticator app.
- Verify tenant data is not visible from another tenant.

### Members / officers / candidates

- Create/edit/delete normal test records.
- Test duplicate review and merge controls.
- Test import/export using synthetic data only.
- Test candidate stages, mentor and tasks.
- Test officer succession.

### Meetings and minutes

- Create a meeting.
- Record attendance and visitors.
- Create minutes and exercise draft → review → approved → locked.
- Verify locked minutes cannot be casually modified.
- Generate meeting/attendance PDF outputs.

### Dues and finance

- Create a dues cycle in PHP.
- Generate assessments.
- Record a manual payment while online.
- Verify receipt numbering and balances.
- Test a foreign-currency expense and confirm original/base-currency snapshots are preserved.
- Keep payment-provider sandbox tests for staging unless you have local sandbox credentials configured.

### Documents and communications

- Upload PDF/JPEG/PNG/OpenXML test files.
- Verify disallowed signatures/types are rejected.
- Test document templates and ACL behaviour.
- Send a test email; inspect it in Mailpit at http://localhost:8025.

### Reports

- Check dashboard metrics.
- Run reporting/insight views.
- Export CSV/XLSX/PDF.
- Verify tenant and permission constraints.

## 10. Offline/PWA QA

Offline functionality must be tested after at least one successful online session because the browser first needs cached application/data state.

Recommended procedure in Chrome/Edge:

1. Sign in and browse Dashboard, Members, Candidates, Meetings and Reports while online.
2. Open DevTools → **Application → Service Workers** and confirm `/sw.js` is registered.
3. Open DevTools → **Application → IndexedDB** and confirm the LodgeFlow database exists. Private cached payloads should not be readable as clear application JSON.
4. Open DevTools → **Network** and select **Offline**, or disconnect Wi-Fi.
5. Revisit previously loaded screens.
6. Make an ordinary queueable CRUD edit such as editing a normal member note.
7. Confirm the offline status UI reports a queued operation.
8. Confirm payment, MFA, credentials, approvals, file upload and other high-risk actions explicitly refuse offline execution.
9. Restore the network.
10. Click **Sync now** if needed and confirm the queue drains.
11. Confirm the server reflects the edit.

### Conflict QA

To verify optimistic conflict protection:

1. Load the same record in Browser A and Browser B.
2. Take Browser A offline.
3. Change/save the record in Browser A so the mutation queues.
4. While Browser A is offline, modify the same record in Browser B and save it online.
5. Reconnect Browser A.
6. The queued stale write should be classified as a conflict instead of silently overwriting Browser B's newer server state.

## 11. Performance QA

In Chrome/Edge DevTools:

- Network: inspect transferred bytes and repeat navigation.
- Lighthouse: run Performance, Accessibility and Best Practices against the landing page and representative authenticated pages.
- Performance panel: record landing-page load and hover/scroll interactions.
- Application → Cache Storage: only public/static app-shell assets should be present; authenticated private API payloads should not be stored there.
- Application → IndexedDB: confirm offline data TTL/queue behaviour.

Also test:

- 1366×768 desktop.
- 1920×1080 desktop.
- iPad/tablet emulation.
- iPhone/Android emulation.
- Keyboard-only navigation.
- `prefers-reduced-motion: reduce` emulation.
- Slow 3G/4G throttling.

## 12. Database inspection

Open a PostgreSQL shell inside Docker:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml exec db psql -U lodgeflow -d lodgeflow
```

Examples:

```sql
\dt
SELECT id, name, slug FROM platform_core_tenant;
SELECT username, email, is_superuser FROM auth_user;
```

Exit with `\q`.

## 13. Django shell

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml exec backend python manage.py shell
```

## 14. Stop and restart

Stop containers while preserving local database volumes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-down.ps1
```

Start again:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-up.ps1
```

## 15. Completely reset local QA data

This deletes local PostgreSQL, Redis, media and related Docker volumes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-reset.ps1
```

The script requires the explicit word `RESET` before deletion.

## 16. Rebuild after dependency changes

If `backend/requirements.txt`, a Dockerfile or frontend dependencies change:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml build --no-cache
docker compose --env-file .env.local -f docker-compose.local.yml up -d
```

If only application source changes, normal hot reload is usually sufficient.

## 17. Before pushing to a server

Do not copy `.env.local` to a server.

Create `.env.production` from `.env.production.example` and replace every placeholder with production credentials. At minimum configure:

- Strong unique `DJANGO_SECRET_KEY`.
- Strong PostgreSQL and Redis passwords.
- Generated Fernet credential-encryption key(s).
- Real `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- HTTPS reverse proxy/TLS.
- S3-compatible private object storage credentials if used.
- Production SMTP.
- ClamAV with `CLAMAV_REQUIRED=true`.
- Stripe/PayMongo/Xendit credentials only through the platform credential workflow where applicable.
- Backup destination and tested restore process.
- Error monitoring/observability as required by your infrastructure.

Then use the production Compose/deployment documentation in `docs/PRODUCTION_DEPLOYMENT.md` and re-run the complete CI/staging gate.
