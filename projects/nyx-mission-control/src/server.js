import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { EventCache } from './cache.js';
import { DEFAULT_CONFIG, collectApprovals, collectCrons, collectLogs, collectProjects, summarize } from './collectors.js';
import { createTask, getTaskBoard, updateTask } from './tasks.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const publicDir = path.join(rootDir, 'public');
const workspaceDir = process.env.WORKSPACE_DIR || '/data/.openclaw/workspace';
const openclawDir = process.env.OPENCLAW_DIR || '/data/.openclaw';
const cacheDir = process.env.CACHE_DIR || path.join(rootDir, 'data');
const port = Number(process.env.PORT || process.env.NYX_MC_PORT || 4317);
const host = process.env.HOST || process.env.NYX_MC_HOST || '0.0.0.0';
const config = { ...DEFAULT_CONFIG, refreshMs: Number(process.env.REFRESH_MS || DEFAULT_CONFIG.refreshMs) };

const clients = new Set();
const cache = new EventCache(cacheDir, config.retentionDays);
let latestSnapshot = null;
let collecting = false;

async function log(message, extra = {}) {
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.appendFile(path.join(cacheDir, 'mission-control.log'), JSON.stringify({ ts: new Date().toISOString(), message, ...extra }) + '\n');
}

async function buildSnapshot() {
  if (collecting) return latestSnapshot;
  collecting = true;
  try {
    const [cronData, projectData, approvalData, logData] = await Promise.all([
      collectCrons(),
      collectProjects(workspaceDir, config),
      collectApprovals(),
      collectLogs(openclawDir, cacheDir, config)
    ]);
    const sourceEvents = [...cronData.events, ...logData.logEvents];
    await cache.append(sourceEvents);
    const events = await cache.read(1000);
    const snapshot = {
      generatedAt: new Date().toISOString(),
      name: 'Nyx Mission Control',
      config,
      sources: [cronData.source, projectData.source, approvalData.source, logData.source],
      crons: cronData.crons,
      calendar: cronData.calendar,
      projects: projectData.projects,
      approvals: approvalData.approvals,
      logErrors: logData.logErrors,
      activity: events.slice(0, 200)
    };
    Object.assign(snapshot, summarize(snapshot, events));
    latestSnapshot = snapshot;
    broadcast({ type: 'snapshot', snapshot });
    return snapshot;
  } catch (error) {
    await log('snapshot failed', { level: 'error', error: String(error?.stack || error) });
    throw error;
  } finally {
    collecting = false;
  }
}

function broadcast(payload) {
  const data = `data: ${JSON.stringify(payload)}\n\n`;
  for (const client of clients) client.write(data);
}

function sendJson(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(data, null, 2));
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw.trim()) return {};
  return JSON.parse(raw);
}

async function sendStatic(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const requested = url.pathname === '/' ? '/index.html' : decodeURIComponent(url.pathname);
  const file = path.normalize(path.join(publicDir, requested));
  if (!file.startsWith(publicDir)) return sendJson(res, 403, { error: 'Forbidden' });
  try {
    const body = await fs.readFile(file);
    const ext = path.extname(file);
    const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
    res.writeHead(200, { 'content-type': types[ext] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (url.pathname === '/healthz') return sendJson(res, 200, { ok: true, generatedAt: latestSnapshot?.generatedAt || null, sources: latestSnapshot?.sources || [] });
    if (url.pathname === '/api/snapshot') return sendJson(res, 200, latestSnapshot || await buildSnapshot());
    if (url.pathname === '/api/diagnostic') return sendJson(res, 200, { snapshot: latestSnapshot || await buildSnapshot(), env: { workspaceDir, openclawDir, cacheDir, host, port }, note: 'Diagnostic bundle.' });
    if (url.pathname === '/api/refresh' && req.method === 'POST') return sendJson(res, 200, await buildSnapshot());
    if (url.pathname === '/api/tasks' && req.method === 'GET') return sendJson(res, 200, await getTaskBoard(cacheDir));
    if (url.pathname === '/api/tasks' && req.method === 'POST') return sendJson(res, 201, await createTask(cacheDir, await readJsonBody(req)));
    const taskMatch = url.pathname.match(/^\/api\/tasks\/([^/]+)$/);
    if (taskMatch && req.method === 'PATCH') return sendJson(res, 200, await updateTask(cacheDir, taskMatch[1], await readJsonBody(req)));
    if (url.pathname === '/events') {
      res.writeHead(200, {
        'content-type': 'text/event-stream; charset=utf-8',
        'cache-control': 'no-cache, no-transform',
        connection: 'keep-alive'
      });
      res.write(': connected\n\n');
      clients.add(res);
      if (latestSnapshot) res.write(`data: ${JSON.stringify({ type: 'snapshot', snapshot: latestSnapshot })}\n\n`);
      req.on('close', () => clients.delete(res));
      return;
    }
    return sendStatic(req, res);
  } catch (error) {
    await log('request failed', { level: 'error', path: req.url, error: String(error?.stack || error) });
    return sendJson(res, 500, { error: String(error?.message || error) });
  }
});

await cache.init();
await log('mission-control starting', { level: 'info', host, port, workspaceDir, openclawDir });
await buildSnapshot();
setInterval(() => buildSnapshot().catch(() => {}), config.refreshMs);

server.listen(port, host, () => {
  const displayHost = host === '0.0.0.0' ? '127.0.0.1' : host;
  console.log(`Nyx Mission Control listening on http://${displayHost}:${port}`);
});
