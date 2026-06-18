import { spawn } from "node:child_process";
import type { AppConfig } from "./env.js";
import type { CliResult } from "./types.js";
import { decodeCliChunk } from "./cliText.js";

export class LarkCli {
  constructor(private readonly config: AppConfig) {}

  run(args: string[], options: { input?: string; dryRun?: boolean } = {}): Promise<CliResult> {
    const dryRun = options.dryRun ?? this.config.dryRun;
    if (dryRun) {
      return Promise.resolve({
        ok: true,
        code: 0,
        stdout: JSON.stringify({ dryRun: true, command: [this.config.larkCliBin, ...args] }),
        stderr: ""
      });
    }
    return spawnCollect(this.config.larkCliBin, args, options.input, this.config.larkCliOutputEncoding);
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

  commandPreview(args: string[]): string {
    return [this.config.larkCliBin, ...args].map(quoteArg).join(" ");
  }
}

export function spawnCollect(command: string, args: string[], input?: string, outputEncoding = "auto"): Promise<CliResult> {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      windowsHide: true,
      env: process.env
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += decodeCliChunk(chunk, outputEncoding);
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += decodeCliChunk(chunk, outputEncoding);
    });
    child.on("error", (error) => {
      resolve({ ok: false, code: null, stdout, stderr: `${stderr}${error.message}` });
    });
    child.on("close", (code) => {
      resolve({ ok: code === 0, code, stdout, stderr });
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
