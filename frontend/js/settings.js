async function loadSettings() {
    const response = await fetch('/api/settings/');
    const settings = await response.json();

    document.getElementById('interval').value = settings.analysis_interval ?? 500;
    document.getElementById('threshold').value = settings.threat_threshold ?? 0.7;
    document.getElementById('voice').checked = !!settings.enable_voice;
    document.getElementById('maxThreats').value = settings.max_threats_display ?? 3;
}

async function loadPrompts() {
    const response = await fetch('/api/rp/prompts');
    const data = await response.json();
    const prompts = data.prompts || {};

    document.getElementById('statePrompt').value = prompts.state_based ?? '';
    document.getElementById('chatPrompt').value = prompts.chat_based ?? '';
    document.getElementById('actionPrompt').value = prompts.action_based ?? '';
    document.getElementById('toolResultPrompt').value = prompts.tool_result_based ?? '';
}

async function saveSettings(e) {
    e.preventDefault();

    const payload = {
        analysis_interval: Number(document.getElementById('interval').value),
        threat_threshold: Number(document.getElementById('threshold').value),
        enable_voice: document.getElementById('voice').checked,
        max_threats_display: Number(document.getElementById('maxThreats').value)
    };

    const response = await fetch('/api/settings/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const text = await response.text();
        alert(`Ошибка сохранения: ${text}`);
        return;
    }

    await loadSettings();
}

async function savePrompts(e) {
    e.preventDefault();

    const statusEl = document.getElementById('promptStatus');
    statusEl.textContent = '';

    const payload = {
        state_based: document.getElementById('statePrompt').value,
        chat_based: document.getElementById('chatPrompt').value,
        action_based: document.getElementById('actionPrompt').value,
        tool_result_based: document.getElementById('toolResultPrompt').value
    };

    const response = await fetch('/api/rp/prompts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const text = await response.text();
        statusEl.textContent = `Ошибка сохранения промптов: ${text}`;
        statusEl.className = 'status-message error';
        return;
    }

    await loadPrompts();
    statusEl.textContent = 'Промпты сохранены.';
    statusEl.className = 'status-message success';
}

document.getElementById('settingsForm').addEventListener('submit', saveSettings);
document.getElementById('promptForm').addEventListener('submit', savePrompts);
loadSettings();
loadPrompts();
