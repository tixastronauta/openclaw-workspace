import fs from 'node:fs/promises';
import path from 'node:path';

function mappingFile(cacheDir) {
  return path.join(cacheDir, 'cron-projects.json');
}

export async function readCronProjectMap(cacheDir) {
  try {
    const raw = await fs.readFile(mappingFile(cacheDir), 'utf8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (error) {
    if (error.code === 'ENOENT') return {};
    throw error;
  }
}

export async function updateCronProject(cacheDir, cronId, projectSlug) {
  if (!cronId || !/^[a-zA-Z0-9:_@.-]+$/.test(cronId)) throw new Error('Invalid cron id');
  if (projectSlug && !/^[a-zA-Z0-9._-]+$/.test(projectSlug)) throw new Error('Invalid project slug');
  const map = await readCronProjectMap(cacheDir);
  if (projectSlug) map[cronId] = projectSlug;
  else delete map[cronId];
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.writeFile(mappingFile(cacheDir), JSON.stringify(map, null, 2) + '\n');
  return { cronId, projectSlug: map[cronId] || null };
}

function normalizeText(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

export function annotateCronsWithProjects(crons, projects, map = {}) {
  const projectHints = projects.map((project) => ({
    slug: project.slug,
    name: project.name,
    needles: [normalizeText(project.slug), normalizeText(project.name)].filter(Boolean)
  }));

  return crons.map((cron) => {
    const manual = map[cron.id];
    const haystack = normalizeText([
      cron.name,
      cron.description,
      cron.scheduleText,
      cron.raw?.payload?.message,
      cron.raw?.payload?.text,
      cron.raw?.description
    ].filter(Boolean).join(' '));
    const inferred = projectHints.find((project) => project.needles.some((needle) => needle && haystack.includes(needle)));
    const projectSlug = manual || inferred?.slug || '';
    const projectName = projects.find((project) => project.slug === projectSlug)?.name || '';
    return {
      ...cron,
      projectSlug,
      projectName,
      projectSource: manual ? 'manual' : (inferred ? 'inferred' : 'none')
    };
  });
}
