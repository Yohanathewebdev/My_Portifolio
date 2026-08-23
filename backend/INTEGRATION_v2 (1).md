# projects app — v2, rebuilt against apps.content (the real precedent)

This supersedes the original INTEGRATION.md. The first version guessed at
`ProjectViewSet`'s base class because `core/views.py` was the only
reference available. Once `apps/content/views.py` and
`apps/content/models.py` were shared, several guesses turned out wrong —
this version fixes them by mirroring `ArticleViewSet`/`Article` directly,
since that's real, shipped code solving the identical problem.

## What changed from v1

**`services.py` and `selectors.py` are deprecated** (renamed to
`.DEPRECATED`, not deleted). `apps.content` has no equivalent layer —
`ArticleViewSet` calls `model.objects.create_for_portfolio(...)` and
`article.publish()` directly. The design doc's §5.3 wants a services/
selectors split; the real codebase doesn't have one for `content`. I
matched the real codebase for consistency. If you'd rather `projects` be
the first app to introduce that layer properly, say so and I'll restore
it — but doing it silently while `content` doesn't follow the same
pattern would leave the codebase with two conflicting conventions.

**`cover_image` is now a real FK**, not a URL placeholder.
`MediaAsset` already exists inside `apps.content` — I didn't know that
until you shared `content/models.py`. This is a genuine fix, not a style
change.

**Added optimistic concurrency (`version` field + `ConflictError`)**,
matching `Article` exactly. `ProjectViewSet.update()` now requires an
`If-Match` header or a `version` field in the request body, and returns
409 via `apps.core.exceptions.ConflictError` on mismatch. This didn't
exist in v1 at all — a real gap, now closed for `projects`, still open
platform-wide for anything that isn't `content` or `projects`.

**`ProjectViewSet` now extends `AccountScopedViewSet`**, resolving the
portfolio the same way `ContentViewSet` does
(`Portfolio.objects.for_accounts(self.get_accounts()).get(pk=...)`),
instead of the untested `PortfolioScopedViewSet` guess from v1.

**Publish/unpublish are model methods**, not service functions —
`project.publish(actor=...)`, matching `article.publish()`'s shape.

## New thing surfaced, not yet resolved — read this before you migrate

**`Project.clean()` blocks a `cover_image` from a different portfolio**;
`Project.save()` calls `self.clean()` to enforce it. `Article.save()`
doesn't call `clean()` at all. This is a deliberate inconsistency, not an
oversight: the serializer's `cover_image` field has to use
`MediaAsset.all_objects` (the *unscoped* manager) to even build a
queryset, since a portfolio-scoped queryset can't be constructed at
field-definition time with no request in scope yet. That means without
the model-level check, nothing stops a payload from attaching another
portfolio's media asset to a project — same class of bug as SEC-8, just
one level removed. Confirm this doesn't already exist somewhere for
`content` (does anything stop a cross-portfolio `MediaAsset` id in
`ArticleSerializer`? I haven't seen that serializer) — if `content` has
the same hole, it's worth fixing there too, not just here.

**Audit logging on publish is real for `projects`, absent for
`content`.** `project.publish()`/`unpublish()` call
`apps.core.audit.record_audit()`. `article.publish()` does not call it
at all, and nothing in `ContentViewSet` does either, based on what's been
shared. Two possibilities: (a) `content`'s audit trail is missing — a
real gap against §24.6 — or (b) it's handled elsewhere, e.g. a
`post_save` signal watching for `status` transitions, which I haven't
seen. Worth checking `apps/content/signals.py` or similar before
assuming either app is "the correct one." I erred toward including the
audit call because the design doc requires it and it's cheap; delete it
from `Project.publish()`/`unpublish()` if it turns out to be redundant.

**`permission_classes = [CreateEditPermission]` applies to every action**,
including `list`/`retrieve` — mirrors `ContentViewSet` exactly. This
means viewer-role users can't read drafts through this endpoint at all,
despite `ROLE_MATRIX` having a `"read_draft"` row that would permit it
for editors/viewers. `ArticleViewSet` has the identical gap. Not
introduced here — surfaced here. Whether to split read vs. write
permissions per-action is a decision worth making once, applied to both
apps, rather than each new content-type app quietly copying the gap
forward.

## Steps to integrate

1. Files already in place under `apps/projects/` and `apps/core/` from
   the previous PowerShell run — only these five changed:
   - `apps/projects/models.py`
   - `apps/projects/serializers.py`
   - `apps/projects/views.py`
   - `apps/projects/tests/test_models.py`
   - `apps/projects/tests/test_api.py`
   - (`services.py`, `selectors.py` renamed to `.DEPRECATED` — delete
     them once you're comfortable, or restore if you want that layer)
2. `apps/core/mixins.py` (`PublishableMixin`) is now **unused** — `Project`
   no longer inherits it, since `content`'s convention is plain fields on
   the model, not a shared mixin. Safe to leave in place for a future
   app, or delete — your call.
3. Run `python manage.py makemigrations projects` again — the model
   shape changed materially (new `cover_image` FK, `version` field,
   dropped `cover_image_url`). If you already ran migrations from v1,
   you'll get a migration that alters the table; check it before
   applying if there's any real data in it yet.
4. Confirm `apps.core.exceptions.ConflictError` renders as HTTP 409 in
   your exception handler — I've only seen it imported and raised in
   `content/views.py`, not the handler that turns it into a response.
