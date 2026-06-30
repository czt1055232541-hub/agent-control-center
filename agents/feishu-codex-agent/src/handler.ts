import type { AppConfig } from "./env.js";
import fs from "node:fs";
import path from "node:path";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "./eventParser.js";
import { routeCommand } from "./router.js";
import { draftAgentResponse } from "./agent.js";
import { ConfirmationStore } from "./confirmationStore.js";
import type { FeishuMessageEvent, RouteResult } from "./types.js";
import { LarkCli, type LarkPostContent, type LarkPostElement } from "./larkCli.js";
import { A2ARelay } from "./a2aRelay.js";

export class MessageHandler {
  private readonly confirmations: ConfirmationStore;
  private readonly a2aBotOpenIds: Set<string>;
  private readonly a2aRelay: A2ARelay;
  private readonly replyGenerations = new Map<string, number>();
  private readonly eventQueue: Array<{
    event: FeishuMessageEvent;
    resolve: () => void;
    reject: (error: Error) => void;
  }> = [];
  private queueRunning = false;

  constructor(
    private readonly config: AppConfig,
    private readonly larkCli: LarkCli
  ) {
    this.confirmations = new ConfirmationStore(config.confirmTimeoutMs);
    this.a2aBotOpenIds = new Set(config.a2aBots.map((b) => b.openId));
    this.a2aRelay = new A2ARelay(config, larkCli);
  }

  async handleRaw(raw: unknown): Promise<void> {
    const event = parseMessageEvent(raw);
    if (!event) {
      debugLog("ignored unparsable event");
      return;
    }
    injectBotSenderInfo(event, this.config);
    const respond = shouldRespond(event, this.config);
    infoLog(
      `event message_id=${event.messageId} chat_id=${event.chatId} chat_type=${event.chatType ?? "unknown"} sender_type=${event.sender.senderType ?? "unknown"} respond=${respond} text=${preview(event.plainText)}`
    );
    if (!respond) {
      return;
    }
    return new Promise<void>((resolve, reject) => {
      this.eventQueue.push({
        event,
        resolve,
        reject
      });
      this.ensureQueueRunning();
    });
  }

  private ensureQueueRunning(): void {
    if (this.queueRunning) {
      return;
    }
    this.queueRunning = true;
    this.runQueue().finally(() => {
      this.queueRunning = false;
    });
  }

  private async runQueue(): Promise<void> {
    while (this.eventQueue.length > 0) {
      const item = this.eventQueue.shift()!;
      try {
        await this.handleEvent(item.event);
        item.resolve();
      } catch (error) {
        item.reject(error instanceof Error ? error : new Error(String(error)));
      }
    }
    this.queueRunning = false;
    if (this.eventQueue.length > 0) {
      this.ensureQueueRunning();
    }
  }

  async flush(): Promise<void> {
    while (this.eventQueue.length > 0 || this.queueRunning) {
      await new Promise((r) => setTimeout(r, 100));
    }
  }

  async handleEvent(event: FeishuMessageEvent): Promise<string> {
    const cleanText = cleanTriggerText(event.plainText, this.config.botName);
    if (this.a2aRelay.shouldHandle(event, cleanText)) {
      return this.a2aRelay.run(event, cleanText);
    }
    const senderKey = senderKeyFor(event);
    const confirmed = this.confirmations.consumeIfConfirmed(event.chatId, senderKey, cleanText);
    if (confirmed) {
      return this.executeAndReply(event.chatId, confirmed.route, true);
    }
    const route = this.a2aBotOpenIds.has(event.sender.openId || "")
      ? routeCommandAsAgentTask(cleanText)
      : routeCommand(cleanText);
    if (route.plan.requiresConfirmation) {
      this.confirmations.create(event.chatId, senderKey, route);
      const response = formatConfirmation(route);
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }
    return this.executeAndReply(event.chatId, route, false);
  }

  private async executeAndReply(chatId: string, route: RouteResult, confirmed: boolean): Promise<string> {
    const generation = this.nextReplyGeneration(chatId);
    await this.setTypingStatus(chatId, "Started");
    try {
      const agentText = sanitizeAgentText(await draftAgentResponse(this.config, route));
      if (!this.isCurrentReplyGeneration(chatId, generation)) {
        infoLog(`suppressed stale draft chat_id=${chatId} generation=${generation}`);
        return prepareResponseForFeishu(agentText);
      }
      const shouldRunCommands = this.config.dryRun || route.plan.executable;
      const commandResults = [];
      if (shouldRunCommands) {
        for (const command of route.plan.commands) {
          if (!this.isCurrentReplyGeneration(chatId, generation)) {
            infoLog(`suppressed stale command execution chat_id=${chatId} generation=${generation}`);
            return prepareResponseForFeishu(agentText);
          }
          const resolved = resolveCommand(command, chatId);
          const result = await this.larkCli.run(resolved);
          commandResults.push({ command: resolved, result });
        }
      }
      const fullResponse = [
        confirmed ? "Confirmed. Continuing execution." : "",
        agentText,
        !shouldRunCommands && route.plan.commands.length ? formatPlanOnly(route) : "",
        commandResults.length ? formatCommandResults(commandResults, this.config.dryRun) : ""
      ]
        .filter(Boolean)
        .join("\n\n");
      const response = prepareResponseForFeishu(fullResponse);
      if (!this.isCurrentReplyGeneration(chatId, generation)) {
        infoLog(`suppressed stale reply chat_id=${chatId} generation=${generation}`);
        return response;
      }
      const richResponse = this.toRichTextWithA2AMentions(response);
      const sendResult = richResponse
        ? await this.larkCli.sendPost(chatId, richResponse)
        : await this.larkCli.sendText(chatId, response);
      if (!sendResult.ok) {
        console.error(`[agent] failed to reply chat_id=${chatId} code=${sendResult.code} stderr=${preview(sendResult.stderr || sendResult.stdout, 1000)}`);
      } else {
        infoLog(`replied chat_id=${chatId}`);
      }
      return response;
    } finally {
      if (this.isCurrentReplyGeneration(chatId, generation)) {
        await this.setTypingStatus(chatId, "Stopped");
      }
    }
  }

  private nextReplyGeneration(chatId: string): number {
    const next = (this.replyGenerations.get(chatId) ?? 0) + 1;
    this.replyGenerations.set(chatId, next);
    return next;
  }

  private isCurrentReplyGeneration(chatId: string, generation: number): boolean {
    return this.replyGenerations.get(chatId) === generation;
  }

  private async setTypingStatus(chatId: string, status: "Started" | "Stopped"): Promise<void> {
    if (typeof this.larkCli.setTypingStatus !== "function") {
      return;
    }
    try {
      const result = await this.larkCli.setTypingStatus(chatId, status);
      if (!result.ok) {
        debugLog(`typing status ${status} failed chat_id=${chatId} code=${result.code} stderr=${preview(result.stderr || result.stdout, 500)}`);
      }
    } catch (error) {
      debugLog(`typing status ${status} threw chat_id=${chatId} error=${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private toRichTextWithA2AMentions(value: string): LarkPostContent | null {
    if (this.config.a2aBots.length === 0) {
      return null;
    }
    const mentionPattern = buildMentionPattern(this.config.a2aBots);
    const elements: LarkPostElement[] = [];
    let cursor = 0;
    let hasMention = false;
    for (const match of value.matchAll(mentionPattern)) {
      const matchText = match[0];
      const index = match.index ?? 0;
      if (index > cursor) {
        elements.push({ tag: "text", text: value.slice(cursor, index) });
      }
      const bot = resolveMentionBot(matchText, this.config.a2aBots);
      if (bot) {
        elements.push({ tag: "at", user_id: bot.openId, user_name: bot.name });
        hasMention = true;
      } else {
        elements.push({ tag: "text", text: matchText });
      }
      cursor = index + matchText.length;
    }
    if (!hasMention) {
      return null;
    }
    if (cursor < value.length) {
      elements.push({ tag: "text", text: value.slice(cursor) });
    }
    return { zh_cn: { content: [elements] } };
  }
}

function buildMentionPattern(bots: Array<{ name: string; openId: string }>): RegExp {
  const names = bots.map((bot) => `@${escapeRegExp(bot.name)}`);
  const tags = bots.map((bot) => `<at\\s+user_id=["']${escapeRegExp(bot.openId)}["']\\s*>[^<]*<\\/at>`);
  return new RegExp([...tags, ...names].join("|"), "g");
}

function resolveMentionBot(matchText: string, bots: Array<{ name: string; openId: string }>): { name: string; openId: string } | undefined {
  const tagMatch = /^<at\s+user_id=["']([^"']+)["']\s*>[^<]*<\/at>$/.exec(matchText);
  if (tagMatch) {
    return bots.find((item) => item.openId === tagMatch[1]);
  }
  return bots.find((item) => matchText === `@${item.name}`);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function routeCommandAsAgentTask(cleanText: string): RouteResult {
  const route = routeCommand(cleanText);
  if (route.plan.requiresConfirmation) {
    return {
      intent: "unknown",
      cleanText,
      plan: {
        title: "A2A collaboration task",
        commands: [],
        executable: true,
        requiresConfirmation: false,
        responsePreview: `I will handle this as an A2A collaboration task under my current role and will not create or publish Feishu resources directly. Request: ${cleanText}`
      }
    };
  }
  return route;
}

function prepareResponseForFeishu(response: string): string {
  const maxLength = 3000;
  if (response.length <= maxLength) {
    return response;
  }
  const filePath = persistLongResponse(response);
  const headLength = Math.max(1000, maxLength - filePath.length - 260);
  return [
    response.slice(0, headLength).trimEnd(),
    "",
    "[Full output was saved to a local file; the Feishu message was truncated due to length limits.]",
    filePath
  ].join("\n");
}

function sanitizeAgentText(response: string): string {
  const lines = response.split(/\r?\n/);
  const cleaned: string[] = [];
  let skippingAuthBlock = false;
  for (const line of lines) {
    const mentionsLarkAuth =
      /lark-cli\s+auth\s+login/i.test(line) ||
      /bot\s*认证.*重新登录/i.test(line) ||
      /重新授权后.*群.*发消息/i.test(line) ||
      /向群.*汇报.*认证/i.test(line);
    const authBlockHeader = /关于.*群聊.*问题/.test(line) || /汇报群聊的问题/.test(line);
    if (authBlockHeader || mentionsLarkAuth) {
      skippingAuthBlock = true;
      continue;
    }
    if (skippingAuthBlock) {
      if (/^\s*(?:---+|\*\*[^*]+\*\*|#{1,6}\s+|\d+[.、]\s+|-+\s+)/.test(line)) {
        skippingAuthBlock = false;
      } else {
        continue;
      }
    }
    cleaned.push(line);
  }
  return cleaned.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function persistLongResponse(response: string): string {
  const dir = path.resolve(process.cwd(), "..", "runtime", "generated", "codex-agent-replies");
  fs.mkdirSync(dir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filePath = path.join(dir, `${stamp}.md`);
  fs.writeFileSync(filePath, response, "utf8");
  return filePath;
}

function resolveCommand(command: string[], chatId: string): string[] {
  return command.map((part) => (part === "$CHAT_ID" ? chatId : part));
}

function formatConfirmation(route: RouteResult): string {
  return [
    "This operation requires confirmation. Reply with confirmation to continue.",
    "",
    `Operation: ${route.plan.title}`,
    route.plan.confirmationReason ? `Reason: ${route.plan.confirmationReason}` : "",
    route.plan.commands.length ? `Planned commands:\n${route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")}` : "",
    "If there is no confirmation within 10 minutes, this operation will be cancelled."
  ]
    .filter(Boolean)
    .join("\n");
}

function formatPlanOnly(route: RouteResult): string {
  return [
    "A plan was generated, but this operation needs target document/table tokens, fields, or publish parameters before it can be executed.",
    route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")
  ].join("\n");
}

function formatCommandResults(items: Array<{ command: string[]; result: { ok: boolean; stdout: string; stderr: string } }>, dryRun: boolean): string {
  const header = dryRun ? "DRY_RUN planned commands:" : "lark-cli execution results:";
  return [
    header,
    ...items.map(({ command, result }) => {
      const status = result.ok ? "ok" : "failed";
      const output = (result.stdout || result.stderr).trim();
      return `- lark-cli ${command.join(" ")} => ${status}${output ? `\n  ${truncate(output, 500)}` : ""}`;
    })
  ].join("\n");
}

function senderKeyFor(event: FeishuMessageEvent): string {
  return event.sender.openId || event.sender.userId || event.sender.unionId || event.messageId;
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function injectBotSenderInfo(event: FeishuMessageEvent, config: AppConfig): void {
  if (!event.sender.openId) {
    return;
  }
  const senderBot = config.a2aBots.find((b) => b.openId === event.sender.openId);
  if (!senderBot) {
    return;
  }
  if (/^\s*\[(?:\u7ed3\u679c\u56de\u4f20|\u4ec5\u901a\u77e5)\]/.test(event.plainText)) {
    return;
  }
  const senderLabel = `[\u6765\u81ea\u673a\u5668\u4eba\u300c${senderBot.name}\u300d\u2014 \u5982\u9700 @ \u56de\u5bf9\u65b9\u8bf7\u5199\uff1a@${senderBot.name}]\n\n`;
  event.plainText = senderLabel + event.plainText;
}

function preview(value: string, max = 160): string {
  return JSON.stringify(truncate(value.replace(/\s+/g, " ").trim(), max));
}

function infoLog(message: string): void {
  if ((process.env.LOG_LEVEL || "info").toLowerCase() !== "silent") {
    console.error(`[agent] ${message}`);
  }
}

function debugLog(message: string): void {
  if ((process.env.LOG_LEVEL || "").toLowerCase() === "debug") {
    console.error(`[agent] ${message}`);
  }
}
