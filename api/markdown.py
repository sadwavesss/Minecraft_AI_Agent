from __future__ import annotations

from html import escape


def _render_inline(value: str) -> str:
    text = escape(value or "")
    text = text.replace("**", "\u0000")
    parts = text.split("\u0000")
    if len(parts) > 1:
        rebuilt = []
        for index, part in enumerate(parts):
            rebuilt.append(part)
            if index < len(parts) - 1:
                rebuilt.append("<strong>" if index % 2 == 0 else "</strong>")
        text = "".join(rebuilt)

    text = text.replace("`", "\u0001")
    parts = text.split("\u0001")
    if len(parts) > 1:
        rebuilt = []
        for index, part in enumerate(parts):
            rebuilt.append(part)
            if index < len(parts) - 1:
                rebuilt.append("<code>" if index % 2 == 0 else "</code>")
        text = "".join(rebuilt)

    return text


def render_markdown_to_html(markdown: str) -> str:
    lines = (markdown or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    html_parts: list[str] = []
    paragraph: list[str] = []
    unordered_items: list[str] = []
    ordered_items: list[str] = []
    quote_lines: list[str] = []
    code_lines: list[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        if paragraph:
            html_parts.append(f"<p>{_render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list(tag: str, items: list[str]) -> None:
        if items:
            rendered = "".join(f"<li>{_render_inline(item)}</li>" for item in items)
            html_parts.append(f"<{tag}>{rendered}</{tag}>")
            items.clear()

    def flush_blockquote() -> None:
        if quote_lines:
            rendered = "".join(f"<p>{_render_inline(line)}</p>" for line in quote_lines)
            html_parts.append(f"<blockquote>{rendered}</blockquote>")
            quote_lines.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_list("ul", unordered_items)
        flush_list("ol", ordered_items)
        flush_blockquote()

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            flush_all()
            if in_code_block:
                html_parts.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not stripped:
            flush_all()
            continue

        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            level = min(6, len(stripped) - len(stripped.lstrip("#")))
            flush_all()
            html_parts.append(f"<h{level}>{_render_inline(heading)}</h{level}>")
            continue

        if stripped[:2] in {"- ", "* ", "+ "}:
            flush_paragraph()
            flush_list("ol", ordered_items)
            flush_blockquote()
            unordered_items.append(stripped[2:].strip())
            continue

        ordered_marker = stripped.split(". ", 1)
        if len(ordered_marker) == 2 and ordered_marker[0].isdigit():
            flush_paragraph()
            flush_list("ul", unordered_items)
            flush_blockquote()
            ordered_items.append(ordered_marker[1].strip())
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list("ul", unordered_items)
            flush_list("ol", ordered_items)
            quote_lines.append(stripped[1:].strip())
            continue

        paragraph.append(stripped)

    flush_all()
    if in_code_block:
        html_parts.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")

    return "".join(html_parts)
