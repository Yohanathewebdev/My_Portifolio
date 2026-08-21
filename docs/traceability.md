# Requirements traceability

| Requirement | Phase 0 artifact |
|---|---|
| §5.2 core contract | `backend/apps/core/models.py` |
| §20.3 pagination | `backend/apps/core/pagination.py` |
| §20.4 error envelope | `backend/apps/core/exceptions.py` |
| §24.2 tenant isolation | `backend/apps/core/managers.py`, `scoping.py`, and tests |
| §24.6 audit trail | `backend/apps/core/models.py`, `audit.py` |
| §26 database standards | UUID base model, explicit FK deletion, indexes, BigAutoField audit |
| §27 testing | `backend/apps/core/tests/`, coverage gate in `pyproject.toml` |
| §28.1 observability | correlation middleware and PII scrub filter |
| §28.3 health | `backend/apps/core/health.py` |
| §29 deployment/CI | `infra/docker-compose.yml`, `.github/workflows/ci.yml` |
| §32 Phase 0 DoD | scoping fixture test demonstrates an intentional violation |
| §6 tenancy and roles | `backend/apps/accounts/`, `backend/apps/core/permissions.py` |
| §7 billing and entitlements | `backend/apps/billing/`, billing seed migration, entitlement tests |
| §24.3 scoped authorization | account/portfolio resolvers and scoped API viewsets |
