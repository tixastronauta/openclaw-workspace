let snapshot = null;
let taskBoard = null;

const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
const fmt = (iso) => iso ? new Intl.DateTimeFormat('pt-PT', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(iso)) : '-';

function badge(severity = 'OK', label = severity) {
  return `<span class="badge ${esc(severity)}">${esc(label)}</span>`;
}

function row(item) {
  return `<div class="row">${badge(item.severity || 'OK')}<div><div class="title">${esc(item.title || item.name)}</div><div class="detail">${esc(item.detail || item.nextAction || '')}</div></div><small>${item.ts ? fmt(item.ts) : ''}</small></div>`;
}

function empty(text) { return `<div class="empty">${esc(text)}</div>`; }

function renderHealth() {
  $('sourceHealth').innerHTML = (snapshot.sources || []).map((source) => badge(source.status, `${source.name}: ${source.status}`)).join('');
  $('subtitle').textContent = `Last sync: ${fmt(snapshot.generatedAt)} · read-only local cockpit`;
}

function renderHome() {
  const attention = snapshot.attention || [];
  const grouped = ['Erro', 'Aviso', 'OK'].map((sev) => ({ sev, items: attention.filter((item) => item.severity === sev) })).filter((g) => g.items.length);
  $('home').innerHTML = `<div class="grid">
    <div class="card span-12"><h2>Atenção agora</h2>${grouped.length ? grouped.map((g) => `<h3>${badge(g.sev)} ${g.items.length}</h3><div class="list">${g.items.map(row).join('')}</div>`).join('') : empty('Nada crítico neste momento. Estranhamente civilizado.')}</div>
    <div class="card span-4"><h2>Resumo 24h</h2><div class="kpis"><div class="kpi"><strong>${snapshot.summary24h?.totalEvents ?? 0}</strong><span>eventos</span></div><div class="kpi"><strong>${snapshot.summary24h?.errors ?? 0}</strong><span>erros</span></div><div class="kpi"><strong>${snapshot.summary24h?.warnings ?? 0}</strong><span>avisos</span></div><div class="kpi"><strong>${snapshot.summary24h?.approvals ?? 0}</strong><span>aprovações</span></div></div></div>
    <div class="card span-4"><h2>Crons</h2><div class="kpis"><div class="kpi"><strong>${snapshot.summary24h?.cronsOk ?? 0}</strong><span>OK</span></div><div class="kpi"><strong>${snapshot.summary24h?.cronsProblem ?? 0}</strong><span>problemas</span></div></div></div>
    <div class="card span-4"><h2>Histórico 7d</h2><div class="kpis"><div class="kpi"><strong>${snapshot.history7d?.totalEvents ?? 0}</strong><span>eventos</span></div><div class="kpi"><strong>${snapshot.history7d?.bySeverity?.Erro ?? 0}</strong><span>erros</span></div></div></div>
    <div class="card span-6"><h2>Projetos</h2><div class="list">${(snapshot.projects || []).slice(0, 8).map((p) => row({ severity: p.severity, title: p.name, detail: `${p.status} · ${p.nextAction}` })).join('') || empty('Sem projetos.')}</div></div>
    <div class="card span-6"><h2>Últimas ações da Nyx</h2><div class="list">${(snapshot.activity || []).slice(0, 20).map(row).join('') || empty('Sem ações recentes indexadas.')}</div></div>
  </div>`;
}

function renderCrons() {
  $('crons').innerHTML = `<div class="card"><h2>Crons & Reminders</h2><table class="table"><thead><tr><th>Status</th><th>Name</th><th>Schedule</th><th>Next</th><th>Last</th></tr></thead><tbody>${(snapshot.crons || []).map((c) => `<tr><td>${badge(c.severity, c.status)}</td><td>${esc(c.name)}<div class="detail">${esc(c.description || '')}</div></td><td><code>${esc(c.scheduleText || '')}</code></td><td>${fmt(c.nextRunAt)}</td><td>${fmt(c.lastRunAt)}</td></tr>`).join('')}</tbody></table>${!snapshot.crons?.length ? empty('Cron source unavailable or no jobs parsed.') : ''}</div>`;
}

function renderCalendar() {
  const calendar = snapshot.calendar || { alwaysRunning: [], days: [] };
  const chips = (calendar.alwaysRunning || []).map((item) => `<span class="task-chip ${esc(item.color)}">${esc(item.title)} · ${esc(item.scheduleText)}</span>`).join('');
  const days = (calendar.days || []).map((day) => `<div class="calendar-day"><div class="day-head"><strong>${esc(day.label)}</strong><small>${fmt(day.date).split(',')[0]}</small></div><div class="day-events">${(day.events || []).map((event) => `<div class="cal-event ${esc(event.color)} ${esc(event.severity)}"><strong>${esc(event.title)}</strong><span>${esc(event.time)} · ${esc(event.status)}</span></div>`).join('') || '<div class="no-events">—</div>'}</div></div>`).join('');
  $('calendar').innerHTML = `<div class="card"><div class="section-head"><div><h2>Scheduled Tasks</h2><p>Nyx automated routines and reminders, mapped by week.</p></div><span class="badge OK">Week</span></div><div class="always"><h3>⚡ Always Running</h3><div class="chips">${chips || '<span class="muted">No interval jobs detected.</span>'}</div></div><div class="calendar-grid">${days}</div></div>`;
}

function ownerBadge(owner) {
  const label = owner === 'nyx' ? '😼 Nyx' : '👤 Tiago';
  return `<span class="owner-pill owner-${esc(owner)}">${label}</span>`;
}

function taskCard(task) {
  const execution = [task.lastRunSummary ? `<div class="task-run">Last run: ${esc(task.lastRunSummary)}</div>` : '', task.blockedReason ? `<div class="task-blocked">Blocked: ${esc(task.blockedReason)}</div>` : ''].join('');
  return `<div class="task-card owner-${esc(task.owner)}" data-task-id="${esc(task.id)}"><div class="task-card-top">${ownerBadge(task.owner)}<span class="priority-pill">${esc(task.priority || 'normal')}</span></div><div class="task-title">${esc(task.title)}</div><div class="task-meta">${task.project ? `Project: ${esc(task.project)}` : 'No project'}${task.runId ? ` · ${esc(task.runId)}` : ''}</div>${task.description ? `<div class="task-desc">${esc(task.description)}</div>` : ''}${execution}<div class="task-actions"><button data-move="backlog">Backlog</button><button data-move="todo">To do</button><button data-move="in_progress">Doing</button><button data-move="blocked">Blocked</button><button data-move="done">Done</button><button class="danger" data-delete="true">Delete</button></div></div>`;
}

function renderTasks() {
  const columns = taskBoard?.columns || [];
  const counts = (taskBoard?.tasks || []).reduce((acc, task) => ({ ...acc, [task.owner]: (acc[task.owner] || 0) + 1 }), {});
  $('tasks').innerHTML = `<div class="card"><div class="section-head"><div><h2>Tasks</h2><p>Kanban operacional. Moves notificam <code>#nyx</code>.</p><div class="owner-legend">${ownerBadge('tiago')} <span>${counts.tiago || 0}</span>${ownerBadge('nyx')} <span>${counts.nyx || 0}</span></div></div><span class="badge OK">Kanban</span></div><form id="taskForm" class="task-form"><input name="title" required placeholder="New task…" /><select name="owner"><option value="tiago">Tiago</option><option value="nyx">Nyx</option></select><select name="status"><option value="backlog">Backlog</option><option value="todo">To do</option><option value="in_progress">In progress</option></select><input name="project" placeholder="Project optional" /><button type="submit">Create</button><textarea name="description" placeholder="Description optional"></textarea></form><div class="kanban">${columns.map((column) => `<div class="kanban-col"><div class="kanban-head"><strong>${esc(column.title)}</strong><span>${column.tasks.length}</span></div><div class="kanban-list">${column.tasks.map(taskCard).join('') || '<div class="no-events">No tasks</div>'}</div></div>`).join('')}</div></div>`;
  bindTaskEvents();
}

function renderProjects() {
  $('projects').innerHTML = `<div class="card"><h2>Projects</h2><table class="table"><thead><tr><th>Status</th><th>Project</th><th>Updated</th><th>Next action</th><th>Files</th><th>Org</th></tr></thead><tbody>${(snapshot.projects || []).map((p) => `<tr><td>${badge(p.severity, p.status)}</td><td>${esc(p.name)}<div class="detail">${esc(p.slug)}</div></td><td>${fmt(p.updatedAt)}</td><td>${esc(p.nextAction)}</td><td>${esc((p.importantFiles || []).join(', ') || '-')}</td><td>${esc(p.organization)}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderActivity() {
  $('activity').innerHTML = `<div class="card"><h2>Activity · 30d cache</h2><div class="list">${(snapshot.activity || []).map((event) => `<details class="row"><summary>${badge(event.severity)} <strong>${esc(event.title)}</strong> <small>${fmt(event.ts)}</small></summary><pre>${esc(JSON.stringify(event.technical || event, null, 2))}</pre></details>`).join('') || empty('Sem atividade indexada.')}</div></div>`;
}

function renderLogs() {
  $('logs').innerHTML = `<div class="card"><h2>Logs & errors</h2><div class="list">${(snapshot.logErrors || []).map((event) => `<details class="row"><summary>${badge(event.severity)} <strong>${esc(event.title)}</strong></summary><pre>${esc(event.detail)}\n\n${esc(JSON.stringify(event.technical, null, 2))}</pre></details>`).join('') || empty('Sem erros graves detetados nos logs recentes.')}</div></div>`;
}

function renderSettings() {
  $('settings').innerHTML = `<div class="card"><h2>Settings</h2><p>Read-only POC config. Future tweakable knobs live here.</p><pre>${esc(JSON.stringify(snapshot.config, null, 2))}</pre><h3>Sources</h3><pre>${esc(JSON.stringify(snapshot.sources, null, 2))}</pre></div>`;
}

function render() {
  if (!snapshot) return;
  renderHealth(); renderHome(); renderCrons(); renderCalendar(); renderTasks(); renderProjects(); renderActivity(); renderLogs(); renderSettings();
}

async function loadTasks() {
  const res = await fetch('/api/tasks');
  taskBoard = await res.json();
}

async function load() {
  const [snapshotRes] = await Promise.all([fetch('/api/snapshot'), loadTasks()]);
  snapshot = await snapshotRes.json();
  render();
}

function bindTaskEvents() {
  const form = document.getElementById('taskForm');
  if (form) form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      await fetch('/api/tasks', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) });
      form.reset();
      await loadTasks();
      renderTasks();
    } finally {
      submit.disabled = false;
    }
  });
  document.querySelectorAll('[data-task-id] [data-move]').forEach((button) => button.addEventListener('click', async () => {
    const card = button.closest('[data-task-id]');
    card.classList.add('moving');
    await fetch(`/api/tasks/${card.dataset.taskId}`, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ status: button.dataset.move }) });
    await loadTasks();
    renderTasks();
  }));
  document.querySelectorAll('[data-task-id] [data-delete]').forEach((button) => button.addEventListener('click', async () => {
    const card = button.closest('[data-task-id]');
    const title = card.querySelector('.task-title')?.textContent || 'this task';
    if (!confirm(`Delete task: ${title}?`)) return;
    card.classList.add('moving');
    await fetch(`/api/tasks/${card.dataset.taskId}`, { method: 'DELETE' });
    await loadTasks();
    renderTasks();
  }));
}

function route() {
  const target = location.hash?.slice(1) || 'home';
  document.querySelectorAll('.page').forEach((el) => el.classList.toggle('active', el.id === target));
  document.querySelectorAll('nav a').forEach((el) => el.classList.toggle('active', el.getAttribute('href') === `#${target}`));
}

window.addEventListener('hashchange', route);
$('refresh').addEventListener('click', async () => { await fetch('/api/refresh', { method: 'POST' }); await load(); });
$('copyDiag').addEventListener('click', async () => {
  const res = await fetch('/api/diagnostic');
  const text = JSON.stringify(await res.json(), null, 2);
  await navigator.clipboard.writeText(text);
  $('copyDiag').textContent = 'Copied';
  setTimeout(() => $('copyDiag').textContent = 'Copy diagnostic', 1200);
});

const events = new EventSource('/events');
events.onmessage = (message) => {
  const data = JSON.parse(message.data);
  if (data.type === 'snapshot') { snapshot = data.snapshot; render(); }
};

route();
load();
