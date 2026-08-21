from __future__ import annotations

RESERVED_SLUGS = frozenset(
    """
    www app api admin staff support help docs blog mail smtp imap ftp cdn static assets media
    img images files download downloads status dashboard login logout register signup signin
    auth oauth account accounts billing pay payment checkout invoice security privacy terms legal
    dmca abuse postmaster hostmaster webmaster noreply no-reply test staging dev demo preview
    sitemap robots feed rss well-known p portfolio portfolios cv resume theme themes new edit
    delete settings me you us about contact pricing plans jobs careers press partners affiliate
    """.split()
)


def validate_reserved_slug(slug: str) -> None:
    normalized = slug.strip().lower()
    if normalized in RESERVED_SLUGS:
        raise ValueError(f"'{slug}' is reserved")
