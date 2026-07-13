import { spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import path from "node:path";
import type { AppConfig } from "./env.js";
import { decodeCliChunk } from "./cliText.js";

export type EventConsumerEvents = {
  ready: [string];
  event: [unknown];
  stderr: [string];
  error: [Error];
  close: [number | null, string];
};

export class EventConsumer extends EventEmitter<EventConsumerEvents> {
  private child: ReturnType<typeof spawn> | null = null;
  private ready = false;
  private stderrTail = "";

  constructor(private readonly config: AppConfig) {
    super();
  }

  start(): void {
    const cmdFile = this.config.larkCliBin;
    const cmdArgs = [
      "event",
      "consume",
      "im.message.receive_v1",
      "--as",
      this.config.larkIdentity,
      "--max-events",
      "0",
      "--timeout",
      this.config.larkEventTimeout
    ];
    const child = spawn(cmdFile, cmdArgs, {
      shell: false,
      windowsHide: true,
      env: process.env,
      cwd: this.config.larkCliCwd,
      stdio: ["pipe", "pipe", "pipe"]
    });
    this.child = child;
    let stdoutBuffer = "";
    let stderrBuffer = "";
    child.stdout.on("data", (chunk: Buffer | string) => {
      stdoutBuffer += decodeCliChunk(chunk, this.config.larkCliOutputEncoding);
      const lines = stdoutBuffer.split(/\r?\n/);
      stdoutBuffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          continue;
        }
        try {
          this.emit("event", JSON.parse(trimmed));
        } catch (error) {
          this.emit("error", error instanceof Error ? error : new Error(String(error)));
        }
      }
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      const text = decodeCliChunk(chunk, this.config.larkCliOutputEncoding);
      stderrBuffer += text;
      this.stderrTail = (this.stderrTail + text).slice(-4000);
      this.emit("stderr", text);
      if (!this.ready && this.config.larkReadyMarker.test(stderrBuffer)) {
        this.ready = true;
        this.emit("ready", stderrBuffer);
      }
    });
    child.on("error", (error) => this.emit("error", error));
    child.on("close", (code) => this.emit("close", code, this.stderrTail));
  }

  stop(): void {
    this.child?.kill();
    this.child = null;
  }
}

