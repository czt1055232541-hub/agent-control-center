import { getConfig } from "./env.js";
import { EventConsumer } from "./eventConsumer.js";
import { LarkCli } from "./larkCli.js";
import { MessageHandler } from "./handler.js";

const config = getConfig();
const larkCli = new LarkCli(config);
const handler = new MessageHandler(config, larkCli);
const consumer = new EventConsumer(config);

consumer.on("ready", (marker) => {
  console.error(`[agent] lark-cli event consumer ready: ${marker.split(/\r?\n/).at(-1) ?? "ready"}`);
});

consumer.on("stderr", (chunk) => {
  if (process.env.LOG_LEVEL === "debug") {
    console.error(`[lark-cli] ${chunk}`);
  }
});

consumer.on("event", (event) => {
  handler.handleRaw(event).catch((error) => {
    console.error("[agent] failed to handle event", error);
  });
});

consumer.on("error", (error) => {
  console.error("[agent] event consumer error", error);
});

consumer.on("close", (code, stderrTail) => {
  console.error(`[agent] event consumer exited with code ${code}`);
  if (code !== 0 && stderrTail.trim()) {
    console.error(`[agent] lark-cli stderr tail:\n${stderrTail.trim()}`);
  }
  process.exitCode = code ?? 1;
});

process.on("SIGINT", () => {
  consumer.stop();
  process.exit(0);
});

consumer.start();
