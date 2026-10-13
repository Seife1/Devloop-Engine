"""Pure, dependency-free Markdown renderer with mandatory HTML escaping.

Threat model:
1. All input text is escaped with html.escape FIRST, preventing any raw HTML injection.
2. Only http:// and https:// URLs are allowed in links with rel="noopener noreferrer".
3. No images, no javascript:/data: URLs, no raw HTML allowed.
"""

from __future__ import annotations

import html
import re
import urllib.parse

_CODE_TOKEN_PATTERN = re.compile(r"\x00CODE_(\d+)\x00")


def _is_safe_http_url(url: str) -> bool:
    """Validate that a URL strictly uses http or https scheme."""
    cleaned = url.strip()
    if not (cleaned.lower().startswith("http://") or cleaned.lower().startswith("https://")):
        return False
    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return True


def _render_inline(text: str) -> str:
    """Render inline markdown elements: code, bold, italic, and safe links."""
    # 1. Stash inline code so its contents are never affected by bold, italic, or links
    code_snippets: list[str] = []

    def _stash_code(match: re.Match[str]) -> str:
        code_snippets.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE_{len(code_snippets) - 1}\x00"

    text = re.sub(r"`([^`\n]+)`", _stash_code, text)

    # 2. Images: explicitly disallowed by spec ("No images"). Replace with alt text or drop
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)

    # 3. Safe links: only http/https allowed
    def _replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2).strip()
        # Unescape quotes in url that might have been escaped by html.escape
        unescaped_url = html.unescape(url)
        if _is_safe_http_url(unescaped_url):
            safe_href = html.escape(unescaped_url, quote=True)
            return f'<a href="{safe_href}" rel="noopener noreferrer">{label}</a>'
        # Unsafe link (javascript:, data:, file:, relative): strip the link and return label
        return label

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _replace_link, text)

    # 4. Bold: **text** or __text__
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_\n]+)__", r"<strong>\1</strong>", text)

    # 5. Italic: *text* or _text_
    text = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", text)

    # 6. Restore inline code
    def _restore_code(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return code_snippets[idx]

    return _CODE_TOKEN_PATTERN.sub(_restore_code, text)


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_table_divider(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [c.strip() for c in stripped[1:-1].split("|")]
    return all(re.match(r"^:?-+:?$", c) for c in cells if c)


def render_markdown(text: str) -> str:
    """Render markdown text to safe HTML without external dependencies.

    Mandatory rules:
    - Escapes all HTML first.
    - Supports headings, paragraphs, bold/italic, inline code, fenced code,
      ordered/unordered lists, blockquotes, simple tables, and safe http/https links.
    - No images, no raw HTML, no javascript:/data: URLs.
    """
    if not text:
        return ""

    # ESCAPE ALL HTML FIRST
    escaped = html.escape(text)
    lines = escaped.splitlines()

    output: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            lang_match = re.match(r"^```(\w*)", stripped)
            lang = lang_match.group(1) if lang_match else ""
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n and lines[i].strip().startswith("```"):
                i += 1
            code_content = "\n".join(code_lines)
            cls_attr = f' class="language-{lang}"' if lang else ""
            output.append(f"<pre><code{cls_attr}>{code_content}</code></pre>")
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = _render_inline(heading_match.group(2).strip())
            output.append(f"<h{level}>{heading_text}</h{level}>")
            i += 1
            continue

        # Blockquote (lines starting with &gt;)
        if stripped.startswith("&gt;"):
            bq_lines: list[str] = []
            while i < n and lines[i].strip().startswith("&gt;"):
                raw_bq = lines[i].strip()
                # strip leading &gt; and optional space
                if raw_bq.startswith("&gt; "):
                    bq_lines.append(raw_bq[5:])
                elif raw_bq.startswith("&gt;"):
                    bq_lines.append(raw_bq[4:])
                i += 1
            inner_md = "\n".join(bq_lines)
            rendered_inner = render_markdown(html.unescape(inner_md))
            output.append(f"<blockquote>{rendered_inner}</blockquote>")
            continue

        # Table
        if (
            _is_table_row(line)
            and i + 1 < n
            and _is_table_divider(lines[i + 1])
        ):
            header_cells = [c.strip() for c in stripped[1:-1].split("|")]
            i += 2  # skip header and divider
            rows: list[list[str]] = []
            while i < n and _is_table_row(lines[i]):
                row_cells = [c.strip() for c in lines[i].strip()[1:-1].split("|")]
                rows.append(row_cells)
                i += 1

            th_html = "".join(f"<th>{_render_inline(c)}</th>" for c in header_cells)
            rows_html: list[str] = []
            for row in rows:
                td_html = "".join(f"<td>{_render_inline(c)}</td>" for c in row)
                rows_html.append(f"<tr>{td_html}</tr>")
            tbody_html = "".join(rows_html)
            output.append(
                f"<table><thead><tr>{th_html}</tr></thead><tbody>{tbody_html}</tbody></table>"
            )
            continue

        # Unordered list
        ul_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if ul_match:
            items: list[str] = []
            while i < n:
                item_match = re.match(r"^[-*]\s+(.*)$", lines[i].strip())
                if item_match:
                    items.append(_render_inline(item_match.group(1).strip()))
                    i += 1
                elif lines[i].strip() and not lines[i].strip().startswith(("#", "```", "&gt;")):
                    # Continuation line for list item
                    if items:
                        items[-1] += " " + _render_inline(lines[i].strip())
                    i += 1
                else:
                    break
            lis_html = "".join(f"<li>{it}</li>" for it in items)
            output.append(f"<ul>{lis_html}</ul>")
            continue

        # Ordered list
        ol_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ol_match:
            items = []
            while i < n:
                item_match = re.match(r"^\d+\.\s+(.*)$", lines[i].strip())
                if item_match:
                    items.append(_render_inline(item_match.group(1).strip()))
                    i += 1
                elif lines[i].strip() and not lines[i].strip().startswith(("#", "```", "&gt;")):
                    if items:
                        items[-1] += " " + _render_inline(lines[i].strip())
                    i += 1
                else:
                    break
            lis_html = "".join(f"<li>{it}</li>" for it in items)
            output.append(f"<ol>{lis_html}</ol>")
            continue

        # Paragraph
        para_lines: list[str] = []
        while (
            i < n
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", "```", "&gt;"))
            and not re.match(r"^[-*]\s+", lines[i].strip())
            and not re.match(r"^\d+\.\s+", lines[i].strip())
            and not (_is_table_row(lines[i]) and i + 1 < n and _is_table_divider(lines[i + 1]))
        ):
            para_lines.append(lines[i].strip())
            i += 1
        para_text = " ".join(para_lines)
        output.append(f"<p>{_render_inline(para_text)}</p>")

    return "\n".join(output)
