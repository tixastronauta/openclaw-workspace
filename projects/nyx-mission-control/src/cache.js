import fs from 'node:fs/promises';
import path from 'node:path';

const DAY_MS = 24 * 60 * 60 * 1000;

export class EventCache {
  constructor(cacheDir, retentionDays = 30) {
    this.cacheDir = cacheDir;
    this.retentionMs = retentionDays * DAY_MS;
    this.file = path.join(cacheDir, 'events.jsonl');
    this.seen = new Set();
  }

  async init() {
    await fs.mkdir(this.cacheDir, { recursive: true });
    try {
      const raw = await fs.readFile(this.file, 'utf8');
      for (const line of raw.split('\n')) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.id) this.seen.add(event.id);
        } catch {}
      }
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    await this.purge();
  }

  async append(events) {
    const fresh = [];
    for (const event of events) {
      if (!event?.id || this.seen.has(event.id)) continue;
      this.seen.add(event.id);
      fresh.push({ ...event, cachedAt: new Date().toISOString() });
    }
    if (!fresh.length) return [];
    await fs.appendFile(this.file, fresh.map((event) => JSON.stringify(event)).join('\n') + '\n');
    return fresh;
  }

  async read(limit = 500) {
    try {
      const raw = await fs.readFile(this.file, 'utf8');
      return raw
        .split('\n')
        .filter(Boolean)
        .map((line) => {
          try { return JSON.parse(line); } catch { return null; }
        })
        .filter(Boolean)
        .sort((a, b) => Date.parse(b.ts || 0) - Date.parse(a.ts || 0))
        .slice(0, limit);
    } catch (error) {
      if (error.code === 'ENOENT') return [];
      throw error;
    }
  }

  async purge() {
    const cutoff = Date.now() - this.retentionMs;
    const events = await this.read(50000);
    const kept = events
      .filter((event) => Date.parse(event.ts || event.cachedAt || 0) >= cutoff)
      .sort((a, b) => Date.parse(a.ts || 0) - Date.parse(b.ts || 0));
    await fs.writeFile(this.file, kept.map((event) => JSON.stringify(event)).join('\n') + (kept.length ? '\n' : ''));
    this.seen = new Set(kept.map((event) => event.id).filter(Boolean));
  }
}
