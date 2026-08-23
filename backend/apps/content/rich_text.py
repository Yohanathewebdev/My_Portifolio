"""Strict write-time HTML sanitizer for portfolio rich-text fields."""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


ALLOWED_TAGS = {"p", "br", "strong", "em", "u", "s", "ul", "ol", "li", "blockquote", "h2", "h3", "a"}
ALLOWED_ATTRIBUTES = {"a": {"href", "title", "target", "rel"}}
ALLOWED_SCHEMES = {"http", "https", "mailto"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        clean = []
        for name, value in attrs:
            if name not in ALLOWED_ATTRIBUTES.get(tag, set()) or value is None:
                continue
            if name == "href" and urlparse(value).scheme.lower() not in ALLOWED_SCHEMES:
                continue
            if name == "target" and value != "_blank":
                continue
            clean.append(f' {name}="{escape(value, quote=True)}"')
        if tag == "a" and any(name == "target" and value == "_blank" for name, value in attrs):
            clean.append(' rel="noopener noreferrer"')
        self.parts.append(f"<{tag}{''.join(clean)}>")
        if tag != "br":
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in self.open_tags:
            self.parts.append(f"</{tag}>")
            self.open_tags.remove(tag)

    def handle_data(self, data):
        self.parts.append(escape(data))


def sanitize_html(value: str) -> str:
    sanitizer = _Sanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return "".join(sanitizer.parts)
