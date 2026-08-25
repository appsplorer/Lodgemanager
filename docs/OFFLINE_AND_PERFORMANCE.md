# Offline continuity and performance design

LodgeFlow uses a layered cache strategy. Next.js/public marketing content may be cached normally. The service worker caches only the application shell, immutable Next.js static assets and explicitly public API content. It never writes authenticated/private `/api/*` responses to CacheStorage.

Authenticated GET responses are stored as bounded, TTL-controlled AES-GCM encrypted snapshots in IndexedDB. The AES key is generated as a non-extractable WebCrypto key and persisted by the browser. Routine JSON mutations may be queued while offline. Each queued mutation receives a UUID idempotency key; the Django idempotency middleware stores a short-lived response receipt, so reconnect/retry does not duplicate a request after a lost response.

For integrity, offline mode deliberately blocks authentication/MFA changes, platform credential and user-security changes, billing/checkout/customer portal actions, provider payment links/webhooks, impersonation, export approvals, governed workflow transitions and file uploads. These operations require server state, anti-malware scanning, payment-provider confirmation or approval serialization.

When connectivity returns, queued requests replay in creation order. 5xx/429/network failures stop the batch and retry on a later online event. HTTP 409 is retained as a conflict for operator resolution. Successful mutations invalidate tenant snapshots so the next GET rehydrates from the server.

Production recommendations: configure CDN caching only for `/_next/static/*` and public marketing assets; never cache authenticated API responses at CDN/proxy; send `Cache-Control: private, no-store` for private API; monitor queue depth/conflict telemetry; purge private IndexedDB on logout/account switch; define device-management policy for shared computers; and run staging tests against real PostgreSQL/Redis/S3/ClamAV/SMTP/payment sandboxes before production cutover.
