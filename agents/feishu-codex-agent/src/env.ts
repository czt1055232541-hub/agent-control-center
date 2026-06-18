import fs from "node:fs";
import path from "node:path";

 export type AppConfig = {
   dryRun: boolean;
   larkCliBin: string;
   larkCliCwd: string;
   larkCliOutputEncoding: string;
   larkEventTimeout: string;
   larkIdentity: "bot" | "user";
   larkReadyMarker: RegExp;
   botName: string;
   botOpenId?: string;
   botUserId?: string;
   botUnionId?: string;
   agentProvider: "local" | "openai" | "codex";
   openaiApiKey?: string;
   openaiModel: string;
   codexCliBin: string;
   codexAgentArgs: string[];
   confirmTimeoutMs: number;
   maxContextMessages: number;
   a2aBots: Array<{ name: string; openId: string; description?: string }>;
   a2aRelay: {
     enabled: boolean;
     groupChatId?: string;
     peerName?: string;
     peerOpenId?: string;
     peerCliHome?: string;
   };
 };

export function loadDotEnv(filePath = path.resolve(process.cwd(), ".env")): void {
  if (!fs.existsSync(filePath)) {
    return;
  }
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const match = /^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(trimmed);
    if (!match) {
      continue;
    }
    const [, key, rawValue] = match;
    if (process.env[key] === undefined) {
      process.env[key] = rawValue.replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
    }
  }
}

export function getConfig(): AppConfig {
  loadDotEnv();
  return {
    dryRun: boolEnv("DRY_RUN", true),
    larkCliBin: process.env.LARK_CLI_BIN || defaultLarkCliBin(),
    larkCliCwd: process.env.LARK_CLI_CWD || path.resolve(process.cwd(), ".."),
    larkCliOutputEncoding: process.env.LARK_CLI_OUTPUT_ENCODING || "auto",
    larkEventTimeout: process.env.LARK_EVENT_TIMEOUT || "8760h",
    larkIdentity: process.env.LARK_IDENTITY === "user" ? "user" : "bot",
    larkReadyMarker: new RegExp(process.env.LARK_READY_MARKER || "ready|listening|connected|waiting|consume|event|\\u542f\\u52a8|\\u76d1\\u542c|\\u7b49\\u5f85", "i"),
    botName: process.env.LARK_BOT_NAME || "Codex",
    botOpenId: emptyToUndefined(process.env.LARK_BOT_OPEN_ID),
    botUserId: emptyToUndefined(process.env.LARK_BOT_USER_ID),
    botUnionId: emptyToUndefined(process.env.LARK_BOT_UNION_ID),
    agentProvider: providerEnv(process.env.AGENT_PROVIDER),
    openaiApiKey: emptyToUndefined(process.env.OPENAI_API_KEY),
    openaiModel: process.env.OPENAI_MODEL || "gpt-4.1-mini",
     codexCliBin: process.env.CODEX_CLI_BIN || "codex",
     codexAgentArgs: splitArgs(process.env.CODEX_AGENT_ARGS || "exec --skip-git-repo-check"),
     confirmTimeoutMs: numberEnv("CONFIRM_TIMEOUT_MS", 600_000),
     maxContextMessages: numberEnv("MAX_CONTEXT_MESSAGES", 30),
     a2aBots: parseA2ABots(process.env.A2A_BOTS || ""),
     a2aRelay: {
       enabled: boolEnv("A2A_RELAY_ENABLED", false),
       groupChatId: emptyToUndefined(process.env.A2A_RELAY_GROUP_CHAT_ID),
       peerName: emptyToUndefined(process.env.A2A_RELAY_PEER_NAME),
       peerOpenId: emptyToUndefined(process.env.A2A_RELAY_PEER_OPEN_ID),
       peerCliHome: emptyToUndefined(process.env.A2A_RELAY_PEER_CLI_HOME)
     }
   };
 }

function defaultLarkCliBin(): string {
  if (process.platform === "win32") {
    const workspaceRoot = path.resolve(process.cwd(), "..");
    const bundledExe = path.join(workspaceRoot, ".npm-global", "node_modules", "@larksuite", "cli", "bin", "lark-cli.exe");
    if (fs.existsSync(bundledExe)) {
      return bundledExe;
    }
  }
  return "lark-cli";
}

function boolEnv(key: string, defaultValue: boolean): boolean {
  const value = process.env[key];
  if (value === undefined || value === "") {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

function numberEnv(key: string, defaultValue: number): number {
  const parsed = Number(process.env[key]);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : defaultValue;
}

function emptyToUndefined(value: string | undefined): string | undefined {
  return value && value.trim() ? value.trim() : undefined;
}

function providerEnv(value: string | undefined): AppConfig["agentProvider"] {
  if (value === "openai" || value === "codex") {
    return value;
  }
  return "local";
}

 function splitArgs(value: string): string[] {
   return value.match(/(?:[^\s"]+|"[^"]*")+/g)?.map((part) => part.replace(/^"|"$/g, "")) ?? [];
 }

 function parseA2ABots(raw: string): Array<{ name: string; openId: string; description?: string }> {
   if (!raw.trim()) {
     return [];
   }
   try {
     const parsed = JSON.parse(raw);
     if (Array.isArray(parsed)) {
       return parsed.filter((b: unknown) => b && typeof b === "object" && (b as Record<string,unknown>).name && (b as Record<string,unknown>).openId);
     }
   } catch {
     // fall back to simple format: name1:openId1,name2:openId2
     return raw.split(",").map((pair) => {
       const [name, openId, description] = pair.split(":").map((s) => s.trim());
       return { name, openId, description };
     }).filter((b) => b.name && b.openId);
   }
   return [];
 }
