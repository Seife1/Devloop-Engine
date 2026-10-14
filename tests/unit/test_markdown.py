from __future__ import annotations

import random
import re
import string

from learnloop.dashboard.markdown import render_markdown


def test_markdown_escapes_raw_html():
    raw = "<script>alert('xss')</script><b>bold</b>"
    rendered = render_markdown(raw)
    assert "<script>" not in rendered
    assert "<b>" not in rendered
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in rendered or "&lt;script&gt;" in rendered
    assert "&lt;b&gt;bold&lt;/b&gt;" in rendered


def test_markdown_strips_unsafe_links():
    raw = "[evil link](javascript:alert(1)) and [data link](data:text/html,evil)"
    rendered = render_markdown(raw)
    assert 'href="javascript:' not in rendered
    assert 'href="data:' not in rendered
    assert "evil link" in rendered
    assert "data link" in rendered


def test_markdown_allows_http_and_https_links():
    raw = "[Google](https://google.com) and [Insecure](http://insecure.org)"
    rendered = render_markdown(raw)
    assert '<a href="https://google.com" rel="noopener noreferrer">Google</a>' in rendered
    assert '<a href="http://insecure.org" rel="noopener noreferrer">Insecure</a>' in rendered


def test_markdown_headings_and_paragraphs():
    raw = "# Title\n\n## Subtitle\n\nThis is a paragraph with **bold** and *italic*."
    rendered = render_markdown(raw)
    assert "<h1>Title</h1>" in rendered
    assert "<h2>Subtitle</h2>" in rendered
    assert "<p>This is a paragraph with <strong>bold</strong> and <em>italic</em>.</p>" in rendered


def test_markdown_inline_and_fenced_code():
    raw = "Here is `some <code />`.\n\n```python\ndef foo():\n    return 42\n```"
    rendered = render_markdown(raw)
    assert "<code>some &lt;code /&gt;</code>" in rendered
    assert '<pre><code class="language-python">def foo():\n    return 42</code></pre>' in rendered


def test_markdown_lists():
    ul_raw = "- Item 1\n- Item 2\n- Item 3"
    ul_rendered = render_markdown(ul_raw)
    assert "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>" in ul_rendered

    ol_raw = "1. First\n2. Second"
    ol_rendered = render_markdown(ol_raw)
    assert "<ol><li>First</li><li>Second</li></ol>" in ol_rendered


def test_markdown_tables():
    raw = "| Col 1 | Col 2 |\n| --- | --- |\n| Val 1 | Val 2 |"
    rendered = render_markdown(raw)
    assert (
        "<table><thead><tr><th>Col 1</th><th>Col 2</th></tr></thead>"
        "<tbody><tr><td>Val 1</td><td>Val 2</td></tr></tbody></table>"
    ) in rendered


def test_markdown_blockquotes():
    raw = "> This is a quote\n> Second line"
    rendered = render_markdown(raw)
    assert "<blockquote>" in rendered
    assert "This is a quote" in rendered


def test_markdown_adversarial_schemes_and_obfuscation():
    cases = [
        "[x](javascript:alert(1))",
        "[x](JaVaScRiPt:alert(1))",
        "[x](java\tscript:alert(1))",
        "[x](java\nscript:alert(1))",
        "[x](java\rscript:alert(1))",
        "[x](&#106;avascript:alert(1))",
        "[x](&#74;avascript:alert(1))",
        "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
        "[x](vbscript:msgbox(1))",
        "[x](file:///etc/passwd)",
    ]
    for c in cases:
        out = render_markdown(c)
        assert "<a href=" not in out, f"Unsafe scheme permitted in {c}: got {out}"
        assert "x" in out


def test_markdown_links_with_quotes_and_angle_brackets():
    cases = [
        '[x](https://example.com" onclick="alert(1))',
        "[x](https://example.com' onfocus='alert(1))",
        "[x](https://example.com/<script>alert(1)</script>)",
        "[x](https://example.com/>)",
        "[x](https://example.com/<)",
        '[<script>alert("text")</script>](https://example.com)',
        '[<img src=x onerror=alert(1)>](https://example.com)',
    ]
    for c in cases:
        out = render_markdown(c)
        # Any raw script or event handler must never survive unescaped
        assert "<script>" not in out
        assert "<img" not in out
        assert "onclick=" not in out
        assert "onfocus=" not in out


def test_markdown_nested_emphasis():
    raw1 = "**bold *italic* bold**"
    out1 = render_markdown(raw1)
    assert "<strong>bold <em>italic</em> bold</strong>" in out1

    raw2 = "*italic **bold** italic*"
    out2 = render_markdown(raw2)
    assert "<em>italic <strong>bold</strong> italic</em>" in out2


def test_markdown_unclosed_code_fence():
    raw = "```python\ndef broken():\n    pass\n# unclosed"
    out = render_markdown(raw)
    assert '<pre><code class="language-python">' in out
    assert "def broken():" in out
    assert "</code></pre>" in out


def test_markdown_raw_img_and_svg_payloads():
    raw = '<img src=x onerror="alert(1)">\n<svg onload="alert(1)">'
    out = render_markdown(raw)
    assert "<img" not in out
    assert "<svg" not in out
    assert "&lt;img" in out
    assert "&lt;svg" in out


def test_markdown_100kb_input():
    # 100 KB text with diverse markdown constructs
    chunk = "# Section\n\nParagraph with **bold** and `code` and [link](https://safe.org).\n\n"
    large_input = chunk * (100_000 // len(chunk) + 1)
    assert len(large_input) >= 100_000
    out = render_markdown(large_input)
    assert len(out) > 0
    assert "<h1>Section</h1>" in out
    assert '<a href="https://safe.org"' in out


def test_markdown_randomized_fuzz_allowed_tags_only():
    allowed_tags = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "code",
        "pre",
        "strong",
        "em",
        "ul",
        "ol",
        "li",
        "blockquote",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
    }

    alphabet = string.ascii_letters + string.digits + "<>/\"'`;:=[]()#*-_\n\t\\ "
    rng = random.Random(42)

    for _ in range(50):
        length = rng.randint(5, 500)
        random_str = "".join(rng.choice(alphabet) for _ in range(length))
        out = render_markdown(random_str)

        # Extract all HTML tag names
        found_tags = re.findall(r"<([a-zA-Z0-9]+)[^>]*>", out)
        for t in found_tags:
            tag_lower = t.lower()
            assert tag_lower in allowed_tags, (
                f"Disallowed tag <{tag_lower}> generated from input {random_str!r}: output {out!r}"
            )
