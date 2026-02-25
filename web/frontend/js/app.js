const API = '';
let sessionId = null;
let ws = null;
let taskMap = {};

// ---- Panels ----
function showPanel(id) {
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
}

function resetToInput() {
    sessionId = null;
    taskMap = {};
    if (ws) { ws.close(); ws = null; }
    document.getElementById('userRequest').value = '';
    document.getElementById('requestHint').textContent = '';
    document.getElementById('logContainer').innerHTML = '';
    showPanel('panelRequest');
    updateConnStatus(false);
}

// ---- API helpers ----
async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
    }
    return res.json();
}

// ---- Submit Request ----
async function submitRequest() {
    const text = document.getElementById('userRequest').value.trim();
    if (!text) return;

    const hint = document.getElementById('requestHint');
    hint.textContent = '正在规划...';
    document.getElementById('btnSubmit').disabled = true;

    try {
        const { session_id } = await api('POST', '/api/session/create');
        sessionId = session_id;

        await api('POST', `/api/session/${sessionId}/request`, { request: text });
        const plan = await api('GET', `/api/session/${sessionId}/plan`);

        renderPlan(plan);
        showPanel('panelPlan');
    } catch (e) {
        hint.textContent = '错误: ' + e.message;
    } finally {
        document.getElementById('btnSubmit').disabled = false;
    }
}

// ---- Render Plan ----
function renderPlan(plan) {
    document.getElementById('planInfo').innerHTML =
        `<div class="task-meta">预估时长: ${plan.estimated_duration}s | 任务数: ${plan.tasks.length}</div>`;

    const list = document.getElementById('taskList');
    list.innerHTML = '';
    plan.tasks.forEach(t => {
        taskMap[t.task_id] = t;
        list.innerHTML += `
            <div class="task-card">
                <span class="task-id">${t.task_id}</span>
                <div class="task-desc">${t.description}</div>
                <div class="task-meta">${t.module_id}.${t.action} | 风险: ${t.risk_level}${t.depends_on.length ? ' | 依赖: ' + t.depends_on.join(', ') : ''}</div>
            </div>`;
    });

    const ac = plan.acceptance_criteria;
    document.getElementById('acceptanceCriteria').innerHTML =
        `<p>${ac.description || '(无描述)'}</p>` +
        (ac.checkpoints || []).map(cp =>
            `<div class="task-meta">[${cp.check_type}] ${cp.field} = ${cp.expected}</div>`
        ).join('');

    document.getElementById('riskAssessment').innerHTML =
        `<p>${plan.risk_assessment || '(无)'}</p>`;
}

// ---- Confirm & Start ----
let pollTimer = null;

async function confirmPlan() {
    try {
        await api('POST', `/api/session/${sessionId}/confirm`);
        initMonitor();
        showPanel('panelMonitor');
        await connectWebSocket();
        await api('POST', `/api/session/${sessionId}/start`);
        startStatusPolling();
    } catch (e) {
        alert('启动失败: ' + e.message);
    }
}

function startStatusPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        if (!sessionId) return;
        try {
            const st = await api('GET', `/api/session/${sessionId}/status`);
            if (st.status === 'accepted' || st.status === 'failed' || st.status === 'stopped') {
                clearInterval(pollTimer);
                pollTimer = null;
                const total = st.total_tasks || 1;
                const done = st.accepted || 0;
                document.getElementById('progressFill').style.width = `${(done / total) * 100}%`;

                for (const [tid, detail] of Object.entries(st.task_details || {})) {
                    updateTaskStatus(tid, detail.status);
                }

                if (st.status === 'accepted') {
                    addLog('所有任务完成，验收通过', 'success');
                    try {
                        const rpt = await api('GET', `/api/session/${sessionId}/report`);
                        renderReport(rpt);
                        showPanel('panelReport');
                    } catch (_) {}
                } else if (st.status === 'failed') {
                    addLog('执行失败', 'error');
                }
            } else {
                const total = st.total_tasks || 1;
                const done = st.accepted || 0;
                document.getElementById('progressFill').style.width = `${(done / total) * 100}%`;
                document.getElementById('roundInfo').textContent = `轮次: ${st.current_round || 1}`;
                for (const [tid, detail] of Object.entries(st.task_details || {})) {
                    updateTaskStatus(tid, detail.status);
                }
            }
        } catch (_) {}
    }, 2000);
}

// ---- Monitor ----
function initMonitor() {
    const list = document.getElementById('taskStatusList');
    list.innerHTML = '';
    Object.values(taskMap).forEach(t => {
        list.innerHTML += `
            <div class="task-status-item" id="tsi-${t.task_id}">
                <span class="status-dot pending" id="dot-${t.task_id}"></span>
                <span>${t.task_id}: ${t.description}</span>
            </div>`;
    });
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('roundInfo').textContent = '轮次: 1';
}

function updateTaskStatus(taskId, status) {
    const dot = document.getElementById('dot-' + taskId);
    if (dot) {
        dot.className = 'status-dot ' + status;
    }
}

function addLog(msg, cls) {
    const el = document.getElementById('logContainer');
    const time = new Date().toLocaleTimeString();
    el.innerHTML += `<div class="log-entry ${cls || ''}"><span class="time">[${time}]</span> ${msg}</div>`;
    el.scrollTop = el.scrollHeight;
}

function updateProgress() {
    const total = Object.keys(taskMap).length || 1;
    const done = document.querySelectorAll('.status-dot.accepted').length;
    document.getElementById('progressFill').style.width = `${(done / total) * 100}%`;
}

// ---- WebSocket ----
function connectWebSocket() {
    return new Promise((resolve, reject) => {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${proto}://${location.host}/ws/session/${sessionId}`);
        ws.onopen = () => { updateConnStatus(true); resolve(); };
        ws.onclose = () => updateConnStatus(false);
        ws.onerror = (e) => { updateConnStatus(false); reject(e); };

        ws.onmessage = (evt) => {
            if (evt.data === 'pong') return;
            const event = JSON.parse(evt.data);
            handleEvent(event);
        };

        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 15000);
    });
}

function updateConnStatus(connected) {
    const el = document.getElementById('connStatus');
    el.textContent = connected ? '已连接' : '未连接';
    el.className = 'status-indicator' + (connected ? ' connected' : '');
}

function handleEvent(event) {
    const { event_type, task_id, data, message } = event;

    switch (event_type) {
        case 'round_start':
            document.getElementById('roundInfo').textContent = `轮次: ${data.round}`;
            addLog(`=== 第 ${data.round} 轮开始 ===`);
            break;
        case 'round_end':
            addLog(`第 ${data.round} 轮结束: ${data.reason || data.status}`);
            break;
        case 'task_start':
            updateTaskStatus(task_id, 'running');
            addLog(`开始: ${task_id} — ${message || ''}`);
            break;
        case 'task_completed':
            updateTaskStatus(task_id, 'accepted');
            addLog(`完成: ${task_id}`, 'success');
            updateProgress();
            break;
        case 'task_failed':
            updateTaskStatus(task_id, 'failed');
            addLog(`失败: ${task_id} — ${data.error || message || ''}`, 'error');
            updateProgress();
            break;
        case 'validation_result':
            if (data.passed) {
                addLog('验收通过', 'success');
            } else {
                addLog(`验收未通过: ${(data.failures || []).join('; ')}`, 'error');
            }
            break;
        case 'captcha_detected':
            addLog('检测到验证码！', 'error');
            break;
        case 'final_report':
            addLog('任务完成，生成报告');
            renderReport(data);
            showPanel('panelReport');
            break;
        default:
            if (message) addLog(message);
    }
}

// ---- Stop ----
async function stopExecution() {
    if (!sessionId) return;
    try {
        await api('POST', `/api/session/${sessionId}/stop`);
        addLog('已发送中止信号', 'error');
    } catch (e) {
        addLog('中止失败: ' + e.message, 'error');
    }
}

// ---- Report ----
function renderReport(data) {
    const s = data.summary || {};
    document.getElementById('reportSummary').innerHTML = `
        <div class="report-summary">
            <div class="stat-card"><div class="value">${s.total_tasks || 0}</div><div class="label">总任务</div></div>
            <div class="stat-card success"><div class="value">${s.accepted || 0}</div><div class="label">成功</div></div>
            <div class="stat-card failed"><div class="value">${s.failed || 0}</div><div class="label">失败</div></div>
            <div class="stat-card"><div class="value">${data.rounds || 0}</div><div class="label">执行轮次</div></div>
        </div>
        <p>状态: <strong>${data.status || '-'}</strong> | 原始需求: ${data.original_request || '-'}</p>`;

    document.getElementById('reportDetails').innerHTML =
        `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// ---- Modals (footer links) ----
function openModal(title, content) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = content;
    document.getElementById('modalOverlay').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modalOverlay').classList.add('hidden');
}

async function showModules() {
    try {
        const mods = await api('GET', '/api/modules');
        const html = mods.map(m =>
            `<div class="task-card"><span class="task-id">${m.id}</span> <span class="task-meta">[${m.category}]</span><div class="task-desc">${m.description}</div></div>`
        ).join('');
        openModal('已注册模块', html);
    } catch (e) {
        openModal('错误', e.message);
    }
}

async function showBrowserStatus() {
    try {
        const st = await api('GET', '/api/browsers/status');
        openModal('浏览器池状态', `<pre>${JSON.stringify(st, null, 2)}</pre>`);
    } catch (e) {
        openModal('错误', e.message);
    }
}

async function showModelConfig() {
    try {
        const cfg = await api('GET', '/api/models');
        openModal('模型配置', `<pre>${JSON.stringify(cfg, null, 2)}</pre>`);
    } catch (e) {
        openModal('错误', e.message);
    }
}
