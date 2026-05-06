from __future__ import annotations

from markdown import markdown as render_markdown


def render_markdown_to_html(markdown: str) -> str:
    safe_markdown = (markdown or "").replace("<", "&lt;").replace(">", "&gt;")
    return render_markdown(
        safe_markdown,
        extensions=[
            "extra",
            "fenced_code",
            "sane_lists",
            "tables",
            "nl2br",
        ],
        output_format="html5",
    )
