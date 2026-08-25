# LodgeFlow Data Model and Tenant Boundaries

## Purpose

LodgeFlow is a multi-tenant lodge-management SaaS. PostgreSQL is the production system of record. Tenant isolation is enforced in server-side query paths by resolving the authenticated user's active `TenantMembership` and then scoping tenant-owned objects by `tenant_id`; a client-supplied lodge identifier is never sufficient authorization.

## Tenant and identity core

`Tenant` is the root business partition. `TenantMembership` links an authenticated user to one tenant and carries a predefined or `CustomRoleDefinition` role. `LodgeProfile` stores lodge presentation/operating defaults. `FeatureFlag`, `EncryptedCredential`, subscription/billing records and tenant security settings are either tenant-scoped or deliberately global platform records with separate platform permissions.

## Membership, officers and candidates

`Member` is the canonical lodge-person record. `OfficerTerm` and `OfficerRoleDefinition` hold time-bounded offices. Candidate workflow state is stored in `Candidate`, with `CandidateTask`, mentor assignments and stage history preserving progression evidence. Tenant-configured stage definitions cannot remove stages still referenced by current/history records.

## Meetings and documents

`Meeting` owns agenda, communications/notices, schedule and lifecycle fields. Normalized `AgendaItem`, `Attendance`, `Visitor` and immutable/versioned `MinuteVersion` records preserve operational history. `MeetingAttachment` links a tenant-authorized PDF `Document` to a meeting pack with display label/order and an explicit `include_in_pack` switch. The meeting-pack generator re-checks document ACL, storage/scanner state, size/page limits and PDF integrity at generation time.

`Document` stores private file metadata, access rules, scan state and template content. Files are served through authorized download endpoints rather than public object URLs. Deletion removes the backing storage object before deleting metadata. `GeneratedDocument` records generated PDF identity, source, template version and SHA-256.

## Finance

`DuesCycle` defines periods/currency/policy. `DuesAssessment` stores member liability. `Payment` is immutable financial evidence except controlled reversal metadata; provider references are tenant/provider unique when present. `PaymentAllocation` maps payments to assessments. `FinancialAdjustment`, `ExpenseCategory` and `Expense` preserve approval/reversal rationale. Provider-facing `PaymentRequest` separates internal idempotency references from external provider references.

## Communications and reporting

`CommunicationCampaign` and `DeliveryLog` preserve server-calculated recipient and delivery outcomes. Delivery logs are unique per tenant/campaign/recipient to prevent duplicate sends during retries. `SavedReport`, `GeneratedReport`, `ReportSchedule` and `ReportDeliveryLog` separate report definition, generated evidence and scheduled delivery state.

## Audit/compliance

`AuditEvent` is append-only and hash-chained. `ExportApprovalRequest`/`ExportEvent`, `WebhookEvent`, `SystemJob`, `SecurityAlert` and related platform logs preserve approval and operational evidence. Cross-tenant object lookups return 403/404 according to the endpoint contract without revealing unauthorized object existence.

## Migration discipline

Committed migrations are the authoritative schema transition. Release CI must run migration drift checks, fresh-database migration tests and upgrade-path tests against PostgreSQL. Production migration is a controlled one-shot release step before web/worker health is considered ready.
