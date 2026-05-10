import fs from 'node:fs/promises';
import path from 'node:path';

function assertSlug(slug) {
  if (!slug || !/^[a-zA-Z0-9._-]+$/.test(slug)) throw new Error('Invalid project slug');
}

function projectDir(workspaceDir, slug) {
  assertSlug(slug);
  return path.join(workspaceDir, 'projects', slug);
}

function projectJsonPath(workspaceDir, slug) {
  return path.join(projectDir(workspaceDir, slug), 'project.json');
}

export async function readProjectJson(workspaceDir, slug) {
  const file = projectJsonPath(workspaceDir, slug);
  try {
    return { slug, exists: true, json: JSON.parse(await fs.readFile(file, 'utf8')) };
  } catch (error) {
    if (error.code === 'ENOENT') {
      return {
        slug,
        exists: false,
        json: {
          name: slug,
          status: 'active',
          updatedAt: new Date().toISOString().slice(0, 10),
          nextAction: '',
          owner: 'Nyx',
          priority: 'normal'
        }
      };
    }
    throw error;
  }
}

export async function writeProjectJson(workspaceDir, slug, input) {
  const dir = projectDir(workspaceDir, slug);
  let json = input;
  if (typeof input === 'string') json = JSON.parse(input);
  if (!json || Array.isArray(json) || typeof json !== 'object') throw new Error('project.json must be a JSON object');
  const next = {
    ...json,
    name: String(json.name || slug).trim(),
    status: String(json.status || 'active').trim(),
    updatedAt: String(json.updatedAt || new Date().toISOString().slice(0, 10)).trim()
  };
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(projectJsonPath(workspaceDir, slug), JSON.stringify(next, null, 2) + '\n');
  return { slug, exists: true, json: next };
}
