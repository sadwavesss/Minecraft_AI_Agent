const MAX_DISPLAY = 100;
let ws = null;
let reconnectTimer = null;
let allEntries = [];

// ── Source metadata ────────────────────────────────────────────────────────────
const SOURCE_META = {
    groq:     { label: 'Groq',     color: '#7c3aed' },
    chat:     { label: 'Чат',      color: '#0ea5e9' },
    ollama:   { label: 'Ollama',   color: '#16a34a' },
    fallback: { label: 'Правила', color: '#64748b' },
};

function sourceMeta(source) {
    return SOURCE_META[source] || { label: source, color: '#64748b' };
}

// ── Model info ─────────────────────────────────────────────────────────────────
async function loadModelInfo() {
    try {
        const res = await fetch('/api/rp/models/available');
        const data = await res.json();
        const key = data.current_model;
        const info = data.model_details[key] || {};
        document.getElementById('modelName').textContent = info.name || key;
        const provider = info.provider || key;
        const badge = document.getElementById('modelProvider');
        badge.textContent = provider;
        badge.style.background = sourceMeta(provider).color;
    } catch (e) {
        document.getElementById('modelName').textContent = 'неизвестно';
    }
}

// ── Render ─────────────────────────────────────────────────────────────────────
function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function confidenceBar(conf) {
    const pct = Math.round((conf || 0) * 100);
    const color = pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
    return `<div class="conf-bar-wrap" title="Уверенность: ${pct}%">
        <div class="conf-bar" style="width:${pct}%;background:${color}"></div>
        <span class="conf-label">${pct}%</span>
    </div>`;
}

function renderEntry(entry) {
    const meta = sourceMeta(entry.source);
    const time = formatTime(entry.timestamp);
    const hasPlayerMsg = entry.player_message && entry.player_message.trim();

    return `<div class="response-entry level-${(entry.level || 'info').toLowerCase()}">
        <div class="response-header">
            <span class="response-time">${time}</span>
            <span class="source-badge" style="background:${meta.color}">${meta.label}</span>
            <span class="response-level">${entry.level || 'INFO'}</span>
        </div>
        ${hasPlayerMsg ? `<div class="player-message">
            <span class="player-icon">👤</span>
            <span>${escHtml(entry.player_message)}</span>
        </div>` : ''}
        <div class="ai-response">
            <span class="ai-icon">🤖</span>
            <span>${escHtml(entry.response)}</span>
        </div>
        ${confidenceBar(entry.confidence)}
    </div>`;
}

function escHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function getFilteredEntries() {
    const src = document.getElementById('sourceFilter').value;
    return src ? allEntries.filter(e => e.source === src) : allEntries;
}

function redrawList() {
    const container = document.getElementById('responsesList');
    const filtered = getFilteredEntries();
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">Нет ответов для отображения</div>';
        return;
    }
    container.innerHTML = filtered.slice(0, MAX_DISPLAY).map(renderEntry).join('');
}

function clearDisplay() {
    allEntries = [];
    redrawList();
}

document.getElementById('sourceFilter').addEventListener('change', redrawList);

// ── Load history ───────────────────────────────────────────────────────────────
async function loadHistory() {
    try {
        const res = await fetch('/api/rp/history?limit=100');
        allEntries = await res.json(); // already newest-first
        redrawList();
    } catch (e) {
        console.error('Failed to load history', e);
    }
}

// ── WebSocket ──────────────────────────────────────────────────────────────────
function setWsStatus(ok) {
    const el = document.getElementById('wsIndicator');
    el.className = 'ws-indicator ' + (ok ? 'ws-connected' : 'ws-disconnected');
    el.title = ok ? 'Онлайн: подключено' : 'Онлайн: переподключение…';
}

function connectWebSocket() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/api/rp/ws`);

    ws.onopen = () => setWsStatus(true);

    ws.onmessage = (event) => {
        const entry = JSON.parse(event.data);
        allEntries.unshift(entry); // prepend newest
        if (allEntries.length > MAX_DISPLAY * 2) allEntries.length = MAX_DISPLAY;
        redrawList();
    };

    ws.onclose = () => {
        setWsStatus(false);
        reconnectTimer = setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

// ── Init ───────────────────────────────────────────────────────────────────────
loadModelInfo();
loadHistory();
connectWebSocket();
