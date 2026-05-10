import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readProjectOverrides } from './project-overrides.js';

const execFileAsync = promisify(execFile);
const DAY_MS = 24 * 60 * 60 * 1000;

export const DEFAULT_CONFIG = {
  approvalWarningHours: 24,
  approvalErrorHours: 72,
  staleActiveProjectDays: 30,
  refreshMs: Number(process.env.REFRESH_MS || 30000),
  retentionDays: 30,
  noise: {
    hideSuccessfulReads: true,
    hideSuccessfulWebFetches: true,
    hideStatusChecks: true
  },
  logPatterns: ['error', 'failed', 'exception', 'critical', 'fatal', 'timeout', 'unsupported channel', 'approval']
};

function sourceOk(name, detail = '') {
  return { name, status: 'OK', detail, checkedAt: new Date().toISOString() };
}

function sourceError(name, error) {
  return { name, status: 'Erro', detail: String(error?.message || error).slice(0, 500), checkedAt: new Date().toISOString() };
}

function severityFromStatus(status) {
  const text = String(status || '').toLowerCase();
  if (['error', 'failed', 'erro', 'critical', 'fatal'].some((x) => text.includes(x))) return 'Erro';
  if (['disabled', 'skipped', 'warning', 'warn'].some((x) => text.includes(x))) return 'Aviso';
  return 'OK';
}

function compact(text, max = 140) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  return clean.length > max ? clean.slice(0, max - 1) + '…' : clean;
}

function parseCronTable(output) {
  const rows = [];
  for (const line of output.split('\n')) {
    const id = line.match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i)?.[0];
    if (!id) continue;
    const rest = line.slice(line.indexOf(id) + id.length).trim();
    const status = rest.match(/\b(ok|error|idle|disabled|skipped|running)\b/i)?.[1] || 'unknown';
    rows.push({
      id,
      name: compact(rest.split(/\s{2,}/)[0] || rest, 80),
      status,
      enabled: !/\bdisabled\b/i.test(rest),
      severity: severityFromStatus(status),
      scheduleText: compact(rest, 120),
      raw: line
    });
  }
  return rows;
}

function cronText(schedule = {}) {
  if (schedule.kind === 'cron') return `${schedule.expr}${schedule.tz ? ` @ ${schedule.tz}` : ''}`;
  if (schedule.kind === 'every') return `Every ${formatDuration(schedule.everyMs)}`;
  if (schedule.kind === 'at') return `At ${schedule.at}`;
  return 'Unknown schedule';
}

function formatDuration(ms = 0) {
  const minutes = Math.round(ms / 60000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

function normalizeCronJob(job) {
  const status = job.state?.lastRunStatus || job.state?.lastStatus || (job.enabled === false ? 'disabled' : 'idle');
  return {
    id: job.id,
    name: job.name || job.description || job.id,
    description: job.description || '',
    enabled: job.enabled !== false,
    status,
    severity: severityFromStatus(status),
    schedule: job.schedule || {},
    scheduleText: cronText(job.schedule || {}),
    nextRunAt: job.state?.nextRunAtMs ? new Date(job.state.nextRunAtMs).toISOString() : null,
    lastRunAt: job.state?.lastRunAtMs ? new Date(job.state.lastRunAtMs).toISOString() : null,
    delivery: job.delivery || {},
    target: job.sessionTarget || job.sessionKey || '',
    raw: job
  };
}

function startOfWeek(date = new Date()) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - d.getDay());
  return d;
}

function parseCronField(field, min, max) {
  const values = new Set();
  if (!field || field === '*') {
    for (let i = min; i <= max; i++) values.add(i);
    return values;
  }
  for (const part of String(field).split(',')) {
    const [rangePart, stepPart] = part.split('/');
    const step = Number(stepPart || 1);
    let start = min;
    let end = max;
    if (rangePart !== '*') {
      if (rangePart.includes('-')) {
        const [a, b] = rangePart.split('-').map(Number);
        start = Number.isFinite(a) ? a : min;
        end = Number.isFinite(b) ? b : max;
      } else {
        const n = Number(rangePart);
        if (Number.isFinite(n)) start = end = n;
      }
    }
    for (let i = start; i <= end; i += step || 1) {
      if (i >= min && i <= max) values.add(i);
    }
  }
  return values;
}

function jobColor(name = '') {
  const colors = ['orange', 'blue', 'green', 'purple', 'red', 'slate'];
  let hash = 0;
  for (const char of name) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
  return colors[Math.abs(hash) % colors.length];
}

function makeCalendarEvent(job, date) {
  return {
    id: `${job.id}:${date.toISOString()}`,
    jobId: job.id,
    title: job.name,
    time: date.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' }),
    iso: date.toISOString(),
    severity: job.severity || 'OK',
    color: jobColor(job.name),
    scheduleText: job.scheduleText,
    status: job.status,
    enabled: job.enabled !== false
  };
}

function buildScheduleCalendar(crons) {
  const weekStart = startOfWeek();
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(weekStart);
    date.setDate(weekStart.getDate() + index);
    return { date: date.toISOString(), label: date.toLocaleDateString('en-US', { weekday: 'short' }), events: [] };
  });
  const alwaysRunning = [];

  for (const job of crons.filter((cron) => cron.enabled !== false)) {
    const schedule = job.schedule || {};
    if (schedule.kind === 'every') {
      alwaysRunning.push({ id: job.id, title: job.name, scheduleText: job.scheduleText, severity: job.severity, color: jobColor(job.name) });
      continue;
    }
    if (schedule.kind === 'at' && schedule.at) {
      const date = new Date(schedule.at);
      const offset = Math.floor((startOfWeek(date) - weekStart) / (7 * DAY_MS));
      const dayIndex = Math.floor((new Date(date).setHours(0, 0, 0, 0) - weekStart) / DAY_MS);
      if (offset === 0 && days[dayIndex]) days[dayIndex].events.push(makeCalendarEvent(job, date));
      continue;
    }
    if (schedule.kind !== 'cron' || !schedule.expr) continue;
    const [minField, hourField, domField, monField, dowField] = schedule.expr.trim().split(/\s+/);
    if (!dowField) continue;
    const minutes = parseCronField(minField, 0, 59);
    const hours = parseCronField(hourField, 0, 23);
    const dom = parseCronField(domField, 1, 31);
    const mon = parseCronField(monField, 1, 12);
    const dow = parseCronField(dowField, 0, 7);
    for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
      const date = new Date(weekStart);
      date.setDate(weekStart.getDate() + dayIndex);
      const dayOfWeek = date.getDay();
      const cronDow = dayOfWeek === 0 ? [0, 7] : [dayOfWeek];
      const matchesDow = dowField === '*' || cronDow.some((value) => dow.has(value));
      const matchesDom = domField === '*' || dom.has(date.getDate());
      if (!matchesDow || !matchesDom || !mon.has(date.getMonth() + 1)) continue;
      for (const hour of hours) {
        for (const minute of minutes) {
          if (days[dayIndex].events.length > 24) continue;
          const occurrence = new Date(date);
          occurrence.setHours(hour, minute, 0, 0);
          days[dayIndex].events.push(makeCalendarEvent(job, occurrence));
        }
      }
    }
  }
  for (const day of days) day.events.sort((a, b) => a.iso.localeCompare(b.iso));
  return { weekStart: weekStart.toISOString(), alwaysRunning, days };
}

export async function collectCrons() {
  try {
    const { stdout, stderr } = await execFileAsync('openclaw', ['cron', 'list', '--json'], { timeout: 9000, maxBuffer: 3 * 1024 * 1024 });
    const parsed = JSON.parse(stdout);
    const crons = (parsed.jobs || []).map(normalizeCronJob);
    return {
      source: sourceOk('cron scheduler', `${crons.length} jobs via openclaw cron list --json`),
      crons,
      calendar: buildScheduleCalendar(crons),
      events: crons.map((cron) => ({
        id: `cron:${cron.id}:${cron.status}:${cron.nextRunAt || ''}`,
        ts: cron.lastRunAt || cron.nextRunAt || new Date().toISOString(),
        type: 'cron',
        severity: cron.severity,
        title: `Cron ${cron.status}: ${cron.name}`,
        detail: `${cron.scheduleText}${cron.nextRunAt ? ` · next ${cron.nextRunAt}` : ''}`,
        technical: { id: cron.id, schedule: cron.schedule, state: cron.raw?.state, stderr }
      }))
    };
  } catch (jsonError) {
    try {
      const { stdout, stderr } = await execFileAsync('openclaw', ['cron', 'list'], { timeout: 9000, maxBuffer: 1024 * 1024 });
      const crons = parseCronTable(stdout);
      return {
        source: sourceOk('cron scheduler', `${crons.length} jobs via openclaw cron list`),
        crons,
        calendar: buildScheduleCalendar(crons),
        events: crons.map((cron) => ({
          id: `cron:${cron.id}:${cron.status}`,
          ts: new Date().toISOString(),
          type: 'cron',
          severity: cron.severity,
          title: `Cron ${cron.status}: ${cron.name}`,
          detail: cron.raw,
          technical: { id: cron.id, raw: cron.raw, stderr }
        }))
      };
    } catch (error) {
      const detail = error?.code === 'ENOENT'
        ? 'OpenClaw CLI not found inside this container. Run embedded in the Gateway/OpenClaw environment or use an image that includes the openclaw CLI.'
        : (jsonError?.message ? `${jsonError.message}; fallback failed: ${error.message}` : error);
      return { source: sourceError('cron scheduler', detail), crons: [], calendar: buildScheduleCalendar([]), events: [] };
    }
  }
}

async function exists(file) {
  try { await fs.access(file); return true; } catch { return false; }
}

async function readFirstExisting(files) {
  for (const file of files) {
    try { return { file, content: await fs.readFile(file, 'utf8') }; } catch {}
  }
  return null;
}

function findNextAction(text) {
  if (!text) return null;
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean);
  const patterns = [/^next action\s*[:\-]\s*(.+)$/i, /^next\s*[:\-]\s*(.+)$/i, /^todo\s*[:\-]\s*(.+)$/i, /^[-*]\s*\[ \]\s*(.+)$/i, /^[-*]\s*(todo|next|fixme)\b[:\-]?\s*(.+)$/i];
  for (const line of lines) {
    for (const pattern of patterns) {
      const match = line.match(pattern);
      if (match) return compact(match[2] || match[1], 160);
    }
  }
  return null;
}

function inferStatus(projectJson, text, latestMs, config) {
  if (projectJson?.status) return projectJson.status;
  const lower = String(text || '').toLowerCase();
  if (/(blocked|bloqueado|error|failed|critical|fatal)/.test(lower)) return 'blocked';
  if (/\[ \]|todo|next action|próxima ação|proxima acao/.test(lower)) return 'active';
  if (Date.now() - latestMs > config.staleActiveProjectDays * DAY_MS) return 'unknown';
  return 'active';
}

async function latestMtime(dir) {
  let latest = 0;
  async function walk(current, depth = 0) {
    if (depth > 3) return;
    let entries = [];
    try { entries = await fs.readdir(current, { withFileTypes: true }); } catch { return; }
    for (const entry of entries) {
      if (entry.name === 'node_modules' || entry.name === '.git') continue;
      const full = path.join(current, entry.name);
      try {
        const stat = await fs.stat(full);
        latest = Math.max(latest, stat.mtimeMs);
        if (entry.isDirectory()) await walk(full, depth + 1);
      } catch {}
    }
  }
  await walk(dir);
  return latest || Date.now();
}

export async function collectProjects(workspaceDir, config = DEFAULT_CONFIG, cacheDir = null) {
  const projectsDir = path.join(workspaceDir, 'projects');
  const overrides = cacheDir ? await readProjectOverrides(cacheDir) : {};
  try {
    const entries = await fs.readdir(projectsDir, { withFileTypes: true });
    const projectDirs = entries.filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name));
    const projects = [];
    for (const entry of projectDirs) {
      const dir = path.join(projectsDir, entry.name);
      const projectJsonPath = path.join(dir, 'project.json');
      let projectJson = null;
      try { projectJson = JSON.parse(await fs.readFile(projectJsonPath, 'utf8')); } catch {}
      const doc = await readFirstExisting([
        path.join(dir, 'README.md'),
        path.join(dir, 'TODO.md'),
        path.join(dir, 'todo.md'),
        path.join(dir, 'data', 'state.json'),
        path.join(dir, 'state', 'latest_release_meta.json')
      ]);
      const combined = [projectJson ? JSON.stringify(projectJson) : '', doc?.content || ''].join('\n');
      const latest = await latestMtime(dir);
      const override = overrides[entry.name] || {};
      const status = override.status || inferStatus(projectJson, combined, latest, config);
      const nextAction = override.nextAction || projectJson?.nextAction || findNextAction(combined) || 'não definido / precisa de organização';
      const hasMetadata = Boolean(projectJson) || Boolean(await exists(path.join(dir, 'README.md')));
      const importantFiles = [];
      for (const name of ['project.json', 'README.md', 'TODO.md', 'todo.md', 'data/state.json']) {
        if (await exists(path.join(dir, name))) importantFiles.push(name);
      }
      const stale = status === 'active' && Date.now() - latest > config.staleActiveProjectDays * DAY_MS;
      projects.push({
        name: projectJson?.name || entry.name,
        slug: entry.name,
        status,
        severity: stale ? 'Aviso' : severityFromStatus(status),
        updatedAt: new Date(latest).toISOString(),
        nextAction,
        importantFiles,
        organization: override.organization || (hasMetadata && projectJson ? 'OK' : 'precisa de organização'),
        organizationNote: override.note || '',
        editable: true,
        risks: stale ? [`Sem atualização há mais de ${config.staleActiveProjectDays} dias`] : []
      });
    }
    const detail = projectDirs.length
      ? `${projects.length} projects from ${projectsDir}`
      : `0 project directories found in ${projectsDir}; check Docker bind mount / WORKSPACE_DIR`;
    const source = sourceOk('workspace projects', detail);
    if (!projectDirs.length) source.status = 'Aviso';
    return { source, projects };
  } catch (error) {
    const enriched = new Error(`${error.message} (workspaceDir=${workspaceDir}, projectsDir=${projectsDir})`);
    return { source: sourceError('workspace projects', enriched), projects: [] };
  }
}

export async function collectLogs(openclawDir, cacheDir, config = DEFAULT_CONFIG) {
  const logDir = path.join(openclawDir, 'logs');
  const missionLog = path.join(cacheDir, 'mission-control.log');
  const candidates = [path.join(logDir, 'commands.log'), path.join(logDir, 'config-audit.jsonl'), missionLog];
  const events = [];
  const errors = [];
  for (const file of candidates) {
    try {
      const raw = await fs.readFile(file, 'utf8');
      const lines = raw.split('\n').filter(Boolean).slice(-500);
      for (const [index, line] of lines.entries()) {
        const lower = line.toLowerCase();
        const matched = config.logPatterns.find((pattern) => lower.includes(pattern));
        let parsed = null;
        try { parsed = JSON.parse(line); } catch {}
        const ts = parsed?.timestamp || parsed?.ts || new Date().toISOString();
        if (matched) {
          const event = {
            id: `log:${file}:${index}:${line.slice(0, 80)}`,
            ts,
            type: 'log',
            severity: /critical|fatal|exception|unsupported channel|failed|error/.test(lower) ? 'Erro' : 'Aviso',
            title: `Log ${matched}: ${path.basename(file)}`,
            detail: compact(line, 500),
            technical: { file, line }
          };
          events.push(event);
          if (event.severity === 'Erro') errors.push(event);
        } else if (parsed?.action === 'new') {
          events.push({
            id: `activity:${parsed.timestamp}:${parsed.sessionKey}`,
            ts,
            type: 'activity',
            severity: 'OK',
            title: `Nova sessão ${parsed.source || ''}`.trim(),
            detail: parsed.sessionKey,
            technical: parsed
          });
        }
      }
    } catch {}
  }
  return { source: sourceOk('logs', `${events.length} recent signals`), logEvents: events, logErrors: errors };
}

export async function collectApprovals() {
  return {
    source: sourceOk('approvals', 'approval source not writable; read-only POC placeholder'),
    approvals: []
  };
}

export function summarize(snapshot, cachedEvents) {
  const now = Date.now();
  const since24 = now - DAY_MS;
  const since7 = now - 7 * DAY_MS;
  const events24 = cachedEvents.filter((event) => Date.parse(event.ts || 0) >= since24);
  const events7 = cachedEvents.filter((event) => Date.parse(event.ts || 0) >= since7);
  const attention = [];
  for (const source of snapshot.sources) {
    if (source.status !== 'OK') attention.push({ severity: 'Erro', title: `${source.name} indisponível`, detail: source.detail });
  }
  for (const cron of snapshot.crons) {
    if (cron.severity !== 'OK') attention.push({ severity: cron.severity, title: `Cron: ${cron.name}`, detail: cron.raw });
  }
  for (const project of snapshot.projects) {
    if (project.severity !== 'OK' || project.organization !== 'OK') attention.push({ severity: project.severity === 'Erro' ? 'Erro' : 'Aviso', title: `Projeto: ${project.name}`, detail: project.risks[0] || project.organization });
  }
  for (const event of snapshot.logErrors.slice(0, 20)) {
    attention.push({ severity: event.severity, title: event.title, detail: event.detail });
  }
  return {
    attention: attention.sort((a, b) => (a.severity === 'Erro' ? -1 : 1) - (b.severity === 'Erro' ? -1 : 1)),
    summary24h: {
      totalEvents: events24.length,
      errors: events24.filter((event) => event.severity === 'Erro').length,
      warnings: events24.filter((event) => event.severity === 'Aviso').length,
      cronsOk: snapshot.crons.filter((cron) => cron.severity === 'OK').length,
      cronsProblem: snapshot.crons.filter((cron) => cron.severity !== 'OK').length,
      approvals: snapshot.approvals.length
    },
    history7d: {
      totalEvents: events7.length,
      bySeverity: {
        OK: events7.filter((event) => event.severity === 'OK').length,
        Aviso: events7.filter((event) => event.severity === 'Aviso').length,
        Erro: events7.filter((event) => event.severity === 'Erro').length
      }
    }
  };
}
