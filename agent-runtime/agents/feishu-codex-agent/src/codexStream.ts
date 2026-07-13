import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

export type CodexStreamEvent = {
  run_id: string;
  timestamp: string;
  phase: "start" | "stdout" | "stderr" | "complete" | "error";
  stream: "stage" | "stdout" | "stderr";
  text: string;
  message_id?: string;
  chat_type?: string;
};

export type CodexStreamWriter = {
  runId: string;
  filePath: string;
  write: (event: Omit<CodexStreamEvent, "run_id" | "timestamp">) => void;
};

export function createCodexStreamWriter(context: { messageId?: string; chatType?: string } = {}): CodexStreamWriter {
  const runId = newRunId();
  const dir = codexStreamDir();
  fs.mkdirSync(dir, { recursive: true });
  const filePath = path.join(dir, `${runId}.jsonl`);
  const base = {
    run_id: runId,
    message_id: context.messageId,
    chat_type: context.chatType
  };
  const writer: CodexStreamWriter = {
    runId,
    filePath,
    write(event) {
      const payload: CodexStreamEvent = {
        ...base,
        timestamp: new Date().toISOString(),
        ...event
      };
      fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`, "utf8");
    }
  };
  writer.write({ phase: "start", stream: "stage", text: "Codex CLI run started." });
  pruneOldStreams(dir, 30);
  return writer;
}

function newRunId(): string {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  return `${stamp}-${randomUUID().slice(0, 8)}`;
}

function codexStreamDir(): string {
  const configured = process.env.ACC_STACK_ROOT;
  const stackRoot = configured && configured.trim()
    ? configured
    : path.resolve(process.cwd(), "..", "..", "..");
  return path.join(stackRoot, "runtime", "streams", "codex-agent");
}

function pruneOldStreams(dir: string, keep: number): void {
  try {
    const files = fs.readdirSync(dir)
      .filter((name) => name.endsWith(".jsonl"))
      .map((name) => {
        const filePath = path.join(dir, name);
        return { filePath, mtime: fs.statSync(filePath).mtimeMs };
      })
      .sort((a, b) => b.mtime - a.mtime);
    for (const stale of files.slice(keep)) {
      fs.rmSync(stale.filePath, { force: true });
    }
  } catch {
    // Best effort retention only; streaming must never break the agent reply path.
  }
}
