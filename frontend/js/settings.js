async function loadSettings() {
    const response = await fetch('/api/settings/');
    const settings = await response.json();

    document.getElementById('interval').value = settings.analysis_interval ?? 500;
    document.getElementById('threshold').value = settings.threat_threshold ?? 0.7;
    document.getElementById('voice').checked = !!settings.enable_voice;
    document.getElementById('maxThreats').value = settings.max_threats_display ?? 3;
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

document.getElementById('settingsForm').addEventListener('submit', saveSettings);
loadSettings();
