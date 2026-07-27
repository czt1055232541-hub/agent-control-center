import test from "node:test";
import assert from "node:assert/strict";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "../src/eventParser.js";
import { routeCommand } from "../src/router.js";
import { getConfig } from "../src/env.js";
import { LarkCli } from "../src/larkCli.js";
import { MessageHandler } from "../src/handler.js";
import { decodeCliChunk } from "../src/cliText.js";
import { draftAgentResponse, resolveCodexCliBin } from "../src/agent.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

process.env.AGENT_PROVIDER = "local";
process.env.DRY_RUN = "true";
process.env.LARK_BOT_NAME = "Codex";
process.env.LARK_BOT_OPEN_ID = "ou_bot";
process.env.A2A_BOTS = "";

const hello = "\u4f60\u597d\uff0c\u4ecb\u7ecd\u4e00\u4e0b\u4f60\u80fd\u505a\u4ec0\u4e48";
const presence = "\u5728\u5417\uff1f";
const summarize = "\u603b\u7ed3\u4e00\u4e0b\u521a\u624d\u7684\u8ba8\u8bba";
const baseCreate = "\u521b\u5efa\u4e00\u4e2a\u9879\u76ee\u4efb\u52a1\u591a\u7ef4\u8868\u683c\uff0c\u5b57\u6bb5\u5305\u62ec\u4efb\u52a1\u540d\u79f0\u3001\u8d1f\u8d23\u4eba\u3001\u622a\u6b62\u65e5\u671f\u3001\u72b6\u6001";
const baseWrite = "\u628a\u521a\u624d\u8ba8\u8bba\u4e2d\u7684\u884c\u52a8\u9879\u5199\u5165\u8fd9\u4e2a\u591a\u7ef4\u8868\u683c";
const docSearch = "\u641c\u7d22\u201c\u9879\u76ee\u8ba1\u5212\u201d\u76f8\u5173\u6587\u6863\u5e76\u603b\u7ed3";
const appsCreate = "\u6839\u636e\u8fd9\u6bb5\u9700\u6c42\u521b\u5efa\u4e00\u4e2a\u5999\u642d\u5e94\u7528\u539f\u578b\uff0c\u4f46\u6267\u884c\u524d\u5148\u8ba9\u6211\u786e\u8ba4";
const localUiApp = "\u751f\u6210\u4e00\u4e2a\u5177\u6709 UI \u754c\u9762\u7684\u8ba1\u7b97\u5668\u5c0f\u8f6f\u4ef6";
const confirm = "\u786e\u8ba4";

test("responds to group mention and extracts core event fields", () => {
  const config = getConfig();
  const event = parseMessageEvent({
    event: {
      sender: { sender_id: { open_id: "ou_user" }, sender_type: "user" },
      message: {
        chat_id: "oc_chat",
        message_id: "om_msg",
        message_type: "text",
        chat_type: "group",
        create_time: "1710000000000",
        content: JSON.stringify({ text: `@Codex ${summarize}` }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.ok(event);
  assert.equal(event.chatId, "oc_chat");
  assert.equal(event.messageId, "om_msg");
  assert.equal(shouldRespond(event, config), true);
  assert.equal(cleanTriggerText(event.plainText), summarize);
});

test("extracts image attachments from Feishu image messages", () => {
  const config = getConfig();
  const event = parseMessageEvent({
    event: {
      sender: { sender_id: { open_id: "ou_user" }, sender_type: "user" },
      message: {
        chat_id: "oc_private",
        message_id: "om_image",
        message_type: "image",
        chat_type: "p2p",
        content: JSON.stringify({ image_key: "img_v3_test" })
      }
    }
  });
  assert.ok(event);
  assert.equal(event.plainText, JSON.stringify({ image_key: "img_v3_test" }));
  assert.deepEqual(event.attachments, [{ kind: "image", key: "img_v3_test", name: undefined, mimeType: undefined }]);
  assert.equal(shouldRespond(event, config), true);
});

test("responds to group mention by own A2A role name and open_id", () => {
  const config = {
    ...getConfig(),
    botOpenId: "ou_bot",
    a2aBots: [{ name: "?????", openId: "ou_bot" }]
  };
  const event = parseMessageEvent({
    event: {
      sender: { sender_id: { open_id: "ou_user" }, sender_type: "user" },
      message: {
        chat_id: "oc_chat",
        message_id: "om_role_mention",
        message_type: "post",
        chat_type: "group",
        content: JSON.stringify({
          zh_cn: {
            content: [[
              { tag: "at", user_id: "ou_bot", user_name: "?????" },
              { tag: "text", text: ` ${summarize}` }
            ]]
          }
        }),
        mentions: [{ open_id: "ou_bot", name: "?????" }]
      }
    }
  });
  assert.ok(event);
  assert.equal(shouldRespond(event, config), true);
  assert.equal(cleanTriggerText(event.plainText, [config.botName, "?????"]), summarize);
});


test("ignores bot self messages", () => {
  const config = getConfig();
  const event = parseMessageEvent({
    event: {
      sender: { sender_id: { open_id: "ou_bot" }, sender_type: "bot" },
      message: {
        chat_id: "oc_chat",
        message_id: "om_msg",
        message_type: "text",
        chat_type: "group",
        content: JSON.stringify({ text: "@Codex hello" }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.ok(event);
  assert.equal(shouldRespond(event, config), false);
});

test("routes required MVP examples", () => {
  assert.equal(routeCommand(hello).intent, "greeting");
  const ping = routeCommand(presence);
  assert.equal(ping.intent, "greeting");
  assert.match(ping.plan.responsePreview, /\u6211\u5728/);
  const summaryRoute = routeCommand(summarize);
  assert.equal(summaryRoute.intent, "summarize");
  assert.deepEqual(summaryRoute.plan.commands[0], ["im", "+chat-messages-list", "--chat-id", "$CHAT_ID", "--page-size", "30", "--as", "bot"]);
  const phaseAdvice = routeCommand("Phase 1 仅做技术可行性意见，评估指标、探活方式、告警渠道、复杂度、风险点和行动项，不写代码。");
  assert.equal(phaseAdvice.intent, "unknown");
  assert.deepEqual(phaseAdvice.plan.commands, []);
  assert.equal(routeCommand(baseCreate).intent, "baseCreate");
  assert.equal(routeCommand(baseWrite).intent, "baseWrite");
  assert.equal(routeCommand(docSearch).intent, "docSearch");
  const apps = routeCommand(appsCreate);
  assert.equal(apps.intent, "apps");
  assert.equal(apps.plan.requiresConfirmation, true);
  assert.equal(routeCommand(localUiApp).intent, "unknown");
  assert.equal(routeCommand("No Feishu Apps. Build a local temporary GUI calculator as one HTML file.").intent, "unknown");
  assert.equal(routeCommand("不要创建飞书应用，只生成本地 HTML 计算器").intent, "unknown");
  assert.equal(routeCommand("任务：开发一个本地单文件 HTML 图形计算器").intent, "unknown");
  assert.equal(routeCommand("请 codeX agent 完成这个开发任务，完成后回报").intent, "unknown");
  assert.equal(routeCommand("创建一个飞书任务清单，分配给团队成员").intent, "task");
  const feishuPublish = routeCommand("\u628a\u8fd9\u4e2a HTML \u9875\u9762\u53d1\u5e03\u5230\u98de\u4e66\u5e94\u7528");
  assert.equal(feishuPublish.intent, "apps");
  assert.equal(feishuPublish.plan.requiresConfirmation, true);
});

test("routes calendar intent to agenda command plan", () => {
  const r1 = routeCommand("查看我的日程");
  assert.equal(r1.intent, "calendar");
  assert.equal(r1.plan.title, "日历与会议");
  assert.deepEqual(r1.plan.commands, [["calendar", "+agenda"]]);
  assert.equal(r1.plan.executable, true);
  assert.equal(r1.plan.requiresConfirmation, false);

  const r2 = routeCommand("今天有什么会议");
  assert.equal(r2.intent, "calendar");

  const r3 = routeCommand("预定下周一的会议室");
  assert.equal(r3.intent, "calendar");

  const r4 = routeCommand("查询会议室忙闲");
  assert.equal(r4.intent, "calendar");

  const r5 = routeCommand("show my agenda");
  assert.equal(r5.intent, "calendar");

  const r6 = routeCommand("安排一个明天的会议");
  assert.equal(r6.intent, "calendar");
});

test("development task mentions are not misrouted as calendar", () => {
  assert.notEqual(routeCommand("日历开发任务实现").intent, "calendar");
  assert.notEqual(routeCommand("会议室订阅系统开发").intent, "calendar");
});

test("codex provider uses model draft instead of local quick reply", async () => {
  const route = routeCommand(summarize);
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-codex-mock-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "if (index >= 0 && process.argv[index + 1]) fs.writeFileSync(process.argv[index + 1], 'MODEL_RESPONSE_FROM_TEST');"
    ].join("\n"),
    "utf8"
  );
  const response = await draftAgentResponse(
    {
      ...getConfig(),
      agentProvider: "codex",
      codexCliBin: process.execPath,
      codexAgentArgs: [scriptPath]
    },
    route
  );
  fs.rmSync(scriptPath, { force: true });
  assert.equal(response, "MODEL_RESPONSE_FROM_TEST");
  assert.doesNotMatch(response, /执行策略/);
});

test("codex cli path refreshes from Codex home config", () => {
  const codexHome = fs.mkdtempSync(path.join(os.tmpdir(), "feishu-codex-home-"));
  const oldBin = path.join(codexHome, "old", "codex.exe");
  const currentBin = path.join(codexHome, "current", "codex.exe");
  fs.mkdirSync(path.dirname(oldBin), { recursive: true });
  fs.mkdirSync(path.dirname(currentBin), { recursive: true });
  fs.writeFileSync(oldBin, "", "utf8");
  fs.writeFileSync(currentBin, "", "utf8");
  fs.writeFileSync(
    path.join(codexHome, "config.toml"),
    [
      "[mcp_servers.node_repl.env]",
      `CODEX_CLI_PATH = '${currentBin.replace(/\\/g, "\\\\")}'`
    ].join("\n"),
    "utf8"
  );
  const previous = process.env.CODEX_HOME;
  process.env.CODEX_HOME = codexHome;
  try {
    assert.equal(resolveCodexCliBin(oldBin), currentBin);
  } finally {
    if (previous === undefined) {
      delete process.env.CODEX_HOME;
    } else {
      process.env.CODEX_HOME = previous;
    }
    fs.rmSync(codexHome, { recursive: true, force: true });
  }
});

test("asks for confirmation before apps creation and executes after confirmation", async () => {
  const config = { ...getConfig(), dryRun: true, confirmTimeoutMs: 600_000 };
  const handler = new MessageHandler(config, new LarkCli(config));
  const baseEvent = {
    chatId: "oc_chat",
    messageId: "om_msg",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: `@Codex ${appsCreate}`,
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  };

  const ask = await handler.handleEvent(baseEvent);
  assert.match(ask, /Reply with confirmation to continue/);
  assert.match(ask, /10 minutes/);

  const done = await handler.handleEvent({
    ...baseEvent,
    messageId: "om_confirm",
    plainText: confirm,
    mentions: []
  });
  assert.match(done, /Confirmed\. Continuing execution/);
  assert.match(done, /计划的飞书操作/);
  assert.match(done, /飞书应用操作/);
  assert.doesNotMatch(done, /apps \+create/);
});

test("handler strips internal lark-cli tails from codex replies", async () => {
  const sent: string[] = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-tail-mock-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "const text = [",
      "  '收到。Phase 1 仅做技术可行性意见。',",
      "  '',",
      "  'lark-cli execution results:',",
      "  '- lark-cli im +chat-messages-list --chat-id oc_secret --page-size 30 --as bot => failed',",
      "  '  {\"error\":{\"message\":\"run lark-cli auth login\"}}'",
      "].join('\\n');",
      "if (output) fs.writeFileSync(output, text);"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendText: async (_chatId: string, text: string) => {
      sent.push(text);
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => {
      throw new Error("technical advice should not run lark-cli commands");
    }
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const response = await handler.handleEvent({
    chatId: "oc_chat",
    messageId: "om_tail",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: "@Codex Phase 1 仅做技术可行性意见，评估指标、行动项和风险点",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  fs.rmSync(scriptPath, { force: true });

  assert.deepEqual(sent, [response]);
  assert.match(response, /技术可行性意见/);
  assert.doesNotMatch(response, /lark-cli execution results/);
  assert.doesNotMatch(response, /chat-messages-list/);
  assert.doesNotMatch(response, /auth login/);
});

test("responds to private chat without mention", () => {
  const config = getConfig();
  const event = parseMessageEvent({
    event: {
      sender: { sender_id: { open_id: "ou_user" }, sender_type: "user" },
      message: {
        chat_id: "oc_private",
        message_id: "om_private",
        message_type: "text",
        chat_type: "p2p",
        content: JSON.stringify({ text: summarize })
      }
    }
  });
  assert.ok(event);
  assert.equal(shouldRespond(event, config), true);
});

test("private chat codex route uses direct-reply context", async () => {
  const sent: string[] = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-private-mock-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const stdin = fs.readFileSync(0, 'utf8');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "if (output) fs.writeFileSync(output, stdin.includes('[Private chat mode]') ? 'PRIVATE_CONTEXT_OK' : 'PRIVATE_CONTEXT_MISSING');"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendText: async (_chatId: string, text: string) => {
      sent.push(text);
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const response = await handler.handleEvent({
    chatId: "oc_private",
    messageId: "om_private_dev",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: "帮我开发一个本地小工具",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "p2p",
    mentions: [],
    raw: {}
  });
  fs.rmSync(scriptPath, { force: true });

  assert.equal(response, "PRIVATE_CONTEXT_OK");
  assert.deepEqual(sent, ["PRIVATE_CONTEXT_OK"]);
});

test("parses flattened lark-cli event consume payload", () => {
  const event = parseMessageEvent({
    chat_id: "oc_flat",
    chat_type: "group",
    content: `@Codex ${summarize}`,
    create_time: "1710000000000",
    message_id: "om_flat",
    message_type: "text",
    sender_id: "ou_flat",
    type: "im.message.receive_v1"
  });
  assert.ok(event);
  assert.equal(event.chatId, "oc_flat");
  assert.equal(event.messageId, "om_flat");
  assert.equal(event.sender.openId, "ou_flat");
  assert.equal(event.plainText, `@Codex ${summarize}`);
});

test("sendText uses current lark-cli im +messages-send flags", async () => {
  const config = { ...getConfig(), dryRun: true };
  const lark = new LarkCli(config);
  const result = await lark.sendText("oc_chat", "hello");
  assert.equal(result.ok, true);
  const payload = JSON.parse(result.stdout) as { command: string[] };
  assert.deepEqual(payload.command.slice(1), [
    "im",
    "+messages-send",
    "--chat-id",
    "oc_chat",
    "--text",
    "hello",
    "--as",
    "bot"
  ]);
});

test("sendPost uses Feishu rich text post content for mentions", async () => {
  const config = { ...getConfig(), dryRun: true };
  const lark = new LarkCli(config);
  const content = {
    zh_cn: {
      content: [[
        { tag: "text" as const, text: "[\u9700\u8981\u534f\u4f5c] " },
        { tag: "at" as const, user_id: "ou_peer", user_name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98" },
        { tag: "text" as const, text: " \u8bf7\u5904\u7406" }
      ]]
    }
  };
  const result = await lark.sendPost("oc_chat", content);
  assert.equal(result.ok, true);
  const payload = JSON.parse(result.stdout) as { command: string[] };
  assert.deepEqual(payload.command.slice(1), [
    "im",
    "+messages-send",
    "--chat-id",
    "oc_chat",
    "--content",
    JSON.stringify(content),
    "--msg-type",
    "post",
    "--as",
    "bot"
  ]);
});

test("addTypingReaction uses Feishu reaction OpenAPI", async () => {
  const config = { ...getConfig(), dryRun: true };
  const lark = new LarkCli(config);
  const result = await lark.addTypingReaction("oc_msg");
  assert.equal(result.ok, true);
  const payload = JSON.parse(result.stdout) as { command: string[] };
  assert.deepEqual(payload.command.slice(1), [
    "api",
    "POST",
    "/open-apis/im/v1/messages/oc_msg/reactions",
    "--data",
    JSON.stringify({ reaction_type: { emoji_type: "Typing" } }),
    "--as",
    "bot"
  ]);
});

test("handler starts and stops typing status around agent reply", async () => {
  const statuses: string[] = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "local" as const,
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => {
      statuses.push("Started");
      return { ok: true, code: 0, stdout: JSON.stringify({ data: { reaction_id: "reaction-1" } }), stderr: "" };
    },
    removeTypingReaction: async () => {
      statuses.push("Stopped");
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendText: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleEvent({
    chatId: "oc_chat",
    messageId: "om_msg",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: `@Codex ${summarize}`,
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  assert.deepEqual(statuses, ["Started", "Stopped"]);
});

test("handler suppresses stale replies when a newer chat request finishes first", async () => {
  const sent: string[] = [];
  const statuses: string[] = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-stale-mock-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const stdin = fs.readFileSync(0, 'utf8');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "const slow = stdin.includes('slow task');",
      "setTimeout(() => {",
      "  if (output) fs.writeFileSync(output, slow ? 'SLOW_RESPONSE_FROM_TEST' : 'FAST_RESPONSE_FROM_TEST');",
      "}, slow ? 200 : 0);"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => {
      statuses.push("Started");
      return { ok: true, code: 0, stdout: JSON.stringify({ data: { reaction_id: "reaction-1" } }), stderr: "" };
    },
    removeTypingReaction: async () => {
      statuses.push("Stopped");
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendText: async (_chatId: string, text: string) => {
      sent.push(text);
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => {
      throw new Error("stale test should not run commands");
    }
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const baseEvent = {
    chatId: "oc_chat",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  };

  const slow = handler.handleEvent({
    ...baseEvent,
    messageId: "om_slow",
    plainText: "@Codex slow task"
  });
  await new Promise((resolve) => setTimeout(resolve, 50));
  await handler.handleEvent({
    ...baseEvent,
    messageId: "om_fast",
    plainText: "@Codex fast task"
  });
  await slow;
  fs.rmSync(scriptPath, { force: true });

  assert.deepEqual(sent, ["FAST_RESPONSE_FROM_TEST"]);
  assert.deepEqual(statuses, ["Started", "Stopped", "Started", "Stopped"]);
});

test("codex progress reporter does not send text status messages", async () => {
  const sent: string[] = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-single-progress-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "setTimeout(() => {",
      "  if (output) fs.writeFileSync(output, 'FINAL_RESPONSE_FROM_TEST');",
      "}, 80);"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    codexProgressInitialMs: 10,
    codexProgressIntervalMs: 10,
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendText: async (_chatId: string, text: string) => {
      sent.push(text);
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => {
      throw new Error("single progress test should not run commands");
    }
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleEvent({
    chatId: "oc_chat",
    messageId: "om_single_progress",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: "@Codex run FDTD slow task",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  fs.rmSync(scriptPath, { force: true });

  assert.deepEqual(sent, ["FINAL_RESPONSE_FROM_TEST"]);
});

test("A2A relay sends bot-to-bot mentions as rich text posts", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string; options?: unknown }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    botOpenId: "ou_codex",
    a2aBots: [{ name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98", openId: "ou_peer" }],
    a2aRelay: {
      enabled: true,
      groupChatId: "oc_group",
      peerName: "\u8d28\u91cf\u5ba1\u8ba1\u5b98",
      peerOpenId: "ou_peer",
      peerCliHome: "C:\Users\admin"
    }
  };
  const fakeLark = {
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async (chatId: string, content: unknown, options?: unknown) => {
      sent.push({ chatId, content, options });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const response = await handler.handleEvent({
    chatId: "oc_group",
    messageId: "om_a2a",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: "@Codex A2A relay test: \u8bf7\u548c\u8d28\u91cf\u5ba1\u8ba1\u5b98\u534f\u4f5c\u8ba8\u8bba\u4e00\u4e0b",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  assert.match(response, /A2A/);
  assert.equal(sent.length, 3);
  assert.equal(sent.filter((item) => item.content).length, 2);
  assert.equal(sent.filter((item) => item.text).length, 1);
  assert.deepEqual(
    (sent[0].content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string }>> } }).zh_cn.content[0][1],
    { tag: "at", user_id: "ou_peer", user_name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98" }
  );
  assert.deepEqual(
    (sent[1].content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string }>> } }).zh_cn.content[0][1],
    { tag: "at", user_id: "ou_codex", user_name: "Codex" }
  );
});

test("known A2A bot sender can receive a rich text mention reply", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    botOpenId: "ou_codex",
    a2aBots: [{ name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98", openId: "ou_peer" }],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async (chatId: string, content: unknown) => {
      sent.push({ chatId, content });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleRaw({
    event: {
      sender: { sender_id: { open_id: "ou_peer" }, sender_type: "bot" },
      message: {
        chat_id: "oc_group",
        message_id: "om_peer",
        message_type: "text",
        chat_type: "group",
        content: JSON.stringify({ text: "@Codex \u8bf7\u5904\u7406\u8fd9\u4e2a\u534f\u4f5c\u8bf7\u6c42" }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].chatId, "oc_group");
  assert.equal(sent[0].text, undefined);
  assert.deepEqual(
    (sent[0].content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string }>> } }).zh_cn.content[0][1],
    { tag: "at", user_id: "ou_peer", user_name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98" }
  );
});

test("A2A task replies without explicit mention are sent back to coordinator as post mentions", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string }> = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-a2a-mention-fallback-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "if (output) fs.writeFileSync(output, '验证完成，以下是完整报告：\\n任务ID：TASK-1');"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    botOpenId: "ou_ops",
    a2aBots: [
      { name: "项目调度官", openId: "ou_coord" },
      { name: "运维验证官", openId: "ou_ops" }
    ],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async (chatId: string, content: unknown) => {
      sent.push({ chatId, content });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleEvent({
    chatId: "oc_group",
    messageId: "om_ops",
    sender: { openId: "ou_coord", senderType: "bot" },
    content: "",
    plainText: "@运维验证官 TASK-1 阶段：运维验证 验证脚本可运行",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["运维验证官"],
    raw: {}
  });
  fs.rmSync(scriptPath, { force: true });

  const final = sent[sent.length - 1];
  assert.equal(final.text, undefined);
  assert.deepEqual(
    (final.content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string }>> } }).zh_cn.content[0][0],
    { tag: "at", user_id: "ou_coord", user_name: "项目调度官" }
  );
});

test("handler converts only the first A2A mention in a final reply", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string }> = [];
  const scriptPath = path.join(os.tmpdir(), `feishu-codex-agent-single-mention-${Date.now()}.js`);
  fs.writeFileSync(
    scriptPath,
    [
      "const fs = require('node:fs');",
      "const index = process.argv.indexOf('--output-last-message');",
      "const output = index >= 0 ? process.argv[index + 1] : '';",
      "if (output) fs.writeFileSync(output, '@项目调度官 已完成。建议下一步通知 @质量审计官。');"
    ].join("\n"),
    "utf8"
  );
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "codex" as const,
    codexCliBin: process.execPath,
    codexAgentArgs: [scriptPath],
    botOpenId: "ou_ops",
    a2aBots: [
      { name: "项目调度官", openId: "ou_coord" },
      { name: "质量审计官", openId: "ou_audit" },
      { name: "运维验证官", openId: "ou_ops" }
    ],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    addTypingReaction: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async (chatId: string, content: unknown) => {
      sent.push({ chatId, content });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleEvent({
    chatId: "oc_group",
    messageId: "om_ops_two_mentions",
    sender: { openId: "ou_coord", senderType: "bot" },
    content: "",
    plainText: "@运维验证官 TASK-1 阶段：运维验证 验证脚本可运行",
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["运维验证官"],
    raw: {}
  });
  fs.rmSync(scriptPath, { force: true });

  const content = sent[sent.length - 1].content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string; text?: string }>> } };
  const elements = content.zh_cn.content[0];
  assert.equal(elements.filter((item) => item.tag === "at").length, 1);
  assert.deepEqual(elements[0], { tag: "at", user_id: "ou_coord", user_name: "项目调度官" });
  assert.ok(elements.some((item) => item.text?.includes("＠质量审计官")));
});

test("A2A result handoff does not trigger a second bot reply", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    botOpenId: "ou_codex",
    a2aBots: [{ name: "\u8d28\u91cf\u5ba1\u8ba1\u5b98", openId: "ou_peer" }],
    a2aRelay: {
      enabled: true,
      groupChatId: "oc_group",
      peerName: "\u8d28\u91cf\u5ba1\u8ba1\u5b98",
      peerOpenId: "ou_peer",
      peerCliHome: "C:\Users\admin"
    }
  };
  const fakeLark = {
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async (chatId: string, content: unknown) => {
      sent.push({ chatId, content });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  await handler.handleRaw({
    event: {
      sender: { sender_id: { open_id: "ou_peer" }, sender_type: "bot" },
      message: {
        chat_id: "oc_group",
        message_id: "om_result",
        message_type: "text",
        chat_type: "group",
        content: JSON.stringify({ text: "[\u7ed3\u679c\u56de\u4f20] @Codex \u5df2\u5b8c\u6210\u534f\u4f5c\u8bf7\u6c42" }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.equal(sent.length, 0);
});

test("long replies are persisted and shortened before sending to Feishu", async () => {
  const sent: Array<{ chatId: string; text?: string }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    agentProvider: "local" as const,
    a2aBots: [],
    a2aRelay: { enabled: false }
  };
  const fakeLark = {
    sendText: async (chatId: string, text: string) => {
      sent.push({ chatId, text });
      return { ok: true, code: 0, stdout: "", stderr: "" };
    },
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => ({ ok: true, code: 0, stdout: "", stderr: "" })
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const response = await handler.handleEvent({
    chatId: "oc_chat",
    messageId: "om_long",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: `@Codex ${"build a local calculator ".repeat(220)}`,
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  assert.ok(sent.length > 1);
  assert.ok(sent.every((item) => (item.text ?? "").length <= 2800));
  assert.equal(response.includes("Full output was saved to a local file"), response.length > 9000);
});

test("non-executable write plans do not run in live mode without completed parameters", async () => {
  const config = { ...getConfig(), dryRun: false, confirmTimeoutMs: 600_000 };
  const fakeLark = {
    sendText: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    sendPost: async () => ({ ok: true, code: 0, stdout: "", stderr: "" }),
    run: async () => {
      throw new Error("run should not be called for non-executable plans");
    }
  } as unknown as LarkCli;
  const handler = new MessageHandler(config, fakeLark);
  const response = await handler.handleEvent({
    chatId: "oc_chat",
    messageId: "om_msg",
    sender: { openId: "ou_user", senderType: "user" },
    content: "",
    plainText: `@Codex ${baseCreate}`,
    messageType: "text",
    createTime: "1710000000000",
    chatType: "group",
    mentions: ["Codex"],
    raw: {}
  });
  assert.match(response, /needs target document\/table tokens/);
  assert.doesNotMatch(response, /DRY_RUN/);
});

test("decodes gb18030 lark-cli output without mojibake", () => {
  const text = "\u4f60\u597d\uff0c\u4f60\u662f\u8c01";
  const bytes = Buffer.from([0xc4, 0xe3, 0xba, 0xc3, 0xa3, 0xac, 0xc4, 0xe3, 0xca, 0xc7, 0xcb, 0xad]);
  assert.equal(decodeCliChunk(bytes, "auto"), text);
});

test("prefers utf-8 lark-cli output when decoding is lossless", () => {
  const text = "\u9879\u76ee\u8c03\u5ea6\u5b98 @\u4ee3\u7801\u6267\u884c\u5b98";
  const bytes = Buffer.from(text, "utf8");
  assert.equal(decodeCliChunk(bytes, "auto"), text);
});
