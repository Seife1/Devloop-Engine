from __future__ import annotations

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
    assert "<table><thead><tr><th>Col 1</th><th>Col 2</th></tr></thead><tbody><tr><td>Val 1</td><td>Val 2</td></tr></tbody></table>" in rendered


def test_markdown_blockquotes():
    raw = "> This is a quote\n> Second line"
    rendered = render_markdown(raw)
    assert "<blockquote>" in rendered
    assert "This is a quote" in rendered
