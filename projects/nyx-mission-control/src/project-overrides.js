import fs from 'node:fs/promises';
import path from 'node:path';

function overrideFile(cacheDir) {
  return path.join(cacheDir, 'project-overrides.json');
}

export async function readProjectOverrides(cacheDir) {
  try {
    const raw = await fs.readFile(overrideFile(cacheDir), 'utf8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (error) {
    if (error.code === 'ENOENT') return {};
    throw error;
  }
}

export async function updateProjectOverride(cacheDir, slug, patch) {
  if (!slug || !/^[a-zA-Z0-9._-]+$/.test(slug)) throw new Error('Invalid project slug');
  const overrides = await readProjectOverrides(cacheDir);
  const existing = overrides[slug] || {};
  const clean = {
    ...existing,
    status: String(patch.status ?? existing.status ?? '').trim(),
    organization: String(patch.organization ?? existing.organization ?? '').trim(),
    nextAction: String(patch.nextAction ?? existing.nextAction ?? '').trim(),
    note: String(patch.note ?? existing.note ?? '').trim(),
    updatedAt: new Date().toISOString()
  };
  for (const key of ['status', 'organization', 'nextAction', 'note']) {
    if (!clean[key]) delete clean[key];
  }
  if (Object.keys(clean).length === 1 && clean.updatedAt) delete overrides[slug];
  else overrides[slug] = clean;
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.writeFile(overrideFile(cacheDir), JSON.stringify(overrides, null, 2) + '\n');
  return { slug, override: overrides[slug] || null };
}
