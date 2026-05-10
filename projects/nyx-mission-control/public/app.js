let snapshot = null;
let taskBoard = null;
let calendarProjectFilter = new Set();

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

function calendarProjectKey(item) {
  return item.projectSlug || '__unassigned';
}

function calendarItemVisible(item) {
  return !calendarProjectFilter.size || calendarProjectFilter.has(calendarProjectKey(item));
}

function cronProjectSelect(item) {
  const options = [`<option value="" ${!item.projectSlug ? 'selected' : ''}>Unassigned</option>`].concat((snapshot.projects || []).map((project) => `<option value="${esc(project.slug)}" ${item.projectSlug === project.slug ? 'selected' : ''}>${esc(project.name)}</option>`));
  return `<select class="cron-project-select" data-cron-id="${esc(item.jobId || item.id)}" title="Associar cron a projeto">${options.join('')}</select>`;
}

function calendarProjectFilters() {
  const items = [{ slug: '__unassigned', name: 'Unassigned' }, ...(snapshot.projects || []).map((project) => ({ slug: project.slug, name: project.name }))];
  return `<div class="calendar-filters"><button type="button" data-calendar-all>All</button>${items.map((item) => `<label><input type="checkbox" value="${esc(item.slug)}" ${calendarProjectFilter.has(item.slug) ? 'checked' : ''} />${esc(item.name)}</label>`).join('')}</div>`;
}

function renderCalendar() {
  const calendar = snapshot.calendar || { alwaysRunning: [], days: [] };
  const running = (calendar.alwaysRunning || []).filter(calendarItemVisible);
  const chips = running.map((item) => `<span class="task-chip ${esc(item.color)}" title="${esc(item.fullTitle || item.title)}\n${esc(item.scheduleText)}\nProjeto: ${esc(item.projectName || 'Unassigned')}"><strong>${esc(item.title)}</strong><small>${esc(item.projectName || 'Unassigned')} · ${esc(item.scheduleText)}</small>${cronProjectSelect(item)}</span>`).join('');
  const days = (calendar.days || []).map((day) => {
    const events = (day.events || []).filter(calendarItemVisible);
    return `<div class="calendar-day"><div class="day-head"><strong>${esc(day.label)}</strong><small>${fmt(day.date).split(',')[0]}</small></div><div class="day-events">${events.map((event) => `<div class="cal-event ${esc(event.color)} ${esc(event.severity)}" title="${esc(event.fullTitle || event.title)}\n${esc(event.scheduleText)}\nProjeto: ${esc(event.projectName || 'Unassigned')}"><strong>${esc(event.title)}</strong><span>${esc(event.time)} · ${esc(event.status)} · ${esc(event.projectName || 'Unassigned')}</span>${cronProjectSelect(event)}</div>`).join('') || '<div class="no-events">—</div>'}</div></div>`;
  }).join('');
  $('calendar').innerHTML = `<div class="card"><div class="section-head"><div><h2>Scheduled Tasks</h2><p>Nyx automated routines and reminders, mapped by week.</p></div><span class="badge OK">Week</span></div>${calendarProjectFilters()}<div class="always"><h3>⚡ Always Running</h3><div class="chips">${chips || '<span class="muted">No interval jobs detected for selected projects.</span>'}</div></div><div class="calendar-grid">${days}</div></div>`;
  bindCalendarEvents();
}

function ownerBadge(owner) {
  const label = owner === 'nyx' ? '😼 Nyx' : '👤 Tiago';
  return `<span class="owner-pill owner-${esc(owner)}">${label}</span>`;
}

function taskCard(task) {
  const execution = [task.lastRunSummary ? `<div class="task-run">Last run: ${esc(task.lastRunSummary)}</div>` : '', task.blockedReason ? `<div class="task-blocked">Blocked: ${esc(task.blockedReason)}</div>` : ''].join('');
  return `<div class="task-card owner-${esc(task.owner)}" data-task-id="${esc(task.id)}"><div class="task-card-top">${ownerBadge(task.owner)}<span class="priority-pill">${esc(task.priority || 'normal')}</span></div><div class="task-title">${esc(task.title)}</div><div class="task-meta">${task.runId ? esc(task.runId) : 'No run'}</div>${task.description ? `<div class="task-desc">${esc(task.description)}</div>` : ''}${execution}<div class="task-actions"><button data-move="backlog">Backlog</button><button data-move="todo">To do</button><button data-move="in_progress">Doing</button><button data-move="blocked">Blocked</button><button data-move="done">Done</button><button class="danger" data-delete="true">Delete</button></div></div>`;
}

function renderTasks() {
  const columns = taskBoard?.columns || [];
  const counts = (taskBoard?.tasks || []).reduce((acc, task) => ({ ...acc, [task.owner]: (acc[task.owner] || 0) + 1 }), {});
  $('tasks').innerHTML = `<div class="card"><div class="section-head"><div><h2>Tasks</h2><p>Kanban operacional. Moves notificam <code>#nyx</code>.</p><div class="owner-legend">${ownerBadge('tiago')} <span>${counts.tiago || 0}</span>${ownerBadge('nyx')} <span>${counts.nyx || 0}</span></div></div><span class="badge OK">Kanban</span></div><form id="taskForm" class="task-form"><input name="title" required placeholder="New task…" /><select name="owner"><option value="tiago">Tiago</option><option value="nyx">Nyx</option></select><select name="status"><option value="backlog">Backlog</option><option value="todo">To do</option><option value="in_progress">In progress</option></select><button type="submit">Create</button><textarea name="description" placeholder="Description optional"></textarea></form><div class="kanban">${columns.map((column) => `<div class="kanban-col"><div class="kanban-head"><strong>${esc(column.title)}</strong><span>${column.tasks.length}</span></div><div class="kanban-list">${column.tasks.map(taskCard).join('') || '<div class="no-events">No tasks</div>'}</div></div>`).join('')}</div></div>`;
  bindTaskEvents();
}

function projectJsonTemplate(project) {
  return JSON.stringify({
    name: project.name || project.slug,
    status: project.status || 'active',
    updatedAt: new Date().toISOString().slice(0, 10),
    nextAction: project.nextAction === 'project.json em falta ou incompleto' ? '' : (project.nextAction || ''),
    owner: 'Nyx',
    priority: 'normal'
  }, null, 2);
}

function selectOptions(values, selected) {
  return values.map((value) => `<option value="${esc(value)}" ${String(selected).toLowerCase() === String(value).toLowerCase() ? 'selected' : ''}>${esc(value)}</option>`).join('');
}

function renderProjects() {
  $('projects').innerHTML = `<div class="card"><div class="section-head"><div><h2>Projects</h2><p>Vista limpa por defeito. Edita campos guiados; JSON avançado é só para extras.</p></div><span class="badge OK">project.json</span></div><div class="project-list">${(snapshot.projects || []).map((p) => `<div class="project-card" data-project-slug="${esc(p.slug)}"><div class="project-main"><div><strong>${esc(p.name)}</strong><div class="detail">${esc(p.slug)} · updated ${fmt(p.updatedAt)}</div><div class="detail">Next: ${esc(p.nextAction || '-')}</div><div class="detail">Files: ${esc((p.importantFiles || []).join(', ') || '-')}</div></div><div class="project-badges">${badge(p.severity, p.status)}${p.hasProjectJson ? badge('OK', 'project.json') : badge('Aviso', 'missing project.json')}</div></div><details class="project-editor"><summary>Edit project</summary><form><div class="project-field-grid"><label>Name<input name="name" value="${esc(p.name || p.slug)}" /></label><label>Status<select name="status">${selectOptions(['active', 'blocked', 'paused', 'done', 'unknown'], p.status || 'active')}</select></label><label>Priority<select name="priority">${selectOptions(['low', 'normal', 'high', 'urgent'], 'normal')}</select></label><label>Owner<select name="owner">${selectOptions(['Nyx', 'Tiago', 'Shared'], 'Nyx')}</select></label><label class="wide">Next action<input name="nextAction" value="${esc(p.nextAction === 'project.json em falta ou incompleto' ? '' : (p.nextAction || ''))}" placeholder="O próximo passo concreto" /></label></div><details class="advanced-json"><summary>Advanced JSON extras</summary><textarea name="json" spellcheck="false">${esc(projectJsonTemplate(p))}</textarea></details><div class="project-editor-actions"><button type="button" data-load-json>Reload from disk</button><button type="submit">Save project.json</button></div><div class="project-save-status"></div></form></details></div>`).join('') || empty('Sem projetos.')}</div></div>`;
  bindProjectEvents();
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

function shouldPreserveTaskDraft() {
  const form = document.getElementById('taskForm');
  if (!form) return false;
  const title = form.querySelector('[name="title"]')?.value.trim();
  const description = form.querySelector('[name="description"]')?.value.trim();
  return form.contains(document.activeElement) || Boolean(title || description);
}

function shouldPreserveProjectEdit() {
  const activeProjectForm = document.activeElement?.closest?.('[data-project-slug]');
  return Boolean(activeProjectForm);
}

function render() {
  if (!snapshot) return;
  const preserveTaskDraft = shouldPreserveTaskDraft();
  const preserveProjectEdit = shouldPreserveProjectEdit();
  renderHealth(); renderHome(); renderCrons(); renderCalendar();
  if (!preserveTaskDraft) renderTasks();
  if (!preserveProjectEdit) renderProjects();
  renderActivity(); renderLogs(); renderSettings();
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

function bindCalendarEvents() {
  const container = $('calendar');
  container.querySelector('[data-calendar-all]')?.addEventListener('click', () => {
    calendarProjectFilter = new Set();
    renderCalendar();
  });
  container.querySelectorAll('.calendar-filters input[type="checkbox"]').forEach((input) => input.addEventListener('change', () => {
    if (input.checked) calendarProjectFilter.add(input.value);
    else calendarProjectFilter.delete(input.value);
    renderCalendar();
  }));
  container.querySelectorAll('.cron-project-select').forEach((select) => select.addEventListener('change', async () => {
    select.disabled = true;
    await fetch(`/api/crons/${encodeURIComponent(select.dataset.cronId)}/project`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ projectSlug: select.value }) });
    await load();
  }));
}

function populateProjectEditor(card, json) {
  card.querySelector('[name="name"]').value = json.name || card.dataset.projectSlug;
  card.querySelector('[name="status"]').value = json.status || 'active';
  card.querySelector('[name="priority"]').value = json.priority || 'normal';
  card.querySelector('[name="owner"]').value = json.owner || 'Nyx';
  card.querySelector('[name="nextAction"]').value = json.nextAction || '';
  card.querySelector('textarea[name="json"]').value = JSON.stringify(json, null, 2);
}

async function loadProjectJson(card) {
  const slug = card.dataset.projectSlug;
  const status = card.querySelector('.project-save-status');
  status.textContent = 'Loading project.json…';
  const res = await fetch(`/api/projects/${encodeURIComponent(slug)}/json`);
  const data = await res.json();
  populateProjectEditor(card, data.json);
  status.textContent = data.exists ? 'Loaded from disk.' : 'No project.json yet — template loaded.';
}

function bindProjectEvents() {
  document.querySelectorAll('[data-project-slug]').forEach((card) => {
    const details = card.querySelector('details');
    details.addEventListener('toggle', () => { if (details.open) loadProjectJson(card).catch((error) => { card.querySelector('.project-save-status').textContent = error.message; }); });
    card.querySelector('[data-load-json]').addEventListener('click', () => loadProjectJson(card));
    card.querySelector('form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = card.querySelector('button[type="submit"]');
      const status = card.querySelector('.project-save-status');
      const textarea = card.querySelector('textarea[name="json"]');
      submit.disabled = true;
      try {
        const parsed = JSON.parse(textarea.value || '{}');
        const next = {
          ...parsed,
          name: card.querySelector('[name="name"]').value.trim() || card.dataset.projectSlug,
          status: card.querySelector('[name="status"]').value,
          priority: card.querySelector('[name="priority"]').value,
          owner: card.querySelector('[name="owner"]').value,
          nextAction: card.querySelector('[name="nextAction"]').value.trim(),
          updatedAt: new Date().toISOString().slice(0, 10)
        };
        await fetch(`/api/projects/${encodeURIComponent(card.dataset.projectSlug)}/json`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(next) });
        status.textContent = 'Saved.';
        await load();
      } catch (error) {
        status.textContent = `Error: ${error.message}`;
      } finally {
        submit.disabled = false;
      }
    });
  });
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
