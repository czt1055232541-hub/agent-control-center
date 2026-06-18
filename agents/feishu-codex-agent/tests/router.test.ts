import test from "node:test";
import assert from "node:assert/strict";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "../src/eventParser.js";
import { routeCommand } from "../src/router.js";
import { getConfig } from "../src/env.js";
import { LarkCli } from "../src/larkCli.js";
import { MessageHandler } from "../src/handler.js";
import { decodeCliChunk } from "../src/cliText.js";
import { draftAgentResponse } from "../src/agent.js";

const hello = "\u4f60\u597d\uff0c\u4ecb\u7ecd\u4e00\u4e0b\u4f60\u80fd\u505a\u4ec0\u4e48";
const presence = "\u5728\u5417\uff1f";
const summarize = "\u603b\u7ed3\u4e00\u4e0b\u521a\u624d\u7684\u8ba8\u8bba";
const baseCreate = "\u521b\u5efa\u4e00\u4e2a\u9879\u76ee\u4efb\u52a1\u591a\u7ef4\u8868\u683c\uff0c\u5b57\u6bb5\u5305\u62ec\u4efb\u52a1\u540d\u79f0\u3001\u8d1f\u8d23\u4eba\u3001\u622a\u6b62\u65e5\u671f\u3001\u72b6\u6001";
const baseWrite = "\u628a\u521a\u624d\u8ba8\u8bba\u4e2d\u7684\u884c\u52a8\u9879\u5199\u5165\u8fd9\u4e2a\u591a\u7ef4\u8868\u683c";
const docSearch = "\u641c\u7d22\u201c\u9879\u76ee\u8ba1\u5212\u201d\u76f8\u5173\u6587\u6863\u5e76\u603b\u7ed3";
const appsCreate = "\u6839\u636e\u8fd9\u6bb5\u9700\u6c42\u521b\u5efa\u4e00\u4e2a\u5999\u642d\u5e94\u7528\u539f\u578b\uff0c\u4f46\u6267\u884c\u524d\u5148\u8ba9\u6211\u786e\u8ba4";
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
  assert.equal(routeCommand(summarize).intent, "summarize");
  assert.equal(routeCommand(baseCreate).intent, "baseCreate");
  assert.equal(routeCommand(baseWrite).intent, "baseWrite");
  assert.equal(routeCommand(docSearch).intent, "docSearch");
  const apps = routeCommand(appsCreate);
  assert.equal(apps.intent, "apps");
  assert.equal(apps.plan.requiresConfirmation, true);
});

test("codex provider uses model draft instead of local quick reply", async () => {
  const route = routeCommand(summarize);
  const response = await draftAgentResponse(
    {
      ...getConfig(),
      agentProvider: "codex",
      codexCliBin: process.execPath,
      codexAgentArgs: ["-e", "console.log('MODEL_RESPONSE_FROM_TEST')"]
    },
    route
  );
  assert.equal(response, "MODEL_RESPONSE_FROM_TEST");
  assert.doesNotMatch(response, /执行策略/);
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
  assert.match(ask, /\u8bf7\u56de\u590d \u786e\u8ba4 \u7ee7\u7eed/);
  assert.match(ask, /10 \u5206\u949f/);

  const done = await handler.handleEvent({
    ...baseEvent,
    messageId: "om_confirm",
    plainText: confirm,
    mentions: []
  });
  assert.match(done, /\u5df2\u6536\u5230\u786e\u8ba4/);
  assert.match(done, /DRY_RUN/);
  assert.match(done, /apps \+create/);
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
        { tag: "text" as const, text: "[需要协作] " },
        { tag: "at" as const, user_id: "ou_peer", user_name: "龙虾酱" },
        { tag: "text" as const, text: " 请处理" }
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

test("A2A relay sends bot-to-bot mentions as rich text posts", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string; options?: unknown }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    botOpenId: "ou_codex",
    a2aBots: [{ name: "龙虾酱", openId: "ou_peer" }],
    a2aRelay: {
      enabled: true,
      groupChatId: "oc_group",
      peerName: "龙虾酱",
      peerOpenId: "ou_peer",
      peerCliHome: "C:\\Users\\admin"
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
    plainText: "@Codex 请和龙虾酱协作讨论一下",
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
    { tag: "at", user_id: "ou_peer", user_name: "龙虾酱" }
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
    a2aBots: [{ name: "龙虾酱", openId: "ou_peer" }],
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
        content: JSON.stringify({ text: "@Codex 请处理这个协作请求" }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].chatId, "oc_group");
  assert.equal(sent[0].text, undefined);
  assert.deepEqual(
    (sent[0].content as { zh_cn: { content: Array<Array<{ tag: string; user_id?: string }>> } }).zh_cn.content[0][1],
    { tag: "at", user_id: "ou_peer", user_name: "龙虾酱" }
  );
});

test("A2A result handoff does not trigger a second bot mention", async () => {
  const sent: Array<{ chatId: string; content?: unknown; text?: string }> = [];
  const config = {
    ...getConfig(),
    dryRun: false,
    botOpenId: "ou_codex",
    a2aBots: [{ name: "龙虾酱", openId: "ou_peer" }],
    a2aRelay: {
      enabled: true,
      groupChatId: "oc_group",
      peerName: "龙虾酱",
      peerOpenId: "ou_peer",
      peerCliHome: "C:\\Users\\admin"
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
        content: JSON.stringify({ text: "[结果回传] @Codex 已完成协作请求" }),
        mentions: [{ name: "Codex" }]
      }
    }
  });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].chatId, "oc_group");
  assert.notEqual(sent[0].text, undefined);
  assert.equal(sent[0].content, undefined);
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
  assert.match(response, /\u9700\u8981\u8865\u9f50/);
  assert.doesNotMatch(response, /DRY_RUN/);
});

test("decodes gb18030 lark-cli output without mojibake", () => {
  const text = "\u4f60\u597d\uff0c\u4f60\u662f\u8c01";
  const bytes = Buffer.from([0xc4, 0xe3, 0xba, 0xc3, 0xa3, 0xac, 0xc4, 0xe3, 0xca, 0xc7, 0xcb, 0xad]);
  assert.equal(decodeCliChunk(bytes, "auto"), text);
});
