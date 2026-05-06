let currentActiveChallenge = null;

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
        kill: 'убить',
        collect: 'собрать'
    };
    return labels[goalType] || goalType || 'цель';
}

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

function renderActiveChallenge(challenge) {
    const container = document.getElementById('activeChallenge');
    const cancelButton = document.getElementById('cancelButton');
    const rewardInfo = document.getElementById('rewardInfo');

    currentActiveChallenge = challenge || null;
    if (!challenge) {
        container.innerHTML = '<div class="empty">Сейчас активного челленджа нет.</div>';
        cancelButton.disabled = true;
        rewardInfo.textContent = 'Награда за выполненный челлендж выдаётся автоматически.';
        return;
    }

    cancelButton.disabled = false;
    rewardInfo.textContent = challenge.status === 'completed' && challenge.reward_status === 'failed'
        ? `Автовыдача не удалась: ${challenge.reward_issue_error || 'неизвестная ошибка'}`
        : 'Награда выдаётся автоматически сразу после выполнения челленджа.';

    container.innerHTML = `
        <div class="kv-list">
            <div class="kv-item"><span>ID</span><strong>${challenge.id}</strong></div>
            <div class="kv-item"><span>Название</span><strong>${challenge.title || 'Без названия'}</strong></div>
            <div class="kv-item"><span>Статус</span><strong><span class="status-pill">${getChallengeStatusLabel(challenge.status)}</span></strong></div>
            <div class="kv-item"><span>Цель</span><strong>${getGoalTypeLabel(challenge.goal_type)} ${challenge.goal_target_name || challenge.goal_target_id} x${challenge.goal_count}</strong></div>
            <div class="kv-item"><span>Прогресс</span><strong>${challenge.progress_count || 0}/${challenge.goal_count || 1}</strong></div>
            <div class="kv-item"><span>Награда</span><strong>${challenge.reward_item_name || challenge.reward_item_id} x${challenge.reward_count || 1}</strong></div>
            <div class="kv-item"><span>Описание</span><strong>${challenge.description || '-'}</strong></div>
        </div>
    `;
}

async function loadChallenges() {
    const response = await fetch('/api/challenges/');
    const state = await response.json();

    document.getElementById('updatedAt').textContent = state.updated_at
        ? `Последнее обновление: ${new Date(state.updated_at).toLocaleString()}`
        : 'Челленджи ещё не создавались.';

    renderActiveChallenge(state.active || null);

    const historyEntries = (state.history || []).slice().reverse().slice(0, 15).map(challenge => [
        `${challenge.title || challenge.id} (${getChallengeStatusLabel(challenge.status)})`,
        `${getGoalTypeLabel(challenge.goal_type)} ${challenge.goal_target_name || challenge.goal_target_id} x${challenge.goal_count} -> ${challenge.reward_item_name || challenge.reward_item_id} x${challenge.reward_count}`
    ]);
    renderKeyValueList('challengeHistory', historyEntries, 'История челленджей пуста.');
}

async function createChallenge() {
    const payload = {
        title: document.getElementById('title').value || null,
        goal_type: document.getElementById('goalType').value,
        goal_target_id: document.getElementById('goalTargetId').value,
        goal_count: Number(document.getElementById('goalCount').value || 1),
        reward_item_id: document.getElementById('rewardItemId').value,
        reward_count: Number(document.getElementById('rewardCount').value || 1)
    };

    const response = await fetch('/api/challenges/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    document.getElementById('createResult').textContent = response.ok
        ? (data.summary || 'Челлендж создан.')
        : (data.detail || 'Не удалось создать челлендж.');
    await loadChallenges();
}

async function cancelChallenge() {
    if (!currentActiveChallenge) {
        return;
    }
    const response = await fetch(`/api/challenges/${currentActiveChallenge.id}/cancel`, { method: 'POST' });
    const data = await response.json();
    alert(response.ok ? (data.summary || 'Челлендж отменён.') : (data.detail || 'Не удалось отменить челлендж.'));
    await loadChallenges();
}

loadChallenges();
setInterval(loadChallenges, 3000);
