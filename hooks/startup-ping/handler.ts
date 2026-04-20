import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CHANNEL = "telegram";
const TARGET = "6384494297";
const MESSAGE = "Nyx ressuscitou 😼";

async function loadRouteReply() {
  const distDir = "/app/dist";
  const entries = await fs.readdir(distDir);
  const runtimeFile = entries.find((name) => name.startsWith("route-reply.runtime-") && name.endsWith(".js"));
  if (!runtimeFile) {
    throw new Error("route-reply runtime module not found");
  }

  const mod = await import(pathToFileURL(path.join(distDir, runtimeFile)).href);
  if (typeof mod.routeReply !== "function") {
    throw new Error("routeReply export not found");
  }

  return mod.routeReply as (params: {
    payload: { text: string };
    channel: string;
    to: string;
    cfg: unknown;
    accountId?: string;
    sessionKey?: string;
    threadId?: string;
  }) => Promise<unknown>;
}

const handler = async (event: any) => {
  if (event?.type !== "gateway" || event?.action !== "startup") {
    return;
  }

  const cfg = event?.context?.cfg;
  if (!cfg) {
    return;
  }

  try {
    const routeReply = await loadRouteReply();
    await routeReply({
      payload: { text: MESSAGE },
      channel: CHANNEL,
      to: TARGET,
      cfg,
    });
  } catch (err) {
    console.warn("[startup-ping] failed:", err instanceof Error ? err.message : String(err));
  }
};

export default handler;
