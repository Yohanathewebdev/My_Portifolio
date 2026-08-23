from apps.content.rich_text import sanitize_html


def test_rich_text_sanitizer_removes_scripts_event_handlers_and_bad_links():
    value = '<p onclick="steal()">Safe <script>alert(1)</script><a href="javascript:alert(1)">bad</a><a href="https://example.com" target="_blank">good</a></p>'

    assert sanitize_html(value) == (
        '<p>Safe alert(1)<a>bad</a><a href="https://example.com" target="_blank" '
        'rel="noopener noreferrer">good</a></p>'
    )
