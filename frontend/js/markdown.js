(function () {
    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderInline(value) {
        let html = escapeHtml(value);
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        return html;
    }

    function flushParagraph(buffer, html) {
        if (!buffer.length) {
            return;
        }
        html.push(`<p>${renderInline(buffer.join(' '))}</p>`);
        buffer.length = 0;
    }

    function flushList(type, items, html) {
        if (!items.length) {
            return;
        }
        html.push(`<${type}>${items.map(item => `<li>${renderInline(item)}</li>`).join('')}</${type}>`);
        items.length = 0;
    }

    function flushBlockquote(buffer, html) {
        if (!buffer.length) {
            return;
        }
        html.push(`<blockquote>${buffer.map(line => `<p>${renderInline(line)}</p>`).join('')}</blockquote>`);
        buffer.length = 0;
    }

    function renderFallback(markdown) {
        const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
        const html = [];
        const paragraph = [];
        const unorderedList = [];
        const orderedList = [];
        const blockquote = [];
        const codeBlock = [];
        let inCodeBlock = false;

        function flushAll() {
            flushParagraph(paragraph, html);
            flushList('ul', unorderedList, html);
            flushList('ol', orderedList, html);
            flushBlockquote(blockquote, html);
        }

        for (const rawLine of lines) {
            const line = rawLine || '';

            if (line.trim().startsWith('```')) {
                flushAll();
                if (inCodeBlock) {
                    html.push(`<pre><code>${escapeHtml(codeBlock.join('\n'))}</code></pre>`);
                    codeBlock.length = 0;
                    inCodeBlock = false;
                } else {
                    inCodeBlock = true;
                }
                continue;
            }

            if (inCodeBlock) {
                codeBlock.push(line);
                continue;
            }

            const trimmed = line.trim();
            if (!trimmed) {
                flushAll();
                continue;
            }

            const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
            if (headingMatch) {
                flushAll();
                const level = headingMatch[1].length;
                html.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
                continue;
            }

            const unorderedMatch = trimmed.match(/^[-*+]\s+(.+)$/);
            if (unorderedMatch) {
                flushParagraph(paragraph, html);
                flushList('ol', orderedList, html);
                flushBlockquote(blockquote, html);
                unorderedList.push(unorderedMatch[1]);
                continue;
            }

            const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/);
            if (orderedMatch) {
                flushParagraph(paragraph, html);
                flushList('ul', unorderedList, html);
                flushBlockquote(blockquote, html);
                orderedList.push(orderedMatch[1]);
                continue;
            }

            const quoteMatch = trimmed.match(/^>\s?(.*)$/);
            if (quoteMatch) {
                flushParagraph(paragraph, html);
                flushList('ul', unorderedList, html);
                flushList('ol', orderedList, html);
                blockquote.push(quoteMatch[1]);
                continue;
            }

            paragraph.push(trimmed);
        }

        flushAll();
        if (inCodeBlock) {
            html.push(`<pre><code>${escapeHtml(codeBlock.join('\n'))}</code></pre>`);
        }
        return html.join('');
    }

    window.renderMarkdown = function renderMarkdown(markdown) {
        if (window.marked && typeof window.marked.parse === 'function') {
            return window.marked.parse(markdown || '');
        }
        return renderFallback(markdown);
    };
})();
