import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export const TASK_COLUMNS = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'todo', title: 'To do' },
  { id: 'in_progress', title: 'In progress' },
  { id: 'blocked', title: 'Blocked' },
  { id: 'done', title: 'Done' }
];

const OWNERS = new Set(['tiago', 'nyx']);
const STATUSES = new Set(TASK_COLUMNS.map((column) => column.id));
const DISCORD_TASK_CHANNEL = process.env.NYX_MC_TASK_NOTIFY_CHANNEL || '1485664101756833902';

function nowIso() {
  return new Date().toISOString();
}

function taskFile(cacheDir) {
  return path.join(cacheDir, 'tasks.json');
}

function auditFile(cacheDir) {
  return path.join(cacheDir, 'task-events.jsonl');
}

function makeId() {
  return `task_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function sanitizeTask(input, existing = {}) {
  const title = String(input.title ?? existing.title ?? '').trim();
  if (!title) throw new Error('Task title is required');
  const owner = String(input.owner ?? existing.owner ?? 'tiago').toLowerCase();
  if (!OWNERS.has(owner)) throw new Error('Owner must be tiago or nyx');
  const status = String(input.status ?? existing.status ?? 'backlog');
  if (!STATUSES.has(status)) throw new Error(`Invalid status: ${status}`);
  return {
    ...existing,
    title,
    owner,
    status,
    description: String(input.description ?? existing.description ?? '').trim(),
    project: String(input.project ?? existing.project ?? '').trim(),
    priority: String(input.priority ?? existing.priority ?? 'normal').trim() || 'normal'
  };
}

export async function readTasks(cacheDir) {
  try {
    const raw = await fs.readFile(taskFile(cacheDir), 'utf8');
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed.tasks) ? parsed.tasks : [];
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
}

async function writeTasks(cacheDir, tasks) {
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.writeFile(taskFile(cacheDir), JSON.stringify({ tasks }, null, 2) + '\n');
}

async function audit(cacheDir, event) {
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.appendFile(auditFile(cacheDir), JSON.stringify(event) + '\n');
}

function ownerLabel(owner) {
  return owner === 'nyx' ? 'Nyx' : 'Tiago';
}

function statusLabel(status) {
  return TASK_COLUMNS.find((column) => column.id === status)?.title || status;
}

async function notifyDiscord(event) {
  const task = event.task;
  const lines = [];
  if (event.kind === 'task_created') {
    lines.push(`🧩 **Task criada**: ${task.title}`);
    lines.push(`Responsável: **${ownerLabel(task.owner)}** · Estado: **${statusLabel(task.status)}**`);
  } else if (event.kind === 'task_moved') {
    lines.push(`🔀 **Task movida**: ${task.title}`);
    lines.push(`Responsável: **${ownerLabel(task.owner)}** · **${statusLabel(event.from)}** → **${statusLabel(event.to)}**`);
  } else if (event.kind === 'task_updated') {
    lines.push(`✏️ **Task atualizada**: ${task.title}`);
    lines.push(`Responsável: **${ownerLabel(task.owner)}** · Estado: **${statusLabel(task.status)}**`);
  }
  if (task.project) lines.push(`Projeto: ${task.project}`);
  if (task.owner === 'nyx' && event.kind === 'task_created') {
    lines.push('Nota: atribuída à Nyx — entra na fila de execução dela.');
  }

  try {
    await execFileAsync('openclaw', [
      'message', 'send',
      '--channel', 'discord',
      '--target', DISCORD_TASK_CHANNEL,
      '--message', lines.join('\n')
    ], { timeout: 10000, maxBuffer: 256 * 1024 });
    return { ok: true };
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
}

export async function createTask(cacheDir, input) {
  const tasks = await readTasks(cacheDir);
  const createdAt = nowIso();
  const task = {
    ...sanitizeTask(input),
    id: makeId(),
    createdAt,
    updatedAt: createdAt,
    history: [{ ts: createdAt, kind: 'created', status: input.status || 'backlog', owner: input.owner || 'tiago' }]
  };
  tasks.unshift(task);
  await writeTasks(cacheDir, tasks);
  const event = { ts: nowIso(), kind: 'task_created', task };
  const notification = await notifyDiscord(event);
  await audit(cacheDir, { ...event, notification });
  return { task, notification };
}

export async function updateTask(cacheDir, id, patch) {
  const tasks = await readTasks(cacheDir);
  const index = tasks.findIndex((task) => task.id === id);
  if (index === -1) throw new Error('Task not found');
  const before = tasks[index];
  const next = {
    ...sanitizeTask(patch, before),
    id: before.id,
    createdAt: before.createdAt,
    updatedAt: nowIso(),
    history: [...(before.history || [])]
  };
  let kind = 'task_updated';
  if (before.status !== next.status) {
    kind = 'task_moved';
    next.history.push({ ts: next.updatedAt, kind: 'moved', from: before.status, to: next.status, owner: next.owner });
  } else {
    next.history.push({ ts: next.updatedAt, kind: 'updated', owner: next.owner });
  }
  tasks[index] = next;
  await writeTasks(cacheDir, tasks);
  const event = { ts: nowIso(), kind, from: before.status, to: next.status, task: next };
  const notification = before.status !== next.status ? await notifyDiscord(event) : { ok: true, skipped: 'not a move' };
  await audit(cacheDir, { ...event, notification });
  return { task: next, notification };
}

export async function getTaskBoard(cacheDir) {
  const tasks = await readTasks(cacheDir);
  return {
    columns: TASK_COLUMNS.map((column) => ({
      ...column,
      tasks: tasks.filter((task) => task.status === column.id)
    })),
    tasks
  };
}
