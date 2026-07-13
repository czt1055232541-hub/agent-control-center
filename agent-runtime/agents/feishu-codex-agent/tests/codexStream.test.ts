import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { draftAgentResponse } from "../src/agent.js";
import { getConfig } from "../src/env.js";
import type { RouteResult } from "../src/types.js";

test("codex provider records subprocess stdout stderr and completion events", async () => {
  const stackRoot = fs.mkdtempSync(path.join(os.tmpdir(), "acc-codex-stream-"));
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-stream-mock-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "process.stdout.write('STDOUT_FROM_TEST');",
      "process.stderr.write('STDERR_FROM_TEST');",
      "if (output) fs.writeFileSync(output, 'FINAL_FROM_TEST');"
    ].join("\n"),
    "utf8"
  );
  const previous = process.env.ACC_STACK_ROOT;
  process.env.ACC_STACK_ROOT = stackRoot;
  try {
    const route: RouteResult = {
      intent: "unknown",
      cleanText: "stream test",
      plan: { title: "stream", commands: [], executable: true, requiresConfirmation: false, responsePreview: "stream" },
      context: { chatType: "group", messageId: "om_test", isPrivate: false, senderIsA2ABot: false }
    };
    const response = await draftAgentResponse(
      {
        ...getConfig(),
        agentProvider: "codex",
        codexCliBin: process.execPath,
        codexAgentArgs: [scriptPath],
        codexCliTimeoutMs: 10_000
      },
      route
    );
    assert.equal(response, "FINAL_FROM_TEST");
    const streamDir = path.join(stackRoot, "runtime", "streams", "codex-agent");
    const files = fs.readdirSync(streamDir).filter((name) => name.endsWith(".jsonl"));
    assert.equal(files.length, 1);
    const events = fs.readFileSync(path.join(streamDir, files[0]), "utf8").trim().split(/\r?\n/).map((line) => JSON.parse(line));
    assert.deepEqual(events.map((event) => event.phase), ["start", "stdout", "stderr", "complete"]);
    assert.equal(events[0].message_id, "om_test");
    assert.equal(events[1].text, "STDOUT_FROM_TEST");
    assert.equal(events[2].text, "STDERR_FROM_TEST");
  } finally {
    if (previous === undefined) {
      delete process.env.ACC_STACK_ROOT;
    } else {
      process.env.ACC_STACK_ROOT = previous;
    }
    fs.rmSync(scriptPath, { force: true });
    fs.rmSync(stackRoot, { recursive: true, force: true });
  }
});
