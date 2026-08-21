# Portfolio CMS

Portfolio CMS is a multi-professional, multi-tenant platform for creating
structured portfolios and publishing fast, server-rendered public sites. The
CMS API and public renderer share one Django domain layer; PostgreSQL stores
source data, Redis handles cache and asynchronous work, and S3-compatible
storage holds media and generated artifacts.

## Local setup

```bash
cp .env.example .env
uv sync
make up
make test
make server
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

The Phase 0 test settings use an in-memory SQLite database, while Compose
provides the local PostgreSQL, Redis, MinIO, and MailHog services used by later
phases.

## Checks

```bash
make lint
make format
make typecheck
make imports
make test
make migrations
make schema
```

The scoping meta-test rejects every registered view that is not a
`PortfolioScopedViewSet`, a declared public view, or an allowlisted
infrastructure endpoint with a written reason.

## Layout

* `backend/config/` — Django project and split settings
* `backend/apps/core/` — Phase 0 models and guardrails
* `docs/` — design document, ADRs, and traceability
* `infra/` — local dependency services
* `.github/workflows/` — CI gates
