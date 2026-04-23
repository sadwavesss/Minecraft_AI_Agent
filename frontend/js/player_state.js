function renderKeyValueList(containerId, entries, emptyText) {
    const container = document.getElementById(containerId);
    if (!entries || !entries.length) {
        container.innerHTML = `<div class="empty">${emptyText}</div>`;
        return;
    }

    container.innerHTML = entries.map(([key, value]) => `
        <div class="kv-item">
            <span>${key}</span>
            <strong>${value}</strong>
        </div>
    `).join('');
}

function renderPills(containerId, entries, emptyText) {
    const container = document.getElementById(containerId);
    if (!entries || !entries.length) {
        container.innerHTML = `<div class="empty">${emptyText}</div>`;
        return;
    }

    container.innerHTML = entries.map(entry => {
        const label = entry.display_name || entry.item_id || 'unknown';
        const count = entry.count ? ` x${entry.count}` : '';
        const slot = entry.slot ? `${entry.slot}: ` : '';
        return `<span class="pill">${slot}${label}${count}</span>`;
    }).join('');
}

async function loadPlayerState() {
    const response = await fetch('/api/player-state/');
    const state = await response.json();

    document.getElementById('updatedAt').textContent = state.updated_at
        ? `Последнее обновление: ${new Date(state.updated_at).toLocaleString()}`
        : 'Данных telemetry пока нет.';

    document.getElementById('killSummary').textContent = `Всего киллов: ${state.kill_total || 0}`;

    const killEntries = (state.kill_count_entries || []).map(entry => [entry.display_name || entry.id, entry.count]);
    renderKeyValueList('killCounts', killEntries, 'Киллы ещё не зафиксированы.');

    const recentKills = (state.recent_kills || []).slice().reverse().slice(0, 10).map(entry => [
        entry.entity_name || entry.entity_id || 'unknown',
        `+${entry.count_delta || 1} · ${new Date(entry.timestamp).toLocaleString()}`
    ]);
    renderKeyValueList('recentKills', recentKills, 'Недавних киллов нет.');

    const inventoryCounts = ((state.inventory || {}).count_entries || [])
        .map(entry => [entry.display_name || entry.id, entry.count])
        .slice(0, 20);
    renderKeyValueList('inventoryCounts', inventoryCounts, 'Инвентарь ещё не считан.');

    renderPills('hotbar', (state.inventory || {}).hotbar || [], 'Hotbar пуст или ещё не считан.');
    renderPills('armor', (state.inventory || {}).armor || [], 'Armor пуст или ещё не считан.');
    renderPills('offhand', (state.inventory || {}).offhand || [], 'Offhand пуст или ещё не считан.');
}

loadPlayerState();
setInterval(loadPlayerState, 3000);
