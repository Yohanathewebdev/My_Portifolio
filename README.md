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

The Phase 0 test settings use the Compose PostgreSQL and Redis services, so
tests exercise the same database semantics as deployment. Compose also
provides MinIO and MailHog.

Portfolio-owned querysets fail closed unless they are scoped with
`.for_portfolio(portfolio)` or deliberately opened with
`.unscoped_explicit(reason=...)`. Tenant writes use
`PortfolioOwnedModel.objects.create_for_portfolio(portfolio, **fields)`;
administrative or system writes that intentionally bypass tenant scope use
`all_objects`.

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
