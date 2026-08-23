from __future__ import annotations

import bleach

# Design doc §24.4: "All rich text sanitized server-side on write with a
# strict allowlist (nh3/bleach): no <script>, no on* handlers, no
# javascript:, no <iframe> except an allowlisted embed set."
# This module implements the bleach variant. If `content` already has an
# equivalent sanitizer (it owns ContentBlock's rich-text payload validation
# per §9), prefer consolidating onto whichever one is canonical rather than
# running two allowlists that can drift apart.

_ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "a", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "blockquote", "code", "pre",
]
_ALLOWED_ATTRS = {"a": ["href", "title", "rel", "target"]}
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(value: str) -> str:
    if not value:
        return value
    return bleach.clean(
        value,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
