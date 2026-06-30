import { spawn } from "node:child_process";
import type { AppConfig } from "./env.js";
import type { CliResult } from "./types.js";
import { decodeCliChunk } from "./cliText.js";

export class LarkCli {
  constructor(private readonly config: AppConfig) {}

  run(args: string[], options: { input?: string; dryRun?: boolean; env?: NodeJS.ProcessEnv; timeoutMs?: number } = {}): Promise<CliResult> {
    const dryRun = options.dryRun ?? this.config.dryRun;
    if (dryRun) {
      return Promise.resolve({
        ok: true,
        code: 0,
        stdout: JSON.stringify({ dryRun: true, command: [this.config.larkCliBin, ...args] }),
        stderr: ""
      });
    }
    return spawnCollect(this.config.larkCliBin, args, options.input, this.config.larkCliOutputEncoding, options.env, options.timeoutMs);
  }

  sendText(chatId: string, text: string): Promise<CliResult> {
    return this.run([
      "im",
      "+messages-send",
      "--chat-id",
      chatId,
      "--text",
      text,
      "--as",
      this.config.larkIdentity
    ]);
  }

  sendPost(chatId: string, content: LarkPostContent, options: { env?: NodeJS.ProcessEnv; identity?: "bot" | "user" } = {}): Promise<CliResult> {
    return this.run(
      [
        "im",
        "+messages-send",
        "--chat-id",
        chatId,
        "--content",
        JSON.stringify(content),
        "--msg-type",
        "post",
        "--as",
        options.identity ?? this.config.larkIdentity
      ],
      { env: options.env }
    );
  }

  setTypingStatus(chatId: string, status: "Started" | "Stopped"): Promise<CliResult> {
    return this.run([
      "api",
      "POST",
      "/open-apis/im/v1/typing_status",
      "--data",
      JSON.stringify({ chat_id: chatId, status }),
      "--as",
      this.config.larkIdentity
    ]);
  }

  commandPreview(args: string[]): string {
    return [this.config.larkCliBin, ...args].map(quoteArg).join(" ");
  }
}

export type LarkPostContent = {
  zh_cn: {
    title?: string;
    content: Array<Array<LarkPostElement>>;
  };
};

export type LarkPostElement =
  | { tag: "text"; text: string }
  | { tag: "at"; user_id: string; user_name?: string };

export function spawnCollect(
  command: string,
  args: string[],
  input?: string,
  outputEncoding = "auto",
  env: NodeJS.ProcessEnv = process.env,
  timeoutMs = 60_000
): Promise<CliResult> {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      windowsHide: true,
      env
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (result: CliResult) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, code: null, stdout, stderr: `${stderr}Command timed out after ${timeoutMs}ms` });
    }, timeoutMs);
    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += decodeCliChunk(chunk, outputEncoding);
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += decodeCliChunk(chunk, outputEncoding);
    });
    child.on("error", (error) => {
      finish({ ok: false, code: null, stdout, stderr: `${stderr}${error.message}` });
    });
    child.on("close", (code) => {
      finish({ ok: code === 0, code, stdout, stderr });
    });
    if (input) {
      child.stdin.write(input);
    }
    child.stdin.end();
  });
}

function quoteArg(arg: string): string {
  if (/^[A-Za-z0-9_./:+@=-]+$/.test(arg)) {
    return arg;
  }
  return JSON.stringify(arg);
}
