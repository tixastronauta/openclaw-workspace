#!/usr/bin/env node
import path from 'node:path';
import { finishTaskExecution } from '../src/tasks.js';

const args = process.argv.slice(2);
function arg(name, fallback = '') {
  const index = args.indexOf(`--${name}`);
  return index >= 0 ? args[index + 1] : fallback;
}

const id = arg('id');
const status = arg('status');
const summary = arg('summary');
const blockedReason = arg('blocked-reason');
if (!id || !status) {
  console.error('Usage: finish-task.js --id <taskId> --status <done|blocked> --summary <summary> [--blocked-reason <reason>]');
  process.exit(2);
}

const appDir = process.env.NYX_MC_APP_DIR || '/data/.openclaw/workspace/projects/nyx-mission-control';
const cacheDir = process.env.CACHE_DIR || path.join(appDir, 'data');
const task = await finishTaskExecution(cacheDir, id, { status, summary, blockedReason });
console.log(JSON.stringify({ finished: true, task }, null, 2));
