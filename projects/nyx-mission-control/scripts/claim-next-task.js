#!/usr/bin/env node
import path from 'node:path';
import { claimNextNyxTask } from '../src/tasks.js';

const appDir = process.env.NYX_MC_APP_DIR || '/data/.openclaw/workspace/projects/nyx-mission-control';
const cacheDir = process.env.CACHE_DIR || path.join(appDir, 'data');

const task = await claimNextNyxTask(cacheDir);
if (!task) {
  console.log('NO_TASK');
} else {
  console.log(JSON.stringify({ claimed: true, task }, null, 2));
}
