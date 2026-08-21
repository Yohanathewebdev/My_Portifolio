# SOFTWARE DESIGN DOCUMENT

## Multi-Professional Portfolio CMS Platform

**Version 3.0 — Implementation-Ready**

Backend: Django 5.x + Django REST Framework · Public site: Django templates (server-rendered) · CMS: React 18 + Vite + Tailwind CSS · Database: PostgreSQL 16 · Queue: Celery + Redis · Storage: S3-compatible + CDN

---

## Document Control

| Field | Detail |
|---|---|
| Document Title | Multi-Professional Portfolio CMS Platform — Software Design Document |
| Version | 3.0 |
| Status | Approved for Implementation |
| Previous Versions | 1.0 — initial architecture and app breakdown · 2.0 — added NFRs, API standards, SEO, i18n/a11y, media, testing, observability, CI/CD, privacy |
| Change Summary (v2.0 → v3.0) | Every deferred decision resolved and recorded as an ADR. Added: Account-level tenancy with membership and roles; Plans/Subscriptions/Entitlements; server-rendered public site decision; enforced tenant-isolation mechanism; publishing model (revisions, scheduling, preview tokens, autosave); slug history and redirects; notification/email architecture; abuse and moderation; owner-facing analytics; custom domains; support back-office; concrete field-level models; endpoint contracts; requirement IDs; per-phase definitions of done. |
| Intended Audience | Implementing engineers, reviewers, QA, operations |
| Author | — |
| Reviewers | — |
| Approver / Sign-off | — |

### Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | — | — | Initial architecture and 12-app breakdown |
| 2.0 | Aug 2026 | — | Non-functional, operational and compliance detail |
| 3.0 | Aug 2026 | — | Implementation-ready: decisions resolved, schema and contracts specified |

### How to read this document

- **Requirement IDs.** Every requirement carries an ID (`FR-x.y`, `NFR-x.y`, `SEC-x`, `OPS-x`). §31 traces every ID to the phase that implements it and the test that proves it. A requirement without a passing test is not delivered.
- **Decisions.** Anything irreversible is recorded as an ADR in Appendix B, with the alternatives rejected and the consequences accepted. If implementation contradicts an ADR, the ADR is amended — not ignored.
- **`MUST` / `SHOULD` / `MAY`** are used in the RFC 2119 sense. `MUST` items are merge-blocking.

---

## Document Contents

1. Purpose and Scope
2. Design Goals and Principles
3. Non-Functional Requirements
4. System Architecture
5. Django Application Architecture
6. Tenancy: Accounts, Portfolios, Membership and Roles
7. Plans, Subscriptions and Entitlements
8. Professional and Multi-Professional Model
9. Profile and Content Architecture
10. Projects, Services and Testimonials
11. Blog Architecture
12. Publishing Model: Drafts, Revisions, Scheduling and Preview
13. CV Builder and PDF Architecture
14. Theme Architecture
15. Leads, Notifications and Email
16. Public Site Rendering, URLs, SEO and Caching
17. Custom Domains
18. CMS Architecture
19. Frontend Architecture
20. API Architecture and Standards
21. Internationalization and Accessibility
22. Media, Storage and CDN Strategy
23. Owner-Facing Analytics
24. Security and Authorization
25. Abuse, Moderation and Platform Trust
26. Database Design Standards
27. Testing Strategy
28. Observability, Support and Operations
29. Deployment, Environments and CI/CD
30. Data Privacy and Compliance
31. Traceability Matrix
32. Implementation Plan and Definitions of Done
33. Risks, Assumptions, Dependencies and Out of Scope
34. Glossary
- Appendix A — Entity Relationship Specification
- Appendix B — Architecture Decision Records
- Appendix C — Sequence Diagrams
- Appendix D — Reserved Slugs and Entitlement Catalogue

---

## 1. Purpose and Scope

This document is the implementation specification for the Multi-Professional Portfolio CMS Platform: a multi-tenant SaaS product in which any professional — developer, teacher, photographer, accountant, consultant, engineer — manages a portfolio through a private CMS and publishes it as a public website with its own URL, generates CVs from that same content, captures client leads, and pays a subscription for higher tiers.

**In scope for v1.0 of the product** (the software this document specifies): accounts and tenancy, portfolios, professions, profiles, structured career records, flexible content sections, projects, services, testimonials, blog, CV builder with PDF export, themes, public server-rendered sites with SEO, leads with notifications, owner-facing analytics, plans/subscriptions/entitlements, custom domains, moderation and support tooling, and the operational baseline (testing, observability, CI/CD, privacy).

**Out of scope for v1.0** — see §33.4 for the full list with rationale: third-party/user-authored themes, a public directory/marketplace, AI content generation, a third-party developer API with OAuth apps, native mobile apps, and machine translation of user content. Each is designed *around* (the schema and interfaces do not block them) but not built.

**Relationship to v2.0.** v2.0 established the architecture and was correct in its structure; this revision changes only what was undecided, contradictory, or too coarse to build from. The 12-app separation, the Portfolio-as-ownership-boundary principle, theme/content independence, and CV-from-single-source-of-truth are all preserved.

---

## 2. Design Goals and Principles

- **P-1 CMS-first.** Users manage everything without touching source code.
- **P-2 API-first for the CMS.** The React CMS talks to Django only through versioned REST APIs; there is no private back channel.
- **P-3 Single source of truth.** Portfolio data powers the public site, the CV engine, analytics and future integrations. Data is duplicated only when *intentionally snapshotted* (§13.4), never for convenience.
- **P-4 Isolation by mechanism, not by discipline.** Tenant scoping is enforced by base classes and automated tests that fail closed, not by reviewers remembering (§24.2).
- **P-5 Profession-neutral.** No profession is privileged in the schema. Adding a profession is a data change.
- **P-6 Extensible without migration.** New professions, sections, themes, plans and entitlements are data/config, not schema.
- **P-7 Separation of concerns.** One responsibility per app; no app imports another app's internals (§5.3).
- **P-8 Server-side authority.** The backend is the only authorization layer; the frontend restricts for UX only.
- **P-9 Theme independence.** Themes reference content; they never store or mutate it. Switching themes is lossless and reversible.
- **P-10 Commercially load-bearing from day one.** Tenancy, entitlements and usage accounting exist in the schema from phase 1, so pricing changes are configuration (§7).
- **P-11 Observable by default.** Every request and background job is traceable end to end by correlation ID.
- **P-12 Global from the data layer up.** UTC storage, ISO currency codes, externalized strings, locale at render time.
- **P-13 Decisions are written down.** Irreversible choices live in ADRs (Appendix B), not in tribal memory.

---

## 3. Non-Functional Requirements

Targets are **p95 unless stated**, measured in production against the staging-validated load profile (§27.6). Averages are not accepted as evidence.

### 3.1 Performance

| ID | Requirement |
|---|---|
| NFR-1.1 | Public portfolio page, cache hit: TTFB < 100 ms p95 at the CDN edge. |
| NFR-1.2 | Public portfolio page, cache miss (origin render): TTFB < 400 ms p95, < 800 ms p99. |
| NFR-1.3 | CMS API read endpoints: < 300 ms p95. CMS API write endpoints: < 500 ms p95. |
| NFR-1.4 | Core Web Vitals on the default theme, field data: LCP < 2.5 s, CLS < 0.1, INP < 200 ms, at the 75th percentile. Lighthouse ≥ 90 in CI on a lab profile is the pre-merge proxy gate. |
| NFR-1.5 | CV PDF generation: < 5 s p95 for a 1–2 page CV, executed asynchronously; the user is never blocked on an HTTP request. |
| NFR-1.6 | Every list endpoint is paginated with a hard `page_size` cap (§20.3). No endpoint may issue an unbounded query. |
| NFR-1.7 | Public portfolio render executes ≤ 15 database queries on a cache miss, asserted by an automated query-count test. |

### 3.2 Availability and Reliability

| ID | Requirement |
|---|---|
| NFR-2.1 | SLO: 99.9% monthly availability for public portfolio pages (they are cacheable and must survive origin degradation). |
| NFR-2.2 | SLO: 99.5% monthly availability for the CMS API and dashboard. |
| NFR-2.3 | Error budget: releases are frozen for the remainder of the month when 100% of the budget is consumed; a burn rate above 2× triggers an alert. |
| NFR-2.4 | Graceful degradation: failure of the CV engine, analytics pipeline, email provider or payment provider MUST NOT take down the CMS or public pages. Each is behind a timeout and a circuit breaker, and degrades to a queued retry plus a user-visible status. |
| NFR-2.5 | Public pages MUST serve stale-while-revalidate from the CDN when the origin is unavailable (a published portfolio stays online through an origin outage). |
| NFR-2.6 | Every background job is idempotent and retryable with exponential backoff, has a max-retry policy, and lands in a dead-letter queue with an alert on exhaustion. |
| NFR-2.7 | Published SLA to customers is deliberately set *below* the SLO (99.5% public / no CMS SLA at launch). SLO is the engineering target; SLA is the contractual promise. |

### 3.3 Scalability

| ID | Requirement |
|---|---|
| NFR-3.1 | 10,000 active portfolios and 1,000 concurrent public visitors on initial production infrastructure, **validated by a load test** (§27.6) before production launch — not asserted. |
| NFR-3.2 | Application servers are stateless (no local session or file state); horizontal scaling requires no code change. |
| NFR-3.3 | Public reads MUST be routable to a read replica without application changes; public querysets are read-only by construction. |
| NFR-3.4 | Tenant fairness: per-account rate limits on API calls and per-account concurrency limits on background jobs. CV rendering, email and analytics use **separate Celery queues** so no tenant's bulk activity delays another tenant's lead notification. |
| NFR-3.5 | Unit cost per active portfolio per month (storage, bandwidth, renders, email) is measured monthly and reported; entitlement limits in §7.4 are derived from it. |

### 3.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-4.1 | Each Django app has its own test suite and passes in isolation. |
| NFR-4.2 | No app imports another app's non-public modules; cross-app access is via documented service functions or model managers (§5.3), enforced by an import-linter rule in CI. |
| NFR-4.3 | Lint and format gates in CI: `ruff` + `ruff format` (Python), ESLint + Prettier (TypeScript). |
| NFR-4.4 | Python is fully type-annotated at app boundaries and checked with `mypy` in CI; the CMS is TypeScript in `strict` mode. |
| NFR-4.5 | The OpenAPI schema is generated in CI (`drf-spectacular`) and a breaking-change diff against the previous release fails the build unless the version is bumped. |

---

## 4. System Architecture

```
                        ┌───────────────────────────────┐
                        │   CDN  (public HTML + media)  │
                        │  cache keys per portfolio,    │
                        │  stale-while-revalidate       │
                        └───────────┬───────────────────┘
                                    │ cache miss / purge
┌───────────────────────────┐       │       ┌──────────────────────────────┐
│  CMS  (React SPA)         │       │       │  Public visitor / crawler    │
│  app.<domain>             │       │       │  <slug>.<domain> or custom   │
└─────────────┬─────────────┘       │       └──────────────┬───────────────┘
              │ HTTPS / JWT         │                      │ HTTPS
              ▼                     ▼                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        DJANGO APPLICATION (stateless)                  │
│  ┌───────────────────────────┐    ┌──────────────────────────────────┐ │
│  │ CMS API  (DRF)            │    │ PUBLIC RENDERER                  │ │
│  │ /api/v1/*  private        │    │ Django templates + theme packs   │ │
│  │ versioned, throttled,     │    │ server-rendered HTML, no auth,   │ │
│  │ CORS-scoped, JWT          │    │ read-only, replica-safe          │ │
│  └───────────┬───────────────┘    └───────────────┬──────────────────┘ │
│              └──────────────┬─────────────────────┘                    │
│                             ▼                                          │
│  DOMAIN LAYER   core · accounts · billing · portfolios · professionals │
│  profiles · career · content · projects · services · testimonials      │
│  blog · cv · leads · themes · media · analytics · moderation           │
└──────────────┬──────────────────────────────┬──────────────────────────┘
               │                              │ enqueue
               ▼                              ▼
┌───────────────────────────┐   ┌──────────────────────────────────────┐
│ PostgreSQL 16             │   │ Celery workers (separate queues)     │
│ primary + read replica    │   │ pdf · email · analytics · media ·    │
└───────────────────────────┘   │ billing · maintenance                │
┌───────────────────────────┐   └──────────────┬───────────────────────┘
│ Redis: cache, broker,     │◄─────────────────┘
│ rate limits, locks        │   ┌──────────────────────────────────────┐
└───────────────────────────┘   │ S3-compatible object storage (media, │
                                │ generated PDFs, backups)             │
                                └──────────────────────────────────────┘
   External: payment provider · transactional email · error tracking ·
             log aggregation · ACME/TLS · malware scanning
```

**Two presentation paths over one domain model.** The CMS writes validated data through DRF. The public renderer reads only published data through Django templates and returns cacheable HTML. This resolves the central contradiction in v2.0 — see **ADR-003**.

**Why the public path is not a React SPA.** Discoverability *is* the product's value (§16). A client-rendered SPA cannot meet NFR-1.1/1.2/1.4 without adding a Node SSR tier, a second deployable and a second failure mode. Server-rendered HTML from the same Django process that owns the data is the shortest path to fast, indexable pages, and makes CDN caching trivial. The cost — themes are authored as Django templates rather than React components — is accepted, and is mitigated by the CMS previewing themes through an iframe pointed at the *real* renderer (§14.5), which is more faithful than a React re-implementation would have been.

---

## 5. Django Application Architecture

### 5.1 Applications

| App | Primary responsibility | New in v3.0 |
|---|---|---|
| `core` | Base model mixins (UUID pk, timestamps, soft delete), tenant-scoped managers/querysets/viewsets, exceptions, pagination, permissions, correlation IDs | ✔ |
| `accounts` | Users, authentication, email verification, Account, AccountMembership, roles | |
| `billing` | Plan, Subscription, entitlements service, usage counters, provider adapters, webhooks | ✔ |
| `portfolios` | Portfolio ownership, slug + slug history, publication state, settings | |
| `professionals` | Profession catalogue, categories, per-profession suggestion config | |
| `profiles` | Profile identity, contact, social links, avatar | |
| `career` | Experience, Education, Skill, Certification, Achievement — typed career records | ✔ |
| `content` | Flexible/custom sections and blocks | |
| `projects` | Projects, work samples, case studies | |
| `services` | Services, pricing, offers | |
| `testimonials` | Testimonials and social proof | |
| `blog` | Posts, categories, tags, publishing | |
| `cv` | CV versions, templates, snapshots, render pipeline, share links | |
| `leads` | Lead capture, spam defence, inbox, statuses | |
| `themes` | Theme catalogue, theme packs, portfolio appearance settings | |
| `media` | MediaAsset, uploads, validation, derivatives, per-tenant usage | ✔ |
| `analytics` | Event ingestion, rollups, owner-facing reporting | ✔ |
| `notifications` | Notification model, email templates, delivery, preferences | ✔ |
| `moderation` | Reports, review queue, suspension, audit of platform actions | ✔ |
| `publishing` | Revisions, scheduled publishing, preview tokens, cache invalidation | ✔ |
| `public` | Public renderer: URL resolution, view logic, template loading, caching | ✔ |

The original 12 apps are unchanged in name and responsibility. The nine additions each exist because v2.0 required behaviour that had no owning module (a media record with no model, "monetization" with no billing app, cache invalidation with no trigger).

### 5.2 `core` contract

Every domain model inherits from exactly one of:

```python
class BaseModel(models.Model):            # id: UUID pk, created_at, updated_at
class SoftDeleteModel(BaseModel):         # + is_deleted, deleted_at, all_objects manager
class PortfolioOwnedModel(SoftDeleteModel):
    portfolio = models.ForeignKey("portfolios.Portfolio", on_delete=models.CASCADE,
                                  related_name="%(class)s_set")
    objects = PortfolioScopedManager()    # see §24.2 — refuses an unscoped query
    class Meta:
        abstract = True
        indexes = [models.Index(fields=["portfolio", "-created_at"])]
```

`core` also owns: `CorrelationIdMiddleware`, `StandardPagination`, `ErrorEnvelopeExceptionHandler` (§20.4), `IsAccountMember`/`HasEntitlement` permissions, and `AuditLog` (§24.6).

### 5.3 Cross-app rule (NFR-4.2)

Each app exposes `services.py` (write operations, transactional, the only legal cross-app write entry point), `selectors.py` (read queries), and `models.py`. Any other module is private. `import-linter` contracts in CI enforce the layering: `core` ← domain apps ← (`api`, `public`) and forbid domain-app-to-domain-app imports outside `services`/`selectors`/`models`.

---

## 6. Tenancy: Accounts, Portfolios, Membership and Roles

**ADR-001** replaces v2.0's `User 1:1 Portfolio` with a two-level model. This is the change that must happen before phase 1 code, because retrofitting it means migrating live tenant data.

```
User ──M:M── Account (via AccountMembership: role)
                │ 1:M
                ▼
            Portfolio ──── all content models (FK portfolio)
```

- **`Account`** is the **billing and quota boundary**. It owns the Subscription, usage counters and members.
- **`Portfolio`** remains the **content and isolation boundary**. Every content model keeps its `FK → Portfolio` exactly as in v2.0; §8–§15 are unaffected.

**Why.** v2.0's own §2 promised team accounts and its §6 note suggested `PortfolioMembership`, while the ERD fixed 1:1 — an internal contradiction. It also blocked the platform's headline use case: a multi-professional user who wants *two separate public sites* (e.g. photographer and consultant) rather than two professions on one site. Launch behaviour is identical to v2.0: signup creates one User, one Account, one owner membership and one Portfolio.

### 6.1 Models

```python
Account:      id(UUID) name slug(unique) plan_ref status[active|suspended|closed]
              billing_email country_code created_at updated_at
AccountMembership: account user role[owner|admin|editor|viewer]
              invited_by invited_at accepted_at
              constraints: unique(account, user);
                           exactly one role=owner per account (partial unique index)
Portfolio:    id(UUID) account(FK) slug(unique, validated, reserved-checked)
              title publication_state[draft|published|unpublished|suspended]
              published_at unpublished_at active_theme(FK) primary_locale
              default_currency seo_title seo_description og_image(FK MediaAsset)
              is_indexable created_at updated_at
              constraints: unique(slug); index(publication_state, published_at)
PortfolioSlugHistory: portfolio old_slug(unique) changed_at  # §16.4 → 301s
```

### 6.2 Role matrix (FR-6.1)

| Action | owner | admin | editor | viewer | platform support | anonymous |
|---|---|---|---|---|---|---|
| Read published public content | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Read draft/unpublished content | ✔ | ✔ | ✔ | ✔ | via impersonation | preview token only |
| Create/edit content | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ |
| Publish / unpublish | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ |
| Manage theme and appearance | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ |
| Read leads | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ |
| Manage members and roles | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ |
| Manage billing / plan | ✔ | ✖ | ✖ | ✖ | ✖ | ✖ |
| Delete portfolio / close account | ✔ | ✖ | ✖ | ✖ | ✖ | ✖ |
| Suspend a portfolio (abuse) | ✖ | ✖ | ✖ | ✖ | ✔ (§25.3) | ✖ |
| Impersonate a user | ✖ | ✖ | ✖ | ✖ | ✔ audited (§28.4) | ✖ |

At launch only `owner` is assignable through the UI; the other roles exist in the schema and permission layer and are unlocked by the `team_members` entitlement (§7.4). **SEC-1:** the matrix above is implemented as a single declarative permission table in `core` and asserted cell-by-cell by an automated authorization-matrix test (§27.4) — every cell is a test case.

---

## 7. Plans, Subscriptions and Entitlements

v2.0 titled §13 "Leads and Monetization Flow" but specified only leads, and deferred billing to "a Portfolio-level plan/tier field". A tier field records *what was bought*; it cannot answer *what is allowed*, so limit checks scatter across every app and every pricing change becomes a codebase-wide edit. This section is the highest-value addition in v3.0.

### 7.1 Models

```python
Plan:  id code(unique) name description interval[month|year] price_amount
       price_currency(ISO 4217) is_public sort_order entitlements(JSONB) provider_price_id
Subscription: id account(1:1) plan(FK) status trial_end current_period_start
       current_period_end cancel_at canceled_at provider_customer_id
       provider_subscription_id provider[stripe|paddle|...] created_at updated_at
UsageCounter: account metric[storage_bytes|leads_month|cv_renders_month|ai_credits_month|portfolios]
       value period_start  constraints: unique(account, metric, period_start)
BillingEvent: id account provider provider_event_id(unique) type payload(JSONB)
       received_at processed_at status  # idempotency ledger, §7.6
```

`Plan.entitlements` is JSONB so a new limit or feature flag is a data change (P-6). The catalogue is in Appendix D.

### 7.2 Subscription state machine

```
                    ┌──────────────┐
  signup ─────────► │   trialing   │ ── trial ends, payment ok ──┐
                    └──────┬───────┘                             ▼
                           │ trial ends, no payment       ┌──────────────┐
                           ▼                              │    active    │
                    ┌──────────────┐  payment recovered   └──┬───────┬───┘
                    │   past_due   │◄────────────────────────┘       │ user cancels
                    └──────┬───────┘  payment fails                  ▼
        dunning exhausted  │                                 ┌──────────────┐
                           ▼                                 │ cancel_at set│
                    ┌──────────────┐  reactivate             │ (stays active│
                    │  suspended   │────────────────────────►│ until period │
                    └──────┬───────┘                         │ end)         │
                           │ 30 days                         └──────┬───────┘
                           ▼                                        ▼
                    ┌────────────────────────────────────────────────────┐
                    │                    canceled                        │
                    └────────────────────────────────────────────────────┘
```

**Effects on the product (FR-7.1) — stated explicitly, because ambiguity here becomes a support incident:**

| Status | Public portfolio | CMS | Data |
|---|---|---|---|
| `trialing`, `active` | live | full | retained |
| `past_due` | **stays live** | full, with a persistent banner | retained |
| `suspended` | stays live, downgraded to free-tier entitlements (custom domain and premium theme disabled, canonical reverts to platform URL) | read-only + export allowed | retained |
| `canceled` | reverts to free-tier entitlements; unpublished only if over free limits | read-only + export allowed | retained ≥ 90 days |
| Account `closed` | offline, 410 Gone | closed | deleted/anonymized per §30.3 |

A portfolio is **never** silently deleted for non-payment. Downgrade-over-limit resolution: the user chooses which items to keep; if they do not choose within 14 days, the newest items over the limit are hidden (never deleted) and flagged in the CMS.

### 7.3 Entitlements service (SEC-2, the load-bearing interface)

One module, `billing/entitlements.py`. **No app may read `plan.code` or `subscription.status` directly** — enforced by an import-linter rule and a CI grep gate.

```python
def features(account) -> frozenset[str]
def has(account, feature: str) -> bool
def limit(account, metric: str) -> int | None          # None = unlimited
def usage(account, metric: str) -> int
def check_and_consume(account, metric: str, amount: int = 1) -> None
    # raises EntitlementExceeded(metric, limit, usage) → HTTP 402 + upgrade CTA
```

Resolution order: `Plan.entitlements` → per-account override (`Account.entitlement_overrides`, for support grants and grandfathering) → hardcoded free-tier defaults. Results are cached in Redis for 60 s and invalidated on subscription change. `HasEntitlement("custom_domain")` is a DRF permission class; `check_and_consume` guards every quota-bearing write (upload, lead accept, CV render, portfolio create).

### 7.4 Entitlement catalogue

Defined in Appendix D. Limits are **derived from the measured unit cost in NFR-3.5**, not guessed — the first pricing review happens after phase 5 load testing produces real cost-per-portfolio numbers.

### 7.5 Provider abstraction (ADR-006)

```python
class PaymentProvider(Protocol):
    def create_customer(account) -> str
    def start_checkout(account, plan, success_url, cancel_url) -> str
    def open_billing_portal(account, return_url) -> str
    def cancel(subscription, at_period_end: bool) -> None
    def parse_webhook(request) -> BillingEvent
```

**DEP-1 (blocking business dependency, §33.3):** Stripe is unavailable to merchants in a number of countries; a merchant-of-record (Paddle, Lemon Squeezy) or a local gateway changes tax, invoicing and refund handling materially. The provider decision has a named owner and a resolution date **before phase 4**. The interface above means the decision does not block phases 1–3, but it must not be discovered in phase 5.

**Tax and invoicing position** must be recorded alongside the provider choice: who is merchant of record, whether VAT/sales tax is provider-handled, invoice numbering and receipt delivery. If a merchant-of-record provider is chosen, the platform holds no tax obligation directly — which is the main reason to prefer one at this stage.

### 7.6 Webhooks (OPS-1)

Webhook endpoint verifies the provider signature, writes a `BillingEvent` row keyed by `provider_event_id` (**unique — this is the idempotency guarantee**), returns 200 immediately, and processes asynchronously. Out-of-order events are resolved by comparing provider timestamps against `Subscription.updated_at`. A **nightly reconciliation job** compares local subscription state against the provider's and alerts on divergence — webhooks *are* missed, and reconciliation is the difference between a billing system and a billing incident.

---

## 8. Professional and Multi-Professional Model

Unchanged in intent from v2.0, with the configuration made concrete so P-6 holds.

```python
Profession: id name slug(unique) category description icon is_active sort_order
            suggestion_config(JSONB)
PortfolioProfession: portfolio profession is_primary display_order
            constraints: unique(portfolio, profession);
                         exactly one is_primary=True per portfolio
```

`suggestion_config` is data, not code — e.g.
```json
{"suggested_sections": ["gallery", "packages"],
 "suggested_cv_template": "creative-1",
 "cv_section_order": ["profile", "experience", "portfolio", "skills"],
 "recommended_theme": "lens"}
```
Adding a profession is therefore an admin data entry task with no migration and no deploy (FR-8.1). Suggestions never *restrict*: a user may always add any section or template regardless of profession (this is the concrete mitigation for the "generic-and-weak" risk in §33.1).

The primary profession drives default SEO metadata (§16.3), schema.org `jobTitle`, and CV template suggestions.

---

## 9. Profile and Content Architecture

**ADR-004** resolves v2.0's open question: career history is **typed first-class models** in the new `career` app, not free-form content sections. Reason: the CV engine needs sortable dates and structured fields, schema.org needs typed values, and any future CV/LinkedIn import needs a target schema. Free-form text cannot produce a good CV, and this was the deferred decision most likely to force a rewrite.

```python
Profile (1:1 Portfolio): full_name headline biography(rich text) avatar(FK MediaAsset)
    email phone city country timezone social_links(JSONB: [{platform,url}])
    available_for_work open_to_relocation

# career app — all PortfolioOwnedModel
Experience:     title organization employment_type location start_date end_date
                is_current description(rich) highlights(JSONB list) sort_order is_visible
Education:      institution degree field_of_study start_date end_date grade
                description sort_order is_visible
Skill:          name category proficiency[1..5] years_experience sort_order is_visible
Certification:  name issuer issue_date expiry_date credential_id credential_url
                sort_order is_visible
Achievement:    title issuer date description sort_order is_visible

# content app — everything genuinely bespoke
ContentSection: portfolio key(slug) title kind[core|professional|custom]
                layout_hint sort_order is_visible
                constraints: unique(portfolio, key)
ContentBlock:   section kind[text|rich_text|image|gallery|list|kv|embed|file]
                payload(JSONB, schema-validated per kind) sort_order
```

Rich text is stored as sanitized HTML (§24.4) plus the original editor JSON, so re-editing is lossless while rendering is safe. `ContentBlock.payload` is validated against a per-kind JSON Schema on write — JSONB without validation is how a data model rots.

**Where each kind of content belongs (FR-9.1):** career facts → `career`; presentation-only, profession-specific or user-invented sections (Teaching Philosophy, Photography Packages) → `content`. Both render on the public site and both can feed a CV; only `career` records get structured-data markup.

---

## 10. Projects, Services and Testimonials

All three are `PortfolioOwnedModel` with `PublishableMixin` (§12.1).

```python
Project:     title slug description(rich) summary client role start_date end_date
             cover_image(FK MediaAsset) gallery(M2M MediaAsset through ProjectImage)
             tags(M2M Tag) links(JSONB: [{label,url}]) is_featured
             publication_state published_at sort_order
             constraints: unique(portfolio, slug)
Service:     title slug description(rich) price_amount price_currency(ISO 4217)
             price_model[fixed|hourly|from|quote] duration deliverables(JSONB)
             is_featured cta_label publication_state sort_order
             constraints: unique(portfolio, slug)
Testimonial: client_name client_role client_company client_photo(FK MediaAsset)
             message rating[1..5] source_url given_at consent_reference
             is_featured publication_state sort_order
```

Notes that matter for implementation:
- **Currency is an ISO 4217 code, never a symbol** (NFR/P-12); amounts are `DecimalField(max_digits=12, decimal_places=2)`, never float.
- `Testimonial.consent_reference` records how the client's permission to publish their name/photo was obtained — the portfolio owner is the controller of that personal data (§30.5) and this field is the platform's evidence that the question was asked.
- Projects are profession-neutral: nothing in the model assumes software.

---

## 11. Blog Architecture

```python
BlogPost: portfolio title slug excerpt content(rich) featured_image(FK MediaAsset)
          category(FK) tags(M2M) publication_state published_at scheduled_for
          reading_time(computed on save) seo_title seo_description og_image
          canonical_url view_count
          constraints: unique(portfolio, slug); index(portfolio, publication_state, -published_at)
BlogCategory / Tag: portfolio-scoped, unique(portfolio, slug)
```

Public routes: `/blog/` and `/blog/<post-slug>/` under the portfolio's host (§16.1). Per-post OG/SEO fields and per-post canonical URLs are required, because on a multi-tenant platform every tenant's content quality feeds the whole domain's search reputation. Post slug changes create redirect history exactly as portfolio slugs do (§16.4). Comments are out of scope for v1.0 (§33.4) — they would drag in a full moderation surface per tenant.

---

## 12. Publishing Model: Drafts, Revisions, Scheduling and Preview

v2.0 had "draft/published states where appropriate" and no data-loss story. This section makes publishing a model rather than a boolean; it is the difference between a CRUD admin and a CMS people trust with their livelihood.

### 12.1 `PublishableMixin`

```python
publication_state[draft|published|unpublished|scheduled]
published_at   scheduled_for   last_published_revision(FK Revision)
```
State transitions run through `publishing.services.publish(obj, actor)` / `unpublish` / `schedule`, which are the only legal mutators. Each transition: validates entitlements, writes a `Revision`, writes an `AuditLog` entry, and **enqueues cache invalidation** (§16.5). Nothing else may set `publication_state` — this is what makes cache correctness a property of the system rather than of the developer.

### 12.2 Revisions (FR-12.1)

```python
Revision: id content_type object_id portfolio actor snapshot(JSONB)
          created_at label is_published_version
          index(content_type, object_id, -created_at)
```
A revision is written on every publish and on every manual save that changes content. Retention: last 20 revisions per object, or unlimited on higher plans (`revision_history` entitlement). Restore is a new revision, never a destructive rollback. *Rationale: "I overwrote my bio" is the highest-frequency support ticket in this product category.*

### 12.3 Scheduled publishing (FR-12.2)

`scheduled_for` (UTC) processed by a Celery beat task every minute, which takes a per-object advisory lock, publishes, and invalidates cache. Idempotent per NFR-2.6.

### 12.4 Preview tokens (FR-12.3)

```python
PreviewToken: id portfolio token(hashed, unique) created_by expires_at
              max_uses use_count scope[portfolio|object] object_ref revoked_at
```
`GET <host>/?preview=<token>` renders **unpublished** content through the real public renderer with `X-Robots-Tag: noindex, nofollow`, `Cache-Control: private, no-store`, and no CDN caching. Default expiry 7 days. This is what lets a user send a draft to a client for approval — high value, low cost, and it must be designed into the resolver (§16.2) rather than bolted on.

### 12.5 Autosave and dirty-state protection (FR-12.4)

The CMS autosaves drafts every 5 s of idle after a change via `PATCH .../draft`, keeps a local snapshot in IndexedDB for crash recovery, blocks navigation on unsaved changes, and uses optimistic concurrency: every editable resource carries a `version` integer; a mismatched `If-Match`/`version` returns **409** with both versions so the CMS can offer a merge/overwrite choice. v2.0 specified no data-loss story at all; losing a user's writing is the fastest way to lose their trust.

---

## 13. CV Builder and PDF Architecture

### 13.1 Data flow

```
career + profiles + projects + content   (single source of truth, §2 P-3)
        │
        ▼   user configures
CVVersion ── selected sections, order, target profession, template, locale, options
        │
        ▼   "Export" → immutable capture
CVSnapshot (JSONB, versioned template_id) ─────► Celery: render (WeasyPrint)
        │                                                │
        ▼                                                ▼
   Live preview (HTML, same template)            PDF in object storage
                                                         │
                                                         ▼
                                             download · share link (§13.6)
```

### 13.2 Models

```python
CVTemplate: id code(unique) name version preview_image engine[weasyprint]
            template_path supports_locales is_premium is_active
CVVersion:  portfolio name target_profession(FK) template(FK) locale
            section_config(JSONB: [{key, include, order, options}])
            options(JSONB: page_size, accent_color, photo, contact visibility)
            is_default created_at updated_at
CVSnapshot: cv_version content(JSONB, immutable) template_code template_version
            rendered_pdf(file ref) page_count render_status[pending|ok|failed]
            render_error checksum created_at
CVShareLink: cv_snapshot token(hashed, unique) expires_at view_count
            download_count last_viewed_at revoked_at
```

### 13.3 Preview vs export

Preview renders **live data** through the same template as the PDF (identical HTML/CSS path — a preview that can disagree with the PDF is worse than no preview). Export **freezes** a `CVSnapshot`.

### 13.4 Snapshot rule (ADR-005) — resolves the v2.0 §11-vs-§21 contradiction

v2.0 said "the CV does not duplicate the portfolio database" (§11) and also "avoid duplicated CMS data unless intentionally versioned/snapshotted" (§21). The resolution: **configuration reads live; every export snapshots.** A PDF a user emailed to an employer must remain reproducible byte-for-byte even after they rewrite their bio, and a template improvement must never reflow a CV already in someone's inbox — hence `template_version` is captured in the snapshot too. This is the one place P-3 is deliberately overridden, and it is overridden explicitly.

### 13.5 Render pipeline and output quality (FR-13.1)

- **WeasyPrint** (ADR-007) — pure Python, no browser process, deterministic, small footprint. Rejected: headless Chromium (heavy, higher operational cost, harder to sandbox), LaTeX (authoring cost).
- Asynchronous Celery task on the dedicated `pdf` queue, per-account concurrency cap (NFR-3.4), retries per NFR-2.6, timeout 30 s.
- **ATS-friendly output is a hard requirement**: real selectable text (never text-in-image), no layout tables, standard section headings, a single logical reading order, embedded subsettable fonts, PDF metadata (title, author), and tagged PDF where WeasyPrint supports it. *This is where CV products win or lose and v2.0 said nothing about it.*
- **Deterministic pagination**: templates define page-break rules (`break-inside: avoid` on records), and a golden-file test asserts page count and checksum for a fixture CV per template so template edits cannot silently reflow output.
- Anonymous/no-photo and "hide contact details" variants are options, not separate templates.

### 13.6 Sharing and export formats

- `CVShareLink`: a public read-only URL with view/download counts and expiry — the CV equivalent of §12.4, and a genuine differentiator.
- **DOCX export** via a template-driven writer for the two most-used templates (recruiters still ask for it). Scheduled phase 4; the snapshot JSON makes it a rendering concern only.

---

## 14. Theme Architecture

```python
Theme: id code(unique) name description preview_image template_pack_path
       supports_layouts(JSONB) color_presets(JSONB) typography_presets(JSONB)
       is_premium is_active version
PortfolioThemeSettings (1:1 Portfolio):
       theme(FK) layout color_preset custom_colors(JSONB, allowlisted keys)
       typography_preset section_order(JSONB) options(JSONB) logo(FK MediaAsset)
```

- **P-9 holds structurally:** themes contain *no* content fields and cannot write to content models. Switching themes changes only `PortfolioThemeSettings`; a theme switch is reversible and lossless, and an automated test asserts content equality across a switch cycle.
- A theme is a **Django template pack**: `themes/<code>/{base,portfolio,project_detail,blog_list,blog_detail,cv_share}.html` + a compiled Tailwind stylesheet. Missing templates fall back to the default pack, so a theme is never required to implement everything.
- **Custom colours are allowlisted CSS custom properties only** — no raw CSS or HTML injection from users. This closes the injection vector that "future premium themes" (v2.0 §12) would otherwise open (§24.4).
- **Preview before activation (FR-14.1)**: the CMS renders the *real* public renderer in an iframe with a preview token and a `?theme=<code>` override, so the preview cannot disagree with production.
- Premium themes are gated by the `premium_themes` entitlement (§7.3), which is why the theme model needs no plan awareness at all.
- **Theme QA is automated** (§27.5): visual-regression snapshots across breakpoints plus axe accessibility checks per theme. v2.0's manual checklist does not survive a growing catalogue and is the most likely source of silent regressions in this architecture.

---

## 15. Leads, Notifications and Email

### 15.1 Lead flow and model

```
Visitor → public portfolio → Service / "Hire me" → form
  → spam gate (honeypot + time-trap + rate limit + optional CAPTCHA on suspicion)
  → Lead(status=NEW)  → notify owner (instant or digest)  → CMS inbox
```

```python
Lead: portfolio service(FK, optional) name email phone company message budget
      preferred_contact source_page status[NEW|CONTACTED|QUALIFIED|WON|LOST|SPAM]
      spam_score ip_hash user_agent utm(JSONB) internal_note
      responded_at created_at
      index(portfolio, status, -created_at)
```

- Owners are notified per preference; leads are visible only to account members with lead access and to platform staff via audited impersonation (§30.4). **Never public, never in a sitemap, never in an OG tag.**
- `ip_hash` is a salted hash, not a raw IP (§30.2 data minimisation).
- Spam defence (SEC-3): honeypot field, minimum form-fill time, per-IP and per-portfolio rate limits (Redis), heuristic scoring, CAPTCHA only when score is suspicious (a CAPTCHA on every form costs real conversions), and quarantine to `SPAM` rather than silent discard so false positives are recoverable.
- Lead volume/retention is entitlement-bound (§7.4).

### 15.2 Notification and email architecture (FR-15.1)

v2.0 said owners are "notified by email/in-app" and specified none of the infrastructure that requires. It is specified here because a platform sending mail on behalf of 10,000 tenants has a domain-reputation problem the moment spam signups begin.

```python
Notification: account user kind title body link_url read_at created_at
NotificationPreference: user kind channel[email|in_app|off] digest[instant|daily|weekly]
EmailMessage: id to_email template_code context(JSONB) provider_message_id
       status[queued|sent|delivered|bounced|complained|failed] error
       related_object_ref created_at
```

- Single transactional provider behind an `EmailProvider` interface; all sends are Celery tasks on the `email` queue, idempotent by `(template_code, related_object, to_email)`.
- **Deliverability is a launch blocker (OPS-2):** SPF, DKIM and DMARC on the sending domain, a dedicated subdomain for transactional mail, warm-up, and monitoring of bounce/complaint rates with alerting.
- **Lead notification emails set `Reply-To` to the lead's address**, so the owner replies directly from their own inbox. Small detail, disproportionate effect on how the product feels.
- Bounce/complaint webhooks update `EmailMessage` and suppress repeat sends to hard-bounced addresses.
- Non-transactional mail carries one-click unsubscribe; transactional mail does not (and is scoped narrowly enough to justify that).
- Email verification is required before a portfolio may be **published** (§25.2) — this is the cheapest, most effective anti-abuse control available.

---

## 16. Public Site Rendering, URLs, SEO and Caching

### 16.1 URL scheme (ADR-002)

| Surface | URL |
|---|---|
| CMS | `https://app.<domain>/` |
| Public portfolio | `https://<portfolio-slug>.<domain>/` |
| Custom domain | `https://<customer-domain>/` (§17) |
| CMS API | `https://api.<domain>/api/v1/` |
| Public JSON (read-only) | `https://<portfolio-slug>.<domain>/data.json` |

**Public content is served from a different origin than the CMS** (subdomain per portfolio, not v2.0's `/p/<slug>/` path). Reason (SEC-4): user-authored HTML rendered on the same origin as the CMS means any stored-XSS escape reaches CMS tokens and cookies. Origin separation makes that structurally impossible, and it is also what makes custom domains a routing change rather than a rewrite. Legacy `/p/<slug>/` paths 301 to the subdomain. Cost accepted: a wildcard TLS certificate and wildcard DNS.

### 16.2 Resolver

```
request (Host header, path)
  → resolve host: platform subdomain → slug | custom domain → Domain → portfolio
  → 404 if unknown host; 301 if slug in PortfolioSlugHistory (§16.4)
  → preview token present? → render unpublished, noindex, no-store  (§12.4)
  → publication_state == published?  no → 404 (or 410 if account closed;
       or a branded "coming soon" page if the owner opted in)
  → account/portfolio suspended? → 451/404 + noindex (§25.3)
  → load PortfolioThemeSettings → theme pack → published content only
  → render HTML → cache (§16.5)
```
The resolver uses **public selectors only**: read-only querysets filtered to published state, replica-safe (NFR-3.3), and never touching a private field. NFR-1.7 caps the query count at 15 with an automated assertion.

### 16.3 SEO requirements (FR-16.x)

| ID | Requirement |
|---|---|
| FR-16.1 | Fully server-rendered HTML for every public page. JavaScript is progressive enhancement only; content MUST be present with JS disabled. |
| FR-16.2 | Per-page `<title>`, meta description, canonical URL, Open Graph and Twitter Card tags — CMS-editable, with sensible defaults derived from the primary profession and profile. |
| FR-16.3 | `sitemap.xml` per portfolio (published URLs only) and a platform sitemap index. |
| FR-16.4 | `robots.txt` per host: published portfolios indexable; drafts, previews, suspended and `is_indexable=False` portfolios `noindex` and disallowed. |
| FR-16.5 | Structured data (JSON-LD): `Person` / `ProfilePage`, `Article` for blog posts, `Service`, `Review` for testimonials, `BreadcrumbList`. Validated in CI against the Schema.org vocabulary. |
| FR-16.6 | Slugs unique, URL-safe, reserved-word checked (Appendix D), user-editable with redirect history. |
| FR-16.7 | Auto-generated OG images per portfolio/post when the user supplies none. |
| FR-16.8 | Custom-domain sites canonicalize to the custom domain; the platform subdomain 301s to it — never two indexable copies of the same content. |

### 16.4 Slug changes (FR-16.6) — a concrete v2.0 gap

v2.0 allowed user-editable slugs with no redirect story. A rename would 404 every indexed URL, shared link and QR code — on a platform whose value proposition is discoverability. Therefore: `PortfolioSlugHistory` (and per-object slug history for projects and posts) with permanent **301** redirects from every previous slug, a reserved-slug list, and a rename rate limit of 2 per 30 days with an explicit in-CMS warning about existing links.

### 16.5 Caching and invalidation (NFR-1.1, NFR-2.5)

- CDN cache key: `host + path + locale`, `Cache-Control: public, s-maxage=300, stale-while-revalidate=86400, stale-if-error=604800`.
- **Explicit purge on**: publish/unpublish/schedule-fire, theme or appearance change, profile/content/project/service/testimonial/post change, slug change, domain change, suspension. All purges originate from `publishing.services` (§12.1), which is why nothing else may mutate publication state.
- Surrogate keys per portfolio (`portfolio:<uuid>`) so a purge is one tag invalidation rather than a URL enumeration.
- Origin-side per-portfolio fragment cache in Redis for the render, plus `ETag`/`Last-Modified` for conditional GETs.
- `stale-if-error` means a published portfolio survives an origin outage — this is how NFR-2.1's 99.9% is actually achieved.

---

## 17. Custom Domains

v2.0 gave this one sentence. It is a top-two paid feature and the most support-heavy one, so it gets a specification.

```python
Domain: id portfolio(FK) hostname(unique) status[pending|verifying|active|failed|removed]
        verification_token verification_method[txt|cname] verified_at
        tls_status[none|pending|active|renew_failed] tls_expires_at
        is_primary redirect_to_primary last_checked_at error_detail
```

Flow: add domain → show DNS instructions → poll DNS (backoff, max 7 days) → verify → request certificate (ACME/HTTP-01 or DNS-01) → activate → serve. Renewal at 30 days remaining with alerting on failure; `renew_failed` pages support before the customer notices.

Implementation requirements: apex-vs-`www` guidance including the ALIAS/ANAME caveat for apex domains, one primary host with 301 from all others (FR-16.8), per-host CORS and cookie scoping, an SNI-capable edge, ACME rate-limit awareness (batch and back off), and an entitlement gate (`custom_domain`). Removing a domain purges cache and reverts the canonical URL to the platform subdomain.

---

## 18. CMS Architecture

The CMS is a React SPA at `app.<domain>`; Django Admin is for **platform** administration only, never end-user portfolio management.

Navigation: Overview · Profile · Career · Professions · Content · Projects · Services · Testimonials · Blog · CV Builder · Leads · Analytics · Theme · Domains · Members · Billing · Settings.

Requirements:

| ID | Requirement |
|---|---|
| FR-18.1 | Publication status and the public URL are visible on every screen, with one-click "view live" and "share preview". |
| FR-18.2 | All input validated client-side *and* server-side; server messages are the authority and are rendered per-field from the error envelope (§20.4). |
| FR-18.3 | Autosave, crash recovery and unsaved-change guards on every editor (§12.5). |
| FR-18.4 | Uploads show progress, client-side validation, previews, and per-plan quota usage with a clear message on rejection. |
| FR-18.5 | Onboarding checklist with measured activation: **published portfolio within 10 minutes of signup** for the median new user. Profession-based starter content (real placeholder sections and demo project) is offered on first run and is removable in one click. |
| FR-18.6 | Every destructive action confirms and is undoable via revisions (§12.2) or soft delete for 30 days. |
| FR-18.7 | Empty states teach rather than block: each section explains what it is for and offers an example. |
| FR-18.8 | Accessible to non-technical users across all professions: no jargon, no schema vocabulary in labels. |

---

## 19. Frontend Architecture (CMS)

```
src/
├── app/            # providers, router, query client, error boundary
├── api/            # generated OpenAPI client (§20.2) — never hand-written
├── components/     # design-system primitives
├── layouts/
├── features/       # accounts billing portfolios profiles career professionals
│                   # content projects services testimonials blog cv leads
│                   # analytics themes domains members
├── hooks/  utils/  i18n/  routes/  types/
```

- **TypeScript strict**; the API client and types are **generated from the OpenAPI schema** in CI, so a backend contract change breaks the frontend build rather than production.
- **TanStack Query** for all server state (caching, invalidation, optimistic updates); no server data in global stores.
- Forms: React Hook Form + Zod, with Zod schemas derived from the OpenAPI schema where possible.
- Routes: `/login`, `/register`, `/verify-email`, `/onboarding`, `/dashboard/*`, `/billing/*`.
- Access tokens in memory only; refresh token in an `HttpOnly` `Secure` `SameSite=Strict` cookie scoped to the API origin (SEC-5). No tokens in `localStorage`.
- Code-split per feature; the CMS bundle budget is enforced in CI.
- All strings through `react-i18next` from the first commit (§21.1) — retrofitting translation keys into every component is the expensive alternative.

---

## 20. API Architecture and Standards

### 20.1 Structure

`https://api.<domain>/api/v1/` — private, JWT-authenticated, account-scoped:

`/auth/` · `/accounts/` · `/members/` · `/billing/` (plans, subscription, portal, webhooks) · `/portfolios/` · `/professions/` · `/profiles/` · `/career/{experience,education,skills,certifications,achievements}/` · `/content/` · `/projects/` · `/services/` · `/testimonials/` · `/blog/` · `/cv/{versions,templates,snapshots,share-links}/` · `/leads/` · `/themes/` · `/media/` · `/domains/` · `/analytics/` · `/notifications/` · `/preview-tokens/` · `/revisions/` · `/export/`

Public read-only endpoints live on the portfolio host, not here (`/data.json`, `/sitemap.xml`, `/robots.txt`, `POST /leads/` for the contact form, `POST /events/` for analytics), each with its own throttle class and public serializer.

### 20.2 Contract (NFR-4.5)

`drf-spectacular` generates the OpenAPI 3.1 schema in CI; the frontend client is generated from it; a breaking-change diff against the last release fails the build unless `v` is bumped. This is what makes versioning enforceable rather than aspirational.

### 20.3 Conventions

- URL versioning from day one (`/api/v1/`). Internal restructuring never breaks a released version.
- Cursor pagination on all list endpoints; `page_size` default 20, hard cap 100 (NFR-1.6).
- Consistent filters: `?published=&q=&ordering=&created_after=`; `?fields=` for sparse fieldsets.
- `PATCH` for partial updates with optimistic concurrency (§12.5); `POST` for creation and explicit named actions (`/publish/`, `/unpublish/`, `/duplicate/`, `/render/`).
- Idempotency: `Idempotency-Key` header honoured on all `POST` endpoints that cost money or send mail.
- Throttle classes: `public_anon` (60/min/IP), `public_form` (5/hour/IP + per-portfolio), `authenticated` (600/min/account), `expensive` (CV render, export: per-plan), `admin`. `429` carries `Retry-After`.
- `402 Payment Required` is the canonical entitlement-exceeded response, with `feature`, `limit`, `usage` and an upgrade URL in the payload.

### 20.4 Error envelope

```json
{ "error": { "code": "validation_error", "message": "Human readable summary",
             "fields": { "slug": ["This slug is reserved."] },
             "correlation_id": "01J8..." } }
```
Single DRF exception handler, one shape for every error including 402/409/429/500, `correlation_id` matching the log entry (§28.1) so a user-reported error is traceable in one query.

---

## 21. Internationalization and Accessibility

### 21.1 i18n

- CMS strings externalized via `react-i18next` from the first commit; backend user-facing strings via Django `gettext`. English ships at launch; adding a locale is a translation file.
- **RTL support designed in**: logical CSS properties (`margin-inline-start`, not `margin-left`), `dir` on `<html>`, and one RTL locale exercised in visual-regression tests from the start — retrofitting RTL after the fact means re-auditing every component.
- Owner content is user-authored and not machine-translated (out of scope, §33.4); `Portfolio.primary_locale` sets `lang` for accessibility and SEO. The schema does not block per-locale content later (content models are already keyed by portfolio + key).
- Currency: ISO 4217 code stored per Service and per Plan; formatting at render time by locale.
- All timestamps stored in UTC (`USE_TZ = True`); rendered in the viewer's timezone; the owner's timezone on `Profile` drives scheduling display.

### 21.2 Accessibility (WCAG 2.1 AA)

| ID | Requirement |
|---|---|
| FR-21.1 | Every theme meets WCAG 2.1 AA colour contrast and full keyboard navigability. Colour presets are contrast-checked programmatically, and a user-chosen custom colour that fails contrast is rejected with an explanation. |
| FR-21.2 | Every image has an editable alt-text field; the CMS warns (does not block) on missing alt text. |
| FR-21.3 | CMS forms: label associations, visible focus states, error text tied via `aria-describedby`, no colour-only signalling. |
| FR-21.4 | `axe-core` runs in CI against the CMS and every theme; new AA violations fail the build (§27.5). This is what makes the AA claim real rather than aspirational. |
| FR-21.5 | An accessibility statement is published; a VPAT is prepared when the first enterprise/public-sector customer requires it. |

---

## 22. Media, Storage and CDN Strategy

```python
MediaAsset: id account portfolio(nullable) kind[image|document|video_embed]
       original_filename storage_key content_type byte_size width height
       checksum(sha256) alt_text caption scan_status[pending|clean|infected|error]
       uploaded_by created_at is_deleted
MediaDerivative: asset preset[thumb|sm|md|lg|og] storage_key width height
       byte_size format[webp|avif|jpeg]
```

- Object storage only, never application-server disk (NFR-3.2).
- CDN in front of public media; long-lived immutable cache keys (content-hashed paths).
- Uploads: **direct-to-storage presigned PUT** (keeps large files off application servers), then a server-side confirm step that validates content type by **magic bytes, not extension or client-declared MIME**, enforces size caps (5 MB images / 10 MB documents by default, per-plan), enforces dimension caps, and calls `entitlements.check_and_consume("storage_bytes")`.
- Derivatives generated asynchronously (`media` queue) into WebP/AVIF with a JPEG fallback; `srcset` on the public site.
- **Malware scanning** before an asset becomes publicly reachable (SEC-6, §25.4); `pending` assets are not served.
- SVG uploads are either rejected or sanitized server-side — an SVG is executable content.
- Per-account `storage_bytes` usage counter is the billing input (§7.1) and is reconciled nightly against storage.
- EXIF (including GPS) stripped from public images by default (§30.2).
- **Object storage is backed up and versioned** (§29.4) — "we restored the database but the images are gone" is a real failure mode that v2.0's backup plan did not cover.

---

## 23. Owner-Facing Analytics

v2.0 covered operational telemetry but not the thing customers pay for: their own numbers. This is one of the strongest upsell hooks in the category and needs real design.

```python
PageViewEvent (append-only, BigAutoField pk, partitioned monthly):
    portfolio path referrer_host country device_type is_bot
    session_hash occurred_at
DailyRollup: portfolio date views unique_visitors lead_count cv_downloads
    top_paths(JSONB) top_referrers(JSONB) countries(JSONB)
    constraints: unique(portfolio, date)
```

- **Cookieless and privacy-respecting**: no cross-site identifier; `session_hash = hash(salt_rotated_daily + ip + user_agent + portfolio)`. This keeps §30.6 free of a consent banner by default, which is both better for conversion and better for users.
- Ingestion: `POST /events/` on the portfolio host, heavily throttled, fire-and-forget, buffered in Redis and flushed by a Celery task. Server-side counting for no-JS visitors and crawlers.
- **Bot filtering** against a maintained UA list plus heuristics, before rollup.
- **Owner dashboards read rollups only, never raw events** — this is what keeps NFR-1.3 true as event volume grows.
- Raw events retained 90 days; rollups retained indefinitely. History window shown to the owner is entitlement-bound (`analytics_history_days`).
- Metrics: views, unique visitors, top pages, top projects, referrers, countries, devices, lead count, **lead conversion rate**, CV downloads, share-link views.

---

## 24. Security and Authorization

### 24.1 Authentication

- Django password hashing (Argon2), password strength validation, breached-password check on set.
- JWT: access token 15 min in memory; refresh token 30 days, `HttpOnly` cookie, **rotated on use with reuse detection** (a replayed refresh token revokes the whole family).
- Email verification required before publishing (§25.2). TOTP 2FA available for all users, required for platform staff (SEC-7).
- Session/device list with individual revocation; all sessions revoked on password change.
- Login throttling per IP and per account with exponential backoff and lockout notification email.

### 24.2 Tenant isolation by mechanism (SEC-8) — the top risk in v2.0's own risk table

v2.0 required queryset-level ownership checks; nothing enforced it, so a single forgetful ViewSet is a data breach and code review is the only guard. v3.0 makes it structural:

1. `PortfolioOwnedModel.objects` is a `PortfolioScopedManager` whose default `get_queryset()` **raises** unless `.for_portfolio(p)` or `.unscoped_explicit()` has been called. Forgetting the scope is a loud 500 in development, not a silent leak in production.
2. `PortfolioScopedViewSet` derives the portfolio from the authenticated membership; `get_queryset()` is not hand-written per app.
3. **A CI meta-test enumerates every registered DRF route** and fails if the view is not a `PortfolioScopedViewSet`/public-declared view or is not on an explicit, reviewed allowlist. A new endpoint cannot be merged unscoped.
4. **A CI serializer test** asserts that no public serializer's field set intersects the declared private-field registry per model.
5. Cross-tenant test fixtures: the default factory set creates **two** accounts, so writing a cross-tenant test is the path of least resistance (§27.4).
6. PostgreSQL **Row-Level Security** on `leads`, `media_asset` and `cv_snapshot` as defence in depth (ADR-008): a bug in the ORM layer still cannot read another tenant's leads.

### 24.3 Authorization

Declarative permission table implementing §6.2, tested cell-by-cell. Object-level checks are always at the queryset level, never post-hoc in view logic. The backend is the sole authority (P-8).

### 24.4 Output safety

- All rich text sanitized **server-side on write** with a strict allowlist (`nh3`/`bleach`): no `<script>`, no `on*` handlers, no `javascript:`, no `<iframe>` except an allowlisted embed set (YouTube/Vimeo) rendered through a server-generated wrapper.
- Django templates autoescape; `|safe` is permitted only on fields sanitized at write time, and its use is enumerated and reviewed in CI.
- CSP on public hosts: `default-src 'self'`, no inline scripts (nonce-based where needed), `frame-ancestors 'none'` on the CMS, plus `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`. Origin separation (§16.1) is the structural backstop.
- User uploads served from a distinct storage domain with `Content-Disposition` and a fixed content type, so an uploaded HTML file can never execute on a portfolio origin.

### 24.5 Platform hardening

HTTPS enforced with HSTS (`includeSubDomains`, preload). CORS allowlisted per environment; wildcard never. Secrets in a secrets manager, never in source control, rotated on a schedule with a documented rotation runbook. Dependency scanning (`pip-audit`, `npm audit`, Dependabot) and container image scanning in CI; a critical CVE fails the build. SQL only through the ORM or parameterized queries. `DEBUG = False` and a settings-assertion test that fails production deploys with unsafe settings.

### 24.6 Audit trail

Append-only `AuditLog` (actor, actor_type, account, portfolio, action, target, before/after diff, ip_hash, correlation_id, created_at) for: login/logout/failed login, permission and membership changes, publish/unpublish, slug and domain changes, plan changes, exports, deletions, **impersonation start/end**, and moderation actions. Write-only from application code, retained 2 years, exportable for an incident.

---

## 25. Abuse, Moderation and Platform Trust

A multi-tenant platform hosting public UGC on a shared domain inherits every tenant's reputation: **one phishing portfolio can get the entire domain flagged by Safe Browsing, which takes every customer offline.** v2.0 had no abuse model at all. This section is not optional.

| ID | Control |
|---|---|
| SEC-9 | Email verification required before first publish; signup rate limits per IP/ASN; disposable-domain blocklist. |
| SEC-10 | New-account publish limits (portfolios per account per day) and outbound-link limits until an account has aged or paid. |
| SEC-11 | Automated screening on publish: phishing keyword/brand-impersonation heuristics, link reputation check, and a review queue for anything flagged. |
| SEC-12 | Upload malware scanning; infected assets quarantined and the account flagged (§22). |
| SEC-13 | "Report this portfolio" link on every public page → `Report` record → moderation queue with SLA. |
| SEC-14 | Moderation actions: warn, `noindex`, unpublish, suspend portfolio, suspend account — all audited, all reversible, all notifying the owner with an appeal path. |
| SEC-15 | Published ToS/AUP and a DMCA/takedown process with a named contact. |
| SEC-16 | Suspended content returns 451/404 with `noindex` and is purged from the CDN immediately. |
| SEC-17 | Reserved slug list prevents impersonation of the platform and well-known brands (Appendix D). |
| SEC-18 | Safe Browsing / domain-reputation monitoring with an alert, so a flag is discovered by the team, not by 10,000 customers. |

```python
Report: id target_type target_id reporter_email reason detail status[open|reviewing|
        actioned|dismissed] handled_by handled_at resolution_note created_at
ModerationAction: target actor action reason expires_at audit_ref created_at
```

---

## 26. Database Design Standards

- PostgreSQL 16. Primary for writes; read replica for public reads (NFR-3.3).
- **PK rule (ADR-009), one rule for everything:** `UUIDv4` primary keys on all domain models (publicly addressable, safe to expose, migration-friendly); `BigAutoField` on high-volume append-only tables (`PageViewEvent`, `AuditLog`, `EmailMessage`) where index locality matters. v2.0's "UUID where appropriate after ERD review" is exactly the kind of per-model judgement that produces an inconsistent schema.
- Every content model: `FK → Portfolio` with an explicit `on_delete`. **Cascade rules are declared per relationship**, never left to a default: content `CASCADE` from Portfolio; `Lead.service` `SET_NULL` (deleting a service must not destroy the lead); `MediaAsset` references `PROTECT` where the asset is in use; `CVSnapshot` `PROTECT` against template deletion.
- Soft delete (`is_deleted`, `deleted_at`) on all user-generated content with a 30-day recovery window and a purge job; `objects` excludes deleted, `all_objects` includes.
- `created_at` / `updated_at` on everything; `sort_order` on every user-orderable collection (integer with gap-based reordering, not a full renumber per drag).
- Constraints in the database, not only in serializers: unique slugs scoped correctly, exactly-one-primary-profession, exactly-one-owner-per-account, check constraints on ratings and date ranges (`end_date >= start_date`), non-negative amounts.
- Indexes on every public lookup path, every ownership filter, and every publication-state filter: `(portfolio, publication_state, -published_at)`, `Portfolio(slug)`, `Domain(hostname)`, `Lead(portfolio, status, -created_at)`.
- JSONB is validated against a JSON Schema on write, and is never used for anything that needs querying or constraints.
- Money: `DecimalField(12, 2)` + ISO 4217 code. Never float, never a symbol.
- Migrations are reviewed artifacts; expand/contract for anything destructive; no migration that locks a large table without a documented plan (`CONCURRENTLY` for index creation).

---

## 27. Testing Strategy

Nothing is "done" without the tests named in §31.

### 27.1 Unit (per app)
Models, constraints, serializers, services, selectors, entitlement resolution, state machines. Coverage gate: **85% overall, 100% on `core` scoping, `billing/entitlements`, publishing transitions and permission logic** — coverage percentage alone is not the goal, but these four areas are where an untested line is a breach or a billing error.

### 27.2 Integration
Every API group: authenticated, unauthenticated, wrong-role, wrong-tenant, over-quota (402), conflicting-version (409), throttled (429).

### 27.3 Contract
OpenAPI schema generated and diffed for breaking changes (NFR-4.5); the generated frontend client compiles against it.

### 27.4 Security (SEC-8, SEC-1)
- **Cross-tenant matrix**: for every tenant-scoped endpoint, User A's token against Portfolio B — asserted to 403/404 and generated automatically from the route table so a new endpoint is covered on the day it is added.
- **Authorization matrix**: every cell of §6.2 asserted.
- Public-serializer field-leak assertions; the private-field registry test.
- Auth flow tests: refresh rotation and reuse detection, throttles, lockouts.
- OWASP Top 10 checks including stored-XSS payload fixtures through every rich-text field.

### 27.5 Frontend, visual and accessibility
Vitest + React Testing Library for CMS components and forms. **Playwright visual-regression snapshots per theme × breakpoint × light/dark × one RTL locale** — this replaces v2.0's manual theme QA checklist, which does not scale past a handful of themes. `axe-core` on the CMS and every theme; new AA violations fail the build (FR-21.4). Lighthouse CI on the default theme against NFR-1.4.

### 27.6 End-to-end and load
E2E critical paths: register → verify → onboard → build → publish → view public page → submit lead → owner notified → generate CV → download PDF; plus subscribe → entitlement granted → downgrade → limits enforced; plus add custom domain → verify → serve.
**Load test (validates NFR-3.1)** with a seeded 10,000-portfolio dataset: 1,000 concurrent public visitors, a realistic cache hit ratio, CV render burst, lead form flood. Pass criteria are the §3.1 numbers. Run before production launch and per release train.

### 27.7 Data and process
Golden-file PDF tests per CV template (page count + checksum). Migration tests on a production-shaped dump. Factory/fixture strategy with two accounts by default. Flaky-test policy: quarantined within 24 h with an owner and a deadline, never silently retried. All of the above run in CI on every pull request; merges are blocked on failure.

---

## 28. Observability, Support and Operations

### 28.1 Logging
Structured JSON logs from web and workers, shipped to aggregation. Every log line carries `correlation_id`, `account_id`, `portfolio_id` (where applicable) and release version. The correlation ID is returned to clients in the error envelope (§20.4) and in a response header, so a user-reported problem is one search away. **PII is never logged** (no emails, no lead content, no tokens) — enforced by a log-scrubbing filter and a test.

### 28.2 Errors and tracing
Sentry (or equivalent) for backend, worker and CMS runtime errors, with release tagging, source maps and alert routing. Correlation IDs propagate into Celery tasks so a CV-render failure links back to the originating request.

### 28.3 Metrics, health and alerts
`/healthz` (liveness), `/readyz` (DB, Redis, storage, queue depth). Dashboards: request rate/latency/error rate per endpoint class, queue depth and age per queue, CV render success rate and duration, email delivery/bounce rate, cache hit ratio, DB connections and slow queries, subscription/webhook processing lag. **Alerts fire on SLO burn rate (NFR-2.3)**, dead-letter arrivals, queue age, TLS renewal failure, backup failure, webhook backlog and Safe Browsing flags — not on raw CPU.

### 28.4 Support back-office (OPS-3)
A staff-only console (not Django Admin's raw model views) providing: find account/user/portfolio, view plan, subscription, usage and invoice pointers, resend verification, force password reset, unpublish/suspend, grant an entitlement override, and **audited impersonation** — mandatory reason, 30-minute hard limit, a visible banner in-session, an `AuditLog` entry, and a notification to the account owner. Support workflows get built eventually; specifying them costs a paragraph now and prevents production shell access becoming the support tool.

### 28.5 Incident response
Severity levels with response targets, on-call rotation, public status page, an incident channel and template, and a blameless postmortem required for Sev-1/2 with tracked actions. Runbooks stored in-repo for: restore from backup, failed migration, queue backlog, TLS renewal failure, payment provider outage, storage outage, Safe Browsing flag, mass-spam-signup event.

---

## 29. Deployment, Environments and CI/CD

### 29.1 Environments
`local` (Docker Compose: Postgres, Redis, MinIO, MailHog) → `ci` (ephemeral) → `staging` (production-shaped, anonymized data, load-test target) → `production`. Same container image promoted across environments; configuration only by environment variables.

### 29.2 Topology
Containerized Django (gunicorn/uvicorn) behind a load balancer; separate deployments per Celery queue (`pdf`, `email`, `analytics`, `media`, `billing`, `maintenance`) so NFR-3.4 is a deployment property; Celery beat as a single instance with a lock; managed PostgreSQL with a read replica; managed Redis; S3-compatible storage; CDN for public HTML and media.

### 29.3 Pipeline
On PR: lint, format, type-check (`mypy`, `tsc`), unit, integration, security-matrix, frontend, accessibility, visual-regression, OpenAPI diff, migration check, dependency and image scan, bundle budget. Merge to `main` → build image → deploy to staging → E2E on staging → **manual approval** → production. Rolling deploys with health gates and automated rollback on error-rate breach.

**Migrations are an explicit, reviewed pipeline step**, run separately from application rollout, backward-compatible (expand/contract) so a rollback never needs a down-migration. Destructive migrations require a named approver.

**Feature flags** for risky or partially complete features, resolvable per account so a feature can be enabled for one tenant before general rollout.

### 29.4 Backup and disaster recovery (OPS-4)
| ID | Requirement |
|---|---|
| OPS-4.1 | **RPO ≤ 15 minutes** (continuous WAL archiving / PITR), **RTO ≤ 4 hours**. Named numbers, because "backups are tested" is not a recovery objective. |
| OPS-4.2 | Daily full database backups, 30-day retention, encrypted, stored in a separate region/account. |
| OPS-4.3 | **Object storage is versioned and replicated** — media is not in the database. |
| OPS-4.4 | Quarterly restore drill into a scratch environment, timed, with results recorded against the RTO. A drill that is not timed is not a drill. |
| OPS-4.5 | Documented, rehearsed restore runbook; backup failure alerts to on-call. |

---

## 30. Data Privacy and Compliance

### 30.1 Roles (the distinction v2.0 missed)
For **account and portfolio data**, the platform is the **controller**. For **lead data and testimonials** — personal data about third parties submitted to a portfolio — the **portfolio owner is the controller and the platform is the processor**. This is not a technicality: it means the platform must offer a **DPA** to owners, must publish a **sub-processor list**, and must expose lead-form notice text that names the owner as the recipient. Every downstream requirement follows from getting this right.

### 30.2 Data minimisation
Collect only what is used: no raw IPs stored (salted hashes only), no cross-site tracking, no third-party analytics on public pages by default, EXIF/GPS stripped from public images, lead data retained per owner setting and per plan.

### 30.3 Rights and lifecycle
| ID | Requirement |
|---|---|
| FR-30.1 | **Self-service export**: full account data (profile, career, content, projects, services, testimonials, posts, CVs, leads, media manifest) as a downloadable JSON + media archive, generated asynchronously. |
| FR-30.2 | **Self-service deletion**: account closure → immediate unpublish and CMS lockout → 30-day recovery window → deletion or anonymization of personal data, with a documented list of what is retained (invoices/tax records as required by law, audit log entries pseudonymized). |
| FR-30.3 | DSAR (access, rectification, erasure, portability, objection) responded to within **30 days**; owner-facing tooling covers the common cases without engineering involvement. |
| FR-30.4 | Retention policy: raw analytics 90 days, logs 30 days, backups 30 days, soft-deleted content 30 days, closed accounts purged at 30 days, audit log 2 years. |
| FR-30.5 | **Breach notification within 72 hours** to the relevant authority and affected users; the incident runbook (§28.5) includes the notification path and templates. |

### 30.4 Lead data
Visible only to authorized account members and to platform staff via audited impersonation. Never public, never indexed, never in an OG tag or sitemap. Exportable and deletable by the owner.

### 30.5 Documents required at launch
Privacy policy, ToS/AUP, cookie policy, DPA (offerable to owners), sub-processor list, security page, accessibility statement (§21.2), and a stated data-residency position.

### 30.6 Cookies and consent
The default build is **cookieless on public pages** (§23), so no consent banner is needed by default — better for conversion and for users. If an owner enables a third-party integration, or the platform later adds tracking, a **geo-aware consent gate** loads it only after consent. The CMS uses strictly-necessary cookies only.

---

## 31. Traceability Matrix

Extract; the full matrix is maintained in-repo as `docs/traceability.md` and a CI check fails when a requirement ID has no linked test.

| ID | Requirement | Phase | Proving test |
|---|---|---|---|
| SEC-8 | Tenant isolation by mechanism | 1 | `test_route_scoping_meta`, `test_cross_tenant_matrix`, RLS tests |
| SEC-1 / FR-6.1 | Role matrix | 1 | `test_authorization_matrix` (per cell) |
| FR-7.1 / SEC-2 | Entitlements and subscription effects | 1 (schema), 4 (billing) | `test_entitlements_resolution`, `test_subscription_state_effects` |
| NFR-1.1/1.2 | Public TTFB | 3 | Load test + CDN synthetic checks |
| NFR-1.4 | Core Web Vitals | 3 | Lighthouse CI + field RUM |
| NFR-1.7 | ≤15 queries per public render | 3 | `test_public_render_query_count` |
| FR-16.1 | Server-rendered public HTML | 3 | `test_public_html_without_js`, crawler fetch test |
| FR-16.6 | Slug history and 301s | 3 | `test_slug_redirects` |
| FR-12.1–12.4 | Revisions, scheduling, preview, autosave | 2–3 | `test_revision_restore`, `test_scheduled_publish`, `test_preview_token_noindex`, E2E autosave |
| FR-13.1 | ATS-friendly deterministic PDFs | 4 | Golden-file PDF tests, text-extraction assertion |
| NFR-2.6 | Idempotent retryable jobs | 2+ | Task idempotency tests, DLQ test |
| NFR-3.1 | 10k portfolios / 1k concurrent | 5 | Load test with pass criteria |
| FR-21.1/21.4 | WCAG 2.1 AA | 3–5 | `axe` CI per theme, contrast tests |
| SEC-9–SEC-18 | Abuse controls | 5 | Moderation integration tests |
| FR-30.1/30.2 | Export and deletion | 5 | E2E export/delete tests |
| OPS-4.1 | RPO/RTO | 5 | Timed restore drill record |

---

## 32. Implementation Plan and Definitions of Done

Universal DoD (every phase, every PR): tests written and passing · lint/format/type-check clean · OpenAPI regenerated · migrations reviewed · requirement IDs linked in the traceability matrix · docs/ADRs updated · observability (logs/metrics for new paths) · no new accessibility violations · deployed to staging and exercised.

### Phase 0 — Foundations (before any feature)
`core` base models, tenant-scoped manager/viewset and **the CI scoping meta-test**, error envelope, correlation IDs, settings/env layout, Docker Compose, CI pipeline with every gate, OpenAPI generation, factory/fixture strategy with two accounts, `AuditLog`.
**DoD:** an intentionally unscoped test endpoint **fails CI**. That single demonstration is what makes P-4 real; do not proceed until it does.

### Phase 1 — Tenancy, accounts, billing schema
`accounts` (User, Account, AccountMembership, verification, JWT with rotation, 2FA), role matrix + authorization-matrix test, `portfolios` (slug, reserved words, slug history, publication state machine), `billing` schema + entitlements service with hardcoded free/pro values and **no payment provider yet**, usage counters.
**DoD:** two accounts cannot see each other's data (matrix test green); entitlement limits enforced on portfolio creation; the role matrix passes cell-by-cell.
*Rationale: v2.0 placed billing in phase 5. Entitlements and tenancy are schema-shaping, so adding them last means migrating live tenant data. The provider integration is late; the schema is early.*

### Phase 2 — Content core
`professionals`, `profiles`, `career`, `content`, `projects`, `services`, `testimonials`, `blog`, `media` (presigned upload, validation, derivatives), `publishing` (revisions, scheduling, preview tokens), CMS shell with autosave.
**DoD:** a portfolio can be fully populated through the API and the CMS; revisions restore; autosave survives a forced browser crash; uploads enforce quota.

### Phase 3 — Public experience (the value proposition)
`public` renderer, `themes` (default pack + 2 themes), SEO complete (FR-16.x), caching and invalidation, `sitemap.xml`/`robots.txt`, structured data, slug redirects, visual-regression and axe harness, theme preview in CMS.
**DoD:** a published portfolio renders with JS disabled; Lighthouse ≥ 90; NFR-1.7 query count green; publish purges cache within 5 s; every SEO requirement has a passing test.

### Phase 4 — Differentiators and revenue
`cv` (templates, versions, snapshots, WeasyPrint pipeline, share links, DOCX for two templates), `leads` + spam defence, `notifications` + email with SPF/DKIM/DMARC live, `analytics` (ingestion + rollups + owner dashboard), payment provider integration + checkout + portal + webhooks + reconciliation, `domains` (verification + ACME).
**DoD:** end-to-end subscribe → entitlement granted → downgrade enforced; a lead reaches the owner's inbox with a working `Reply-To`; a CV PDF passes ATS text extraction and golden-file checks; a custom domain serves with valid TLS.

### Phase 5 — Production readiness
`moderation` and all SEC-9–SEC-18 controls, support back-office with audited impersonation, privacy tooling (export, deletion, DSAR), load test against NFR-3.1, DR drill against OPS-4, alerting and runbooks, security review, legal documents, status page.
**DoD:** load test passes at the §3.1 numbers; a timed restore meets RTO; export and deletion work end to end; every SEC and OPS requirement has a passing test or a signed-off record.

### Phase 6 — Post-launch (design allows, not built)
Team seats UI, AI assistance with credit accounting, public directory, third-party API + webhooks + embeds, per-locale content, additional themes.

---

## 33. Risks, Assumptions, Dependencies and Out of Scope

### 33.1 Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Cross-tenant data leakage | Critical | §24.2 mechanism + generated matrix tests + RLS; a phase-0 gate proves the mechanism before features exist |
| Shared-domain reputation damage from one abusive tenant | Critical | §25 controls; origin separation (§16.1); Safe Browsing monitoring (SEC-18) |
| Payment provider unavailable in the operating country | High | `PaymentProvider` interface + DEP-1 resolved before phase 4 |
| Public pages slow or unindexed | High | Server-rendered HTML (ADR-003), CDN caching, NFR-1.7 query cap, Lighthouse CI |
| Content loss through editing or theme switching | High | Revisions, autosave, soft delete, theme-switch equality test |
| PDF rendering saturating workers | Medium | Dedicated queue, per-account concurrency, timeouts, async-only (§13.5) |
| Slug renames destroying user SEO | Medium | Slug history + 301s + rate limit (§16.4) |
| Stored XSS through rich text or themes | Medium | Write-time sanitization, allowlisted CSS only, CSP, origin separation |
| Spam/abuse of public lead forms | Medium | Layered defence (§15.1), quarantine not discard |
| "Multi-professional" flexibility making every feature generic-and-weak | Medium | Typed career models (ADR-004) + profession suggestions that never restrict (§8) |
| Billing/subscription drift from the provider | Medium | Idempotent webhook ledger + nightly reconciliation (§7.6) |
| Scope creep from six new apps | Medium | Phase gates with explicit DoD; §33.4 non-goals |

### 33.2 Assumptions
Launch locale is English with the i18n framework fully in place. Managed cloud infrastructure, not on-premise. One Account, one Portfolio, one member per customer at launch. Themes are platform-authored. Owners author their own content.

### 33.3 Dependencies (each needs an owner and a date)
**DEP-1** payment provider decision (before phase 4, blocks revenue) · **DEP-2** transactional email provider + sending-domain DNS (before phase 4, blocks leads) · **DEP-3** wildcard DNS + wildcard TLS for `*.<domain>` (before phase 3, blocks the URL scheme) · **DEP-4** CDN with surrogate-key purge and stale-if-error (before phase 3, blocks NFR-1.1/2.5) · **DEP-5** object storage + malware scanning (phase 2) · **DEP-6** error tracking and log aggregation (phase 0) · **DEP-7** legal review of privacy policy, ToS and DPA (before launch).

### 33.4 Out of scope for v1.0 (explicit non-goals)
User-authored or third-party themes (a sandboxing problem, not a feature) · public directory/marketplace (needs moderation maturity first) · AI content generation (needs credit accounting and a training-data position) · third-party developer API with OAuth apps · native mobile apps · machine translation of user content · blog comments · e-commerce/payments *between* an owner and their client · multi-portfolio UI beyond the schema. Each is unblocked by the design; none is built.

---

## 34. Glossary

| Term | Definition |
|---|---|
| **Account** | The billing and quota boundary. Owns the subscription, usage counters and members; owns one or more Portfolios. |
| **Portfolio** | The content and isolation boundary. Every content record belongs to exactly one Portfolio. |
| **Tenant** | The Account for billing and quota purposes; the Portfolio for data-isolation purposes. The two are deliberately distinguished (v2.0 conflated them). |
| **Entitlement** | A feature flag or numeric limit granted by a Plan, resolved only through the entitlements service. |
| **Profession** | A catalogue entry (Photographer, Accountant) a Portfolio may be associated with; drives suggestions, never restrictions. |
| **Theme** | A Django template pack plus allowlisted appearance settings. Contains no content. |
| **Theme pack** | The on-disk templates and compiled stylesheet implementing a theme. |
| **Publication state** | `draft` / `published` / `unpublished` / `scheduled` / `suspended`, mutated only through `publishing.services`. |
| **Revision** | An immutable JSON snapshot of a content object, used for history and restore. |
| **Preview token** | A signed, expiring, `noindex` credential that renders unpublished content through the real renderer. |
| **CV Version** | A user-configured CV definition (sections, order, template, locale) that reads live data. |
| **CV Snapshot** | An immutable capture of the content and template version used for one export, guaranteeing a sent PDF stays reproducible. |
| **Lead** | A contact/hire inquiry from a public visitor, targeted at one Portfolio; third-party personal data for which the owner is the controller. |
| **Public selector** | A read-only, published-only query function used by the public renderer; replica-safe and free of private fields. |
| **Surrogate key** | A CDN cache tag (`portfolio:<uuid>`) enabling one-call invalidation of every page for a portfolio. |
| **Correlation ID** | A per-request identifier threaded through logs, jobs and error responses. |
| **SLO / SLA** | Internal engineering target / external contractual promise; the SLO is deliberately stricter. |

---

## Appendix A — Entity Relationship Specification

```
User ──M:M── Account (AccountMembership: role)
                │
                ├─1:1── Subscription ──M:1── Plan
                ├─1:M── UsageCounter
                ├─1:M── MediaAsset
                └─1:M── Portfolio
                          │
                          ├─1:1── Profile
                          ├─1:1── PortfolioThemeSettings ──M:1── Theme
                          ├─1:M── PortfolioSlugHistory
                          ├─1:M── Domain
                          ├─M:M── Profession  [PortfolioProfession: is_primary, order]
                          ├─1:M── Experience / Education / Skill /
                          │        Certification / Achievement        (career)
                          ├─1:M── ContentSection ──1:M── ContentBlock
                          ├─1:M── Project ──M:M── MediaAsset [ProjectImage]
                          ├─1:M── Service
                          ├─1:M── Testimonial
                          ├─1:M── BlogPost ──M:1── BlogCategory, M:M Tag
                          ├─1:M── CVVersion ──M:1── CVTemplate
                          │           └─1:M── CVSnapshot ──1:M── CVShareLink
                          ├─1:M── Lead ──M:1(optional)── Service
                          ├─1:M── Revision (generic FK)
                          ├─1:M── PreviewToken
                          ├─1:M── PageViewEvent ──► DailyRollup
                          └─1:M── Report / ModerationAction
```

Two boundaries, deliberately: **Account** is where money and quotas live; **Portfolio** is where isolation lives. Every content model attaches to Portfolio, which is what makes tenant scoping, theme independence and CV generation from one source of truth mechanically enforceable rather than aspirational.

Field-level definitions are inline in §6–§23. The implementation deliverable is the generated migration set plus `docs/erd.svg` regenerated in CI from the models, so the diagram cannot drift from the schema.

---

## Appendix B — Architecture Decision Records

| ADR | Decision | Alternatives rejected | Consequences accepted |
|---|---|---|---|
| **ADR-001** | `Account` (billing/quota) → many `Portfolio` (content/isolation), with `AccountMembership` roles | User 1:1 Portfolio (v2.0) | One extra join and one extra model at launch; removes a future breaking migration and unblocks multi-site and team use |
| **ADR-002** | Public sites on per-portfolio subdomains, distinct origin from the CMS | `/p/<slug>/` paths on one origin (v2.0) | Wildcard DNS + wildcard TLS required; in exchange, stored XSS cannot reach CMS credentials and custom domains become routing |
| **ADR-003** | Public pages server-rendered by Django templates; React only for the CMS | Node SSR tier (Remix/Next); client-rendered SPA with prerender service | Themes authored as Django templates rather than React; no second runtime, best TTFB, trivially cacheable, one deployable |
| **ADR-004** | Career history as typed models (`career` app) | Free-form content sections (v2.0 left this open) | More models; enables real CVs, structured data and future CV import |
| **ADR-005** | CV configuration reads live data; every export writes an immutable snapshot including the template version | Always live (v2.0 §11) or always duplicated | Storage cost per export; a sent PDF stays reproducible and template changes never reflow delivered CVs |
| **ADR-006** | Payment provider behind a `PaymentProvider` interface; concrete provider chosen by DEP-1 | Direct Stripe coupling | A thin adapter layer; the provider decision cannot block phases 1–3 or strand the launch |
| **ADR-007** | WeasyPrint for PDF | Headless Chromium; LaTeX | Some CSS unsupported; deterministic, light, sandboxable, no browser process to operate |
| **ADR-008** | PostgreSQL RLS as defence in depth on `leads`, `media_asset`, `cv_snapshot` | Application-layer checks only | Slightly more complex DB setup and connection handling; an ORM-layer bug still cannot leak the highest-value tables |
| **ADR-009** | UUIDv4 PKs on all domain models; `BigAutoField` on append-only high-volume tables | Integer PKs everywhere; "UUID where appropriate" (v2.0) | Marginally larger indexes; one consistent, exposable, migration-safe rule |
| **ADR-010** | Cookieless first-party analytics with rollup tables | Third-party analytics; raw-event querying | Rebuilt basics in-house; no consent banner needed, and owner dashboards stay fast at volume |

---

## Appendix C — Sequence Diagrams

**C.1 Publish → invalidate → serve**
```
CMS ─POST /portfolios/{id}/publish/─► API ─► publishing.services.publish()
   ├─ validate entitlements + required fields
   ├─ write Revision, set state=published, published_at
   ├─ write AuditLog
   └─ enqueue purge(surrogate_key=portfolio:<uuid>)  ──► CDN purge (< 5s)
Visitor ─GET https://slug.domain/─► CDN (miss) ─► public renderer
   ├─ resolve host → portfolio (published?)
   ├─ public selectors (published only, ≤15 queries)
   └─ render theme pack ─► HTML + Cache-Control + ETag ─► CDN stores ─► Visitor
```

**C.2 Lead capture → notification**
```
Visitor ─POST /leads/ (portfolio host)─► spam gate (honeypot, time-trap, rate limit, score)
   ├─ score suspicious → CAPTCHA challenge
   ├─ entitlements.check_and_consume("leads_month")
   ├─ create Lead(status=NEW) + AuditLog
   └─ enqueue notify_owner (email queue, idempotent)
worker ─► render template ─► send via provider (Reply-To: lead.email)
   ├─ EmailMessage(status=sent) → provider webhook → delivered|bounced
   └─ Notification(in_app) for each member with lead access
```

**C.3 CV export**
```
CMS ─POST /cv/versions/{id}/render/─► entitlements.check_and_consume("cv_renders_month")
   ├─ build CVSnapshot.content from live data (immutable) + template_version
   └─ enqueue render (pdf queue, per-account concurrency cap)
worker ─► WeasyPrint(template, snapshot) ─► PDF ─► object storage
   ├─ snapshot.render_status=ok, page_count, checksum
   └─ Notification + email "your CV is ready"
CMS polls / receives notification ─► signed download URL (short TTL)
```

**C.4 Signup → subscription → entitlement**
```
User ─register─► email verification ─► Account + owner membership + Portfolio (free plan)
   └─ onboarding: profession → starter content → publish (target < 10 min)
User ─upgrade─► provider.start_checkout() ─► provider hosted checkout ─► success
provider ─webhook─► verify signature ─► BillingEvent(provider_event_id unique) ─► 200
   └─ async: update Subscription(status=active, period) ─► invalidate entitlement cache
Next request ─► entitlements.features(account) ─► custom_domain, premium_themes unlocked
nightly ─► reconcile local vs provider state ─► alert on divergence
```

---

## Appendix D — Reserved Slugs and Entitlement Catalogue

### D.1 Reserved slugs (SEC-17)
`www, app, api, admin, staff, support, help, docs, blog, mail, smtp, imap, ftp, cdn, static, assets, media, img, images, files, download, downloads, status, dashboard, login, logout, register, signup, signin, auth, oauth, account, accounts, billing, pay, payment, checkout, invoice, security, privacy, terms, legal, dmca, abuse, postmaster, hostmaster, webmaster, noreply, no-reply, test, staging, dev, demo, preview, sitemap, robots, feed, rss, well-known, p, portfolio, portfolios, cv, resume, theme, themes, new, edit, delete, settings, me, you, us, about, contact, pricing, plans, jobs, careers, press, partners, affiliate` — plus the platform's own brand terms, a maintained impersonation blocklist of well-known brands, and a profanity list. Validated on every slug write, with a migration-safe check for existing rows.

### D.2 Entitlement catalogue (initial values; **limits to be re-derived from measured unit cost per NFR-3.5 after phase 5 load testing**)

| Key | Type | Free | Pro | Studio |
|---|---|---|---|---|
| `portfolios` | limit | 1 | 3 | 10 |
| `storage_bytes` | limit | 250 MB | 5 GB | 25 GB |
| `custom_domain` | feature | ✖ | ✔ (1) | ✔ (10) |
| `premium_themes` | feature | ✖ | ✔ | ✔ |
| `remove_branding` | feature | ✖ | ✔ | ✔ |
| `cv_versions` | limit | 1 | 10 | unlimited |
| `cv_renders_month` | limit | 5 | 100 | 500 |
| `docx_export` | feature | ✖ | ✔ | ✔ |
| `leads_month` | limit | 20 | 500 | unlimited |
| `lead_retention_days` | limit | 90 | 730 | unlimited |
| `analytics_history_days` | limit | 7 | 365 | unlimited |
| `revision_history` | limit | 5 | 50 | unlimited |
| `scheduled_publishing` | feature | ✖ | ✔ | ✔ |
| `preview_links` | limit | 1 active | 10 | unlimited |
| `team_members` | limit | 1 | 1 | 10 |
| `blog_posts` | limit | 10 | unlimited | unlimited |
| `api_access` | feature | ✖ | ✖ | ✔ (phase 6) |
| `ai_credits_month` | limit | 0 | 100 | 500 (phase 6) |

Keys are stable strings; changing a value is a `Plan.entitlements` data edit with no deploy (P-6). Per-account overrides exist for support grants and grandfathering (§7.3).

---

**END OF SOFTWARE DESIGN DOCUMENT — VERSION 3.0 (IMPLEMENTATION-READY)**
