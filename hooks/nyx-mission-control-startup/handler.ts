import { spawn } from "node:child_process";
import fs from "node:fs/promises";

const DEFAULT_SCRIPT = "/data/.openclaw/workspace/projects/nyx-mission-control/scripts/start-embedded.sh";

async function exists(path: string) {
  try {
    await fs.access(path);
    return true;
  } catch {
    return false;
  }
}

const handler = async (event: any) => {
  if (event?.type !== "gateway" || event?.action !== "startup") {
    return;
  }

  const workspaceDir = event?.context?.workspaceDir || "/data/.openclaw/workspace";
  const script = `${workspaceDir}/projects/nyx-mission-control/scripts/start-embedded.sh`;
  const scriptPath = (await exists(script)) ? script : DEFAULT_SCRIPT;

  if (!(await exists(scriptPath))) {
    console.warn(`[nyx-mission-control-startup] start script not found: ${scriptPath}`);
    return;
  }

  try {
    const child = spawn("sh", [scriptPath], {
      detached: true,
      stdio: "ignore",
      env: {
        ...process.env,
        NYX_MC_APP_DIR: `${workspaceDir}/projects/nyx-mission-control`,
        WORKSPACE_DIR: workspaceDir,
        OPENCLAW_DIR: process.env.OPENCLAW_DIR || "/data/.openclaw",
      },
    });
    child.unref();
    console.log(`[nyx-mission-control-startup] launch requested via ${scriptPath}`);
  } catch (err) {
    console.warn("[nyx-mission-control-startup] failed:", err instanceof Error ? err.message : String(err));
  }
};

export default handler;
