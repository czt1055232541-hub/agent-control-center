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
  addTypingReaction(messageId: string): Promise<CliResult> {
    return this.run([
      "api",
      "POST",
      `/open-apis/im/v1/messages/${messageId}/reactions`,
      "--data",
      JSON.stringify({ reaction_type: { emoji_type: "Typing" } }),
      "--as",
      this.config.larkIdentity
    ]);
  }

  removeTypingReaction(messageId: string, reactionId: string): Promise<CliResult> {
    return this.run([
      "api",
      "DELETE",
      `/open-apis/im/v1/messages/${messageId}/reactions/${reactionId}`,
      "--as",
      this.config.larkIdentity
    ]);
  }

  downloadMessageResource(messageId: string, fileKey: string, type: "image" | "file", output: string): Promise<CliResult> {
    return this.run([
      "im",
      "+messages-resources-download",
      "--message-id",
      messageId,
      "--file-key",
      fileKey,
      "--type",
      type,
      "--output",
      output,
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
  timeoutMs = 60_000,
  events: { onStdout?: (text: string) => void; onStderr?: (text: string) => void } = {}
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
      if (timer) {
        clearTimeout(timer);
      }
      resolve(result);
    };
    const timer =
      timeoutMs > 0
        ? setTimeout(() => {
            finish({ ok: false, code: null, stdout, stderr: `${stderr}Command timed out after ${timeoutMs}ms; process was left running by policy.` });
          }, timeoutMs)
        : undefined;
    child.stdout.on("data", (chunk: Buffer | string) => {
      const text = decodeCliChunk(chunk, outputEncoding);
      stdout += text;
      events.onStdout?.(text);
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      const text = decodeCliChunk(chunk, outputEncoding);
      stderr += text;
      events.onStderr?.(text);
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
