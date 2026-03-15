let ws = null;
let reconnectTimer = null;
const MAX_DISPLAY_LOGS = 50;  // Limit to prevent page overflow

async function loadLogs() {
    const level = document.getElementById('levelFilter').value;
    const limit = document.getElementById('limitInput').value;
    
    const url = `/api/logs/?limit=${limit}${level ? `&level=${level}` : ''}`;
    const response = await fetch(url);
    const logs = await response.json();
    
    displayLogs(logs);
}

function truncateMessage(message, maxLength = 120) {
    if (typeof message !== 'string') return '';
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
}

function displayLogs(logs) {
    const container = document.getElementById('logsList');
    // Limit to most recent logs to prevent page overflow
    const displayLogs = logs.slice(-MAX_DISPLAY_LOGS);
    
    container.innerHTML = displayLogs.map(log => `
        <div class="log-entry level-${log.level.toLowerCase()}">
            <div class="log-header">
                <span class="timestamp">${new Date(log.timestamp).toLocaleString()}</span>
                <span class="level">${log.level}</span>
            </div>
            <div class="log-message" title="${log.message}">${truncateMessage(log.message, 120)}</div>
            ${log.threats_detected ? 
                `<div class="threats">Угрозы: ${log.threats_detected.map(t => t.type).join(', ')}</div>` : ''}
            ${log.confidence ? `<div class="confidence">Точность: ${(log.confidence*100).toFixed(1)}%</div>` : ''}
        </div>
    `).join('');
}

// WebSocket для real-time
function connectWebSocket() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${proto}://${window.location.host}/api/logs/ws`;
    ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
        const log = JSON.parse(event.data);
        prependLog(log);
    };

    ws.onclose = () => {
        reconnectTimer = setTimeout(connectWebSocket, 1000);
    };

    ws.onerror = () => {
        try { ws.close(); } catch (e) {}
    };
}

function prependLog(log) {
    const container = document.getElementById('logsList');
    const entry = document.createElement('div');
    entry.className = `log-entry level-${log.level.toLowerCase()}`;
    entry.innerHTML = `
        <div class="log-header">
            <span class="timestamp">${new Date(log.timestamp).toLocaleString()}</span>
            <span class="level">${log.level}</span>
        </div>
        <div class="log-message" title="${log.message}">${truncateMessage(log.message, 120)}</div>
    `;
    container.insertBefore(entry, container.firstChild);
    
    // Remove old logs if too many (keep only MAX_DISPLAY_LOGS)
    while (container.children.length > MAX_DISPLAY_LOGS) {
        container.removeChild(container.lastChild);
    }
}

loadLogs();
connectWebSocket();
