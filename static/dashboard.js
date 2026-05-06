// Global State
let ws = null;
let autoScroll = true;
let recipes = [];
let currentPage = 'dashboard';

function getChallengeStatusLabel(status) {
    const labels = {
        active: 'активен',
        completed: 'выполнен',
        rewarded: 'награда выдана',
        cancelled: 'отменён'
    };
    return labels[status] || status || 'неизвестно';
}

function getGoalTypeLabel(goalType) {
    const labels = {
        kill: 'Убей',
        collect: 'Собери'
    };
    return labels[goalType] || goalType || 'Цель';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    connectWebSocket();
    loadInitialData();
    loadDashboardSettings();
    setupEventListeners();
    const initialPage = window.location.hash ? window.location.hash.slice(1) : 'dashboard';
    switchPage(initialPage);
});

// Navigation Setup
function setupNavigation() {
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.getAttribute('data-page');
            switchPage(page);
        });
    });
}

// Switch Pages
function switchPage(page) {
    const targetPage = document.getElementById(`${page}-page`) ? page : 'dashboard';
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`${targetPage}-page`).classList.add('active');
    
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-page="${targetPage}"]`).classList.add('active');
    
    currentPage = targetPage;
    window.history.replaceState(null, '', `#${targetPage}`);
    
    // Load page-specific data
    if (targetPage === 'logs') loadLogs();
    else if (targetPage === 'challenges') loadChallenges();
    else if (targetPage === 'inventory') loadInventory();
    else if (targetPage === 'crafting') loadCrafting();
    else if (targetPage === 'dashboard') updateDashboard();
    else if (targetPage === 'settings') loadDashboardSettings();
}

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/api/logs/ws`);
    
    ws.onopen = () => {
        updateConnectionStatus('Подключено', true);
    };
    
    ws.onmessage = (event) => {
        const log = JSON.parse(event.data);
        addLogEntry(log);
        updateSidebar();
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('Ошибка', false);
    };
    
    ws.onclose = () => {
        updateConnectionStatus('Отключено', false);
        setTimeout(connectWebSocket, 3000);
    };
}

function updateConnectionStatus(text, connected) {
    document.getElementById('status-text').textContent = text;
    const dot = document.querySelector('.status-dot');
    dot.style.background = connected ? '#76c043' : '#c41e3a';
}

// Load Initial Data
async function loadInitialData() {
    try {
        await Promise.all([
            loadPlayerState(),
            loadChallenges(),
            loadRecipes()
        ]);
        updateDashboard();
    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

// Load Player State
async function loadPlayerState() {
    try {
        const response = await fetch('/api/player-state/');
        const state = await response.json();
        
        const kills = state.kill_total || Object.values(state.kill_counts || {}).reduce((a, b) => a + b, 0);
        document.getElementById('total-kills').textContent = kills;
        document.getElementById('dashboard-kills').textContent = kills;
        
        const inventoryCount = Object.values(state.inventory?.counts || {}).reduce((a, b) => a + b, 0);
        document.getElementById('inventory-count').textContent = inventoryCount;
    } catch (error) {
        console.error('Error loading player state:', error);
    }
}

// Load Logs
async function loadLogs() {
    try {
        const response = await fetch('/api/logs/');
        const logs = await response.json();
        
        const logsList = document.getElementById('logs-list');
        logsList.innerHTML = '';
        
        logs.reverse().forEach(log => addLogEntry(log, logsList));
        
        if (autoScroll) {
            logsList.scrollTop = logsList.scrollHeight;
        }
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

function addLogEntry(log, container = null) {
    if (!container) {
        container = document.getElementById('logs-list');
        if (!container) return;
    }
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${log.level || 'INFO'}`;
    
    const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '—';
    const message = log.message || log.event_type || 'Неизвестное событие';
    
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-level ${log.level || 'INFO'}">${log.level || 'INFO'}</span>
        <span class="log-message">${message}</span>
    `;
    
    container.appendChild(entry);
    
    if (autoScroll && container === document.getElementById('logs-list')) {
        container.parentElement.scrollTop = container.parentElement.scrollHeight;
    }
}

// Load Challenges
async function loadChallenges() {
    try {
        const response = await fetch('/api/challenges/');
        const data = await response.json();
        
        const active = data.active || data.active_challenge;
        const history = data.history || data.completed || [];
        
        // Update sidebar
        const preview = document.getElementById('active-challenge');
        if (active) {
            preview.innerHTML = `
                <div class="challenge-title">${active.title || 'Без названия'}</div>
                <div class="challenge-progress">
                    Прогресс: ${active.progress_count || 0}/${active.goal_count || 1}
                </div>
            `;
        } else {
            preview.innerHTML = '<p class="empty-state">Сейчас активного челленджа нет</p>';
        }
        
        // Update detail page
        const detail = document.getElementById('active-challenge-detail');
        if (active) {
            const rewardHint = active.status === 'completed' && active.reward_status === 'failed'
                ? `<small>Автовыдача не удалась: ${active.reward_issue_error || 'неизвестная ошибка'}</small>`
                : '<small>Награда будет выдана автоматически после выполнения.</small>';
            detail.innerHTML = `
                <div class="challenge-item">
                    <div class="challenge-title">${active.title || 'Челлендж без названия'}</div>
                    <p>${getGoalTypeLabel(active.goal_type)} ${active.goal_target_name || active.goal_target_id} x${active.goal_count}. Награда: ${active.reward_item_name || active.reward_item_id} x${active.reward_count || 1}.</p>
                    <div class="challenge-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${(active.progress_count || 0) / (active.goal_count || 1) * 100}%"></div>
                        </div>
                        <small>Прогресс: ${active.progress_count || 0}/${active.goal_count || 1}</small>
                    </div>
                    <div class="challenge-actions">
                        ${active.status === 'active' ? `
                            <button class="btn btn-secondary" onclick="cancelChallenge('${active.id}')">Отменить</button>
                        ` : ''}
                    </div>
                    ${rewardHint}
                </div>
            `;
        } else {
            detail.innerHTML = '<p class="empty-state">Сейчас активного челленджа нет. Награды за завершённые челленджи выдаются автоматически.</p>';
        }
        
        // Update history
        const historyEl = document.getElementById('challenges-history');
        if (history.length > 0) {
            historyEl.innerHTML = history.slice(0, 10).map(c => `
                <div class="challenge-item">
                    <div class="challenge-title">${c.title || 'Челлендж'}</div>
                    <small>Статус: ${getChallengeStatusLabel(c.status)}</small>
                </div>
            `).join('');
        } else {
            historyEl.innerHTML = '<p class="empty-state">История челленджей пока пуста</p>';
        }
    } catch (error) {
        console.error('Error loading challenges:', error);
    }
}

// Load Inventory
async function loadInventory() {
    try {
        const response = await fetch('/api/player-state/inventory');
        const payload = await response.json();
        const inventory = payload.inventory || {};
        
        // Main inventory
        const invGrid = document.getElementById('inventory-items');
        const countEntries = inventory.count_entries || Object.entries(inventory.counts || {}).map(([id, count]) => ({ id, display_name: id, count }));
        if (countEntries.length > 0) {
            invGrid.innerHTML = countEntries.map((entry) => `
                <div class="inventory-slot">
                    <div class="inventory-slot-item" title="${entry.display_name || entry.id}">${entry.display_name || entry.id}</div>
                    <div class="inventory-slot-count">×${entry.count}</div>
                </div>
            `).join('');
        } else {
            invGrid.innerHTML = '<p class="empty-state">Предметов нет</p>';
        }
        
        // Armor
        const armorGrid = document.getElementById('armor-items');
        const armor = inventory.armor || [];
        if (armor.length > 0) {
            armorGrid.innerHTML = armor.map(item => `
                <div class="inventory-slot">
                    <div class="inventory-slot-item" title="${item.display_name || item.item_id || 'Неизвестный предмет'}">${item.display_name || item.item_id || 'Неизвестный предмет'}</div>
                </div>
            `).join('');
        } else {
            armorGrid.innerHTML = '<p class="empty-state">Броня не надета</p>';
        }
        
        // Hotbar
        const hotbarGrid = document.getElementById('hotbar-items');
        const hotbar = inventory.hotbar || [];
        if (hotbar.length > 0) {
            hotbarGrid.innerHTML = hotbar.map(item => `
                <div class="inventory-slot">
                    <div class="inventory-slot-item" title="${item.display_name || item.item_id || 'Неизвестный предмет'}">${item.display_name || item.item_id || 'Неизвестный предмет'}</div>
                </div>
            `).join('');
        } else {
            hotbarGrid.innerHTML = '<p class="empty-state">Хотбар пуст</p>';
        }
        
        // Offhand
        const offhandGrid = document.getElementById('offhand-items');
        const offhand = inventory.offhand || [];
        if (offhand.length > 0) {
            offhandGrid.innerHTML = offhand.map(item => `
                <div class="inventory-slot">
                    <div class="inventory-slot-item" title="${item.display_name || item.item_id || 'Неизвестный предмет'}">${item.display_name || item.item_id || 'Неизвестный предмет'}</div>
                </div>
            `).join('');
        } else {
            offhandGrid.innerHTML = '<p class="empty-state">Левая рука пуста</p>';
        }
    } catch (error) {
        console.error('Error loading inventory:', error);
    }
}

// Load Crafting Recipes
async function loadCrafting() {
    try {
        const response = await fetch('/api/recipes');
        const data = await response.json();
        recipes = data.recipes || {};
        
        displayRecipes(recipes);
    } catch (error) {
        console.error('Error loading recipes:', error);
    }
}

function displayRecipes(recipesToShow) {
    const grid = document.getElementById('crafting-grid');
    grid.innerHTML = '';
    
    Object.entries(recipesToShow).forEach(([id, recipe]) => {
        const emoji = getRecipeEmoji(id);
        const card = document.createElement('div');
        card.className = 'recipe-card';
        card.innerHTML = `
            <div class="recipe-emoji">${emoji}</div>
            <div class="recipe-name">${recipe.name}</div>
            <div class="recipe-description">${recipe.description || ''}</div>
        `;
        grid.appendChild(card);
    });
}

function getRecipeEmoji(key) {
    if (key.includes('кирка')) return '⛏️';
    if (key.includes('топор')) return '🪓';
    if (key.includes('меч')) return '⚔️';
    if (key.includes('броня') || key.includes('шлем')) return '🛡️';
    if (key.includes('блок') || key.includes('камень')) return '🧱';
    if (key.includes('печь')) return '🔥';
    return '🔨';
}

// Load Recipes (for search)
async function loadRecipes() {
    await loadCrafting();
}

// Update Dashboard
async function updateDashboard() {
    try {
        const logsResp = await fetch('/api/logs/');
        const logs = await logsResp.json();
        
        document.getElementById('total-events').textContent = logs.length;
        document.getElementById('dashboard-deaths').textContent = logs.filter(l => l.event_type === 'death').length;
        document.getElementById('health-warnings').textContent = logs.filter(l => l.event_type === 'low_health').length;
        
        // Recent events
        const recentEl = document.getElementById('recent-events');
        if (logs.length > 0) {
            recentEl.innerHTML = logs.slice(-5).reverse().map(log => `
                <div class="event-item">
                    <div class="event-time">${new Date(log.timestamp).toLocaleTimeString()}</div>
                    <div class="event-text">${log.message || log.event_type}</div>
                </div>
            `).join('');
        }
        
        // Load challenge
        await loadChallenges();
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// Update Sidebar
function updateSidebar() {
    loadPlayerState();
    loadChallenges();
}

// Chat Functions
function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    const messagesContainer = document.getElementById('chat-messages');
    
    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
    messagesContainer.appendChild(userMsg);
    
    input.value = '';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Send to AI
    sendChatToAI(message);
}

async function sendChatToAI(message) {
    try {
        const response = await fetch('/api/rp/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: message })
        });
        
        const data = await response.json();
        
        // Add AI response
        const messagesContainer = document.getElementById('chat-messages');
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message ai';
        aiMsg.innerHTML = `<div class="message-content">${escapeHtml(data.response || data.message || 'Ответа пока нет')}</div>`;
        messagesContainer.appendChild(aiMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('Error sending chat:', error);
    }
}

// Analytics
async function generateAnalysis() {
    try {
        const response = await fetch('/api/analytics/session_summary');
        const data = await response.json();
        
        const contentEl = document.getElementById('analytics-content');
        if (data.status === 'success') {
            const renderedMarkdown = data.analysis_html
                || (typeof renderMarkdown === 'function'
                    ? renderMarkdown(data.analysis_markdown || '')
                    : escapeHtml(data.analysis_markdown || ''));
            contentEl.innerHTML = `
                <div class="analysis-section">
                    <h3>Разбор сессии</h3>
                    <div class="analysis-text markdown-output">${renderedMarkdown}</div>
                </div>
                <div class="analysis-section">
                    <h3>Статистика</h3>
                    <div class="analysis-text">
                        <p>Всего логов: ${data.stats.total_logs}</p>
                        <p>Смертей: ${data.stats.deaths}</p>
                        <p>Предупреждений о низком здоровье: ${data.stats.low_health_warnings}</p>
                        <p>Встреч с враждебными мобами: ${data.stats.hostile_encounters}</p>
                    </div>
                </div>
            `;
        } else {
            contentEl.innerHTML = `<p class="error">${data.message}</p>`;
        }
    } catch (error) {
        console.error('Error generating analysis:', error);
        document.getElementById('analytics-content').innerHTML = '<p class="error">Не удалось сгенерировать аналитику</p>';
    }
}

async function loadDashboardSettings() {
    const setStatus = (msg, isError = false) => {
        const el = document.getElementById('dashboard-settings-status');
        if (el) {
            el.textContent = msg;
            el.className = 'settings-status ' + (isError ? 'error' : '');
        }
    };

    try {
        setStatus('Загружаем настройки…');
        const [settingsResponse, promptsResponse] = await Promise.all([
            fetch('/api/settings/'),
            fetch('/api/rp/prompts')
        ]);

        if (!settingsResponse.ok || !promptsResponse.ok) {
            throw new Error(`HTTP ${settingsResponse.status} / ${promptsResponse.status}`);
        }

        const settings = await settingsResponse.json();
        const promptPayload = await promptsResponse.json();
        const prompts = promptPayload.prompts || {};

        const intervalEl = document.getElementById('settings-interval');
        if (intervalEl) intervalEl.value = settings.analysis_interval ?? 500;
        const threshEl = document.getElementById('settings-threshold');
        if (threshEl) threshEl.value = settings.threat_threshold ?? 0.7;
        const voiceEl = document.getElementById('settings-voice');
        if (voiceEl) voiceEl.value = String(!!settings.enable_voice);
        const threatsEl = document.getElementById('settings-max-threats');
        if (threatsEl) threatsEl.value = settings.max_threats_display ?? 3;

        const stateEl = document.getElementById('dashboard-state-prompt');
        if (stateEl) stateEl.value = prompts.state_based || '';
        const chatEl = document.getElementById('dashboard-chat-prompt');
        if (chatEl) chatEl.value = prompts.chat_based || '';
        const actionEl = document.getElementById('dashboard-action-prompt');
        if (actionEl) actionEl.value = prompts.action_based || '';
        const toolEl = document.getElementById('dashboard-tool-result-prompt');
        if (toolEl) toolEl.value = prompts.tool_result_based || '';

        setStatus('');
    } catch (error) {
        console.error('Error loading dashboard settings:', error);
        setStatus(`Ошибка загрузки: ${error.message}`, true);
    }
}

async function saveDashboardSettings(event) {
    event.preventDefault();
    const statusEl = document.getElementById('dashboard-settings-status');
    statusEl.textContent = '';

    const payload = {
        analysis_interval: Number(document.getElementById('settings-interval').value),
        threat_threshold: Number(document.getElementById('settings-threshold').value),
        enable_voice: document.getElementById('settings-voice').value === 'true',
        max_threats_display: Number(document.getElementById('settings-max-threats').value)
    };

    const response = await fetch('/api/settings/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        statusEl.textContent = `Ошибка сохранения: ${await response.text()}`;
        statusEl.className = 'settings-status error';
        return;
    }

    statusEl.textContent = 'Игровые настройки сохранены.';
    statusEl.className = 'settings-status success';
}

async function saveDashboardPrompts(event) {
    event.preventDefault();
    const statusEl = document.getElementById('dashboard-prompts-status');
    statusEl.textContent = '';

    const payload = {
        state_based: document.getElementById('dashboard-state-prompt').value,
        chat_based: document.getElementById('dashboard-chat-prompt').value,
        action_based: document.getElementById('dashboard-action-prompt').value,
        tool_result_based: document.getElementById('dashboard-tool-result-prompt').value
    };

    const response = await fetch('/api/rp/prompts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        statusEl.textContent = `Ошибка сохранения промптов: ${await response.text()}`;
        statusEl.className = 'settings-status error';
        return;
    }

    await loadDashboardSettings();
    statusEl.textContent = 'Промпты сохранены.';
    statusEl.className = 'settings-status success';
}

// Challenge Management
function openNewChallengeModal() {
    document.getElementById('new-challenge-modal').classList.add('active');
}

function closeNewChallengeModal() {
    document.getElementById('new-challenge-modal').classList.remove('active');
}

async function createChallenge(event) {
    event.preventDefault();
    
    const data = {
        title: document.getElementById('challenge-title').value,
        description: document.getElementById('challenge-desc').value,
        goal_type: document.getElementById('challenge-type').value,
        goal_target_id: document.getElementById('challenge-target').value,
        goal_count: parseInt(document.getElementById('challenge-count').value),
        reward_item_id: document.getElementById('challenge-reward').value,
        reward_count: 1
    };
    
    try {
        const response = await fetch('/api/challenges/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeNewChallengeModal();
            document.getElementById('challenge-form').reset();
            loadChallenges();
        }
    } catch (error) {
        console.error('Error creating challenge:', error);
    }
}

async function cancelChallenge(id) {
    try {
        await fetch(`/api/challenges/${id}/cancel`, { method: 'POST' });
        loadChallenges();
    } catch (error) {
        console.error('Error cancelling challenge:', error);
    }
}

// Log Control
function clearLogs() {
    document.getElementById('logs-list').innerHTML = '';
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const btn = document.getElementById('auto-scroll-btn');
    btn.textContent = `Автопрокрутка: ${autoScroll ? 'вкл.' : 'выкл.'}`;
}

// Setup Event Listeners
function setupEventListeners() {
    const logFilter = document.getElementById('log-filter');
    if (logFilter) {
        logFilter.addEventListener('change', loadLogs);
    }
    
    const craftSearch = document.getElementById('craft-search');
    if (craftSearch) {
        craftSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = Object.fromEntries(
                Object.entries(recipes).filter(([id, recipe]) =>
                    id.includes(query) || recipe.name.toLowerCase().includes(query)
                )
            );
            displayRecipes(filtered);
        });
    }
    
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendChatMessage();
        });
    }
    
    // Modal close on background click
    const modal = document.getElementById('new-challenge-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeNewChallengeModal();
        });
    }

    const settingsForm = document.getElementById('dashboard-settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', saveDashboardSettings);
    }

    const promptForm = document.getElementById('dashboard-prompt-form');
    if (promptForm) {
        promptForm.addEventListener('submit', saveDashboardPrompts);
    }
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
