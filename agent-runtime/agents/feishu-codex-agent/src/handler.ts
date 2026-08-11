import type { AppConfig } from "./env.js";
import fs from "node:fs";
import path from "node:path";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "./eventParser.js";
import { routeCommand } from "./router.js";
import { draftAgentResponse } from "./agent.js";
import { ConfirmationStore } from "./confirmationStore.js";
import type { CliResult, FeishuMessageEvent, MessageAttachment, RouteResult } from "./types.js";
import { LarkCli, type LarkPostContent, type LarkPostElement } from "./larkCli.js";
import { A2ARelay } from "./a2aRelay.js";

export class MessageHandler {
  private readonly confirmations: ConfirmationStore;
  private readonly a2aBotOpenIds: Set<string>;
  private readonly a2aRelay: A2ARelay;
 private readonly replyGenerations = new Map<string, number>();
 private codexUsageCooldownUntil = 0;
 private readonly eventQueue: Array<{
   event: FeishuMessageEvent;
   resolve: () => void;
   reject: (error: Error) => void;
 }> = [];
 private queueRunning = false;
  private typingReactions = new Map<number, { messageId: string; reactionId: string }>();

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
    if (isA2AResultNotification(event, this.config)) {
      infoLog(`ignored A2A result notification message_id=${event.messageId}`);
      return;
    }
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
    const attachments = await this.prepareAttachments(event);
    const cleanText = cleanTriggerText(event.plainText, botTriggerNames(this.config));
    if (this.a2aRelay.shouldHandle(event, cleanText)) {
      return this.a2aRelay.run(event, cleanText);
    }
    const senderKey = senderKeyFor(event);
   const confirmed = this.confirmations.consumeIfConfirmed(event.chatId, senderKey, cleanText);
   if (confirmed) {
      return this.executeAndReply(event.chatId, event.messageId, confirmed.route, true);
   }
   const senderIsA2ABot = this.a2aBotOpenIds.has(event.sender.openId || "");
    const route = senderIsA2ABot
      ? routeCommandAsAgentTask(cleanText)
      : routeCommand(cleanText);
    attachConversationContext(route, event, senderIsA2ABot, attachments);
    if (route.plan.requiresConfirmation) {
      this.confirmations.create(event.chatId, senderKey, route);
      const response = formatConfirmation(route);
      await this.larkCli.sendText(event.chatId, response, replyOptions(event.messageId));
      return response;
   }
    return this.executeAndReply(event.chatId, event.messageId, route, false);
 }

  private async prepareAttachments(event: FeishuMessageEvent): Promise<MessageAttachment[]> {
    if ((event.attachments ?? []).length === 0) {
      return [];
    }
    const selected = (event.attachments ?? []).slice(0, Math.max(1, this.config.maxAttachments));
    const prepared: MessageAttachment[] = [];
    for (const attachment of selected) {
      prepared.push(await this.downloadAttachment(event.messageId, attachment));
    }
    return prepared;
  }

  private async downloadAttachment(messageId: string, attachment: MessageAttachment): Promise<MessageAttachment> {
    const output = safeAttachmentOutput(this.config.attachmentDownloadDir, messageId, attachment);
    const absoluteOutput = path.resolve(process.cwd(), output);
    fs.mkdirSync(path.dirname(absoluteOutput), { recursive: true });
    const result = await this.larkCli.downloadMessageResource(messageId, attachment.key, attachment.kind, output);
    if (!result.ok) {
      return { ...attachment, downloadError: preview(result.stderr || result.stdout || "download failed", 500) };
    }
    const localPath = findDownloadedPath(result.stdout, absoluteOutput);
    return { ...attachment, localPath };
  }

  private async executeAndReply(chatId: string, messageId: string, route: RouteResult, confirmed: boolean): Promise<string> {
   const generation = this.nextReplyGeneration(chatId);
   if (this.isCodexUsageCooldownActive()) {
     infoLog(`suppressed codex task during usage cooldown chat_id=${chatId}`);
     return "";
   }
   await this.startTypingReaction(messageId, generation);
    const progress = this.startProgressReporter(chatId, route, generation);
   try {
     const agentText = sanitizeAgentText(await draftAgentResponse(this.config, route));
      this.recordCodexUsageCooldownIfNeeded(agentText);
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
      const sendResult = await this.sendResponse(chatId, messageId, response, route);
      if (!sendResult.ok) {
        console.error(`[agent] failed to reply chat_id=${chatId} code=${sendResult.code} stderr=${preview(sendResult.stderr || sendResult.stdout, 1000)}`);
      } else {
        infoLog(`replied chat_id=${chatId}`);
      }
      return response;
    } finally {
     progress.stop();
     if (this.isCurrentReplyGeneration(chatId, generation)) {
        await this.stopTypingReaction(generation);
     }
   }
 }

 private nextReplyGeneration(chatId: string): number {
   const next = (this.replyGenerations.get(chatId) ?? 0) + 1;
   this.replyGenerations.set(chatId, next);
    // Clean up any stale typing reaction from previous generation
    const prev = next - 1;
    const staleState = this.typingReactions.get(prev);
    if (staleState) {
      this.typingReactions.delete(prev);
      this.larkCli.removeTypingReaction(staleState.messageId, staleState.reactionId).catch(() => {});
    }
   return next;
 }

  private isCurrentReplyGeneration(chatId: string, generation: number): boolean {
    return this.replyGenerations.get(chatId) === generation;
  }

  private isCodexUsageCooldownActive(): boolean {
    return this.config.agentProvider === "codex" && Date.now() < this.codexUsageCooldownUntil;
  }

  private recordCodexUsageCooldownIfNeeded(response: string): void {
    if (this.config.agentProvider !== "codex" || !isCodexUsageLimitText(response)) {
      return;
    }
    this.codexUsageCooldownUntil = codexUsageCooldownUntil(response, Date.now());
    infoLog(`codex usage cooldown active until ${new Date(this.codexUsageCooldownUntil).toISOString()}`);
  }

  private async startTypingReaction(messageId: string, generation: number): Promise<void> {
    try {
      const result = await this.larkCli.addTypingReaction(messageId);
      if (!result.ok) {
        debugLog(`typing reaction add failed message_id=${messageId} code=${result.code} stderr=${preview(result.stderr || result.stdout, 500)}`);
        return;
      }
      let reactionId: string | null = null;
      try {
        const body = JSON.parse(result.stdout);
        reactionId = body?.data?.reaction_id ?? null;
      } catch {
        // ignore parse errors
      }
      if (reactionId) {
        this.typingReactions.set(generation, { messageId, reactionId });
      }
    } catch (error) {
      debugLog(`typing reaction add error message_id=${messageId} error=${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async stopTypingReaction(generation: number): Promise<void> {
    const state = this.typingReactions.get(generation);
    if (!state) {
      return;
    }
    this.typingReactions.delete(generation);
    try {
      const result = await this.larkCli.removeTypingReaction(state.messageId, state.reactionId);
      if (!result.ok) {
        debugLog(`typing reaction remove failed message_id=${state.messageId} reaction_id=${state.reactionId} code=${result.code} stderr=${preview(result.stderr || result.stdout, 500)}`);
      }
    } catch (error) {
      debugLog(`typing reaction remove error message_id=${state.messageId} reaction_id=${state.reactionId} error=${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private startProgressReporter(chatId: string, route: RouteResult, generation: number): { stop: () => void } {
    void chatId;
    void route;
    void generation;
    return {
      stop: () => undefined
    };
  }

  private async sendResponse(chatId: string, messageId: string, response: string, route: RouteResult): Promise<CliResult> {
    const outbound = ensureCoordinatorMentionForA2AReply(response, route, this.config.a2aBots);
    const chunks = splitResponseForFeishu(outbound, this.config.a2aBots);
    let lastResult: CliResult = { ok: true, code: 0, stdout: "", stderr: "" };
    for (let index = 0; index < chunks.length; index += 1) {
      const isLast = index === chunks.length - 1;
      const chunk = chunks[index];
      const richResponse = isLast ? this.toRichTextWithA2AMentions(chunk) : null;
      lastResult = richResponse
        ? await this.larkCli.sendPost(chatId, richResponse, replyOptions(messageId))
        : await this.larkCli.sendText(chatId, isLast ? chunk : neutralizeA2AMentions(chunk, this.config.a2aBots), replyOptions(messageId));
      if (!lastResult.ok) {
        return lastResult;
      }
    }
    return lastResult;
  }

  private toRichTextWithA2AMentions(value: string): LarkPostContent | null {
    if (this.config.a2aBots.length === 0) {
      return null;
    }
    const mentionPattern = buildMentionPattern(this.config.a2aBots);
    const elements: LarkPostElement[] = [];
    let cursor = 0;
    let convertedMention = false;
    for (const match of value.matchAll(mentionPattern)) {
      const matchText = match[0];
      const index = match.index ?? 0;
      if (index > cursor) {
        elements.push({ tag: "text", text: value.slice(cursor, index) });
      }
      const bot = resolveMentionBot(matchText, this.config.a2aBots);
      if (bot && !convertedMention) {
        elements.push({ tag: "at", user_id: bot.openId, user_name: bot.name });
        convertedMention = true;
      } else if (bot) {
        elements.push({ tag: "text", text: neutralizedMentionText(matchText, bot) });
      } else {
        elements.push({ tag: "text", text: matchText });
      }
      cursor = index + matchText.length;
    }
    if (cursor < value.length) {
      elements.push({ tag: "text", text: value.slice(cursor) });
    }
    return { zh_cn: { content: [elements] } };
  }
}

function replyOptions(messageId: string): { replyToMessageId: string; replyInThread: true } {
  return { replyToMessageId: messageId, replyInThread: true };
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

function neutralizedMentionText(matchText: string, bot: { name: string; openId: string }): string {
  if (matchText.startsWith("@")) {
    return `＠${bot.name}`;
  }
  return bot.name;
}

function ensureCoordinatorMentionForA2AReply(value: string, route: RouteResult, bots: Array<{ name: string; openId: string }>): string {
  if (route.context?.isPrivate || !route.context?.senderIsA2ABot || bots.length === 0) {
    return value;
  }
  const mentionPattern = buildMentionPattern(bots);
  if (mentionPattern.test(value)) {
    return value;
  }
  const coordinator = bots.find((bot) => bot.name === "项目调度官");
  if (!coordinator) {
    return value;
  }
  return `@${coordinator.name} ${value}`;
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

function attachConversationContext(route: RouteResult, event: FeishuMessageEvent, senderIsA2ABot: boolean, attachments: MessageAttachment[] = []): RouteResult {
  route.context = {
    chatType: event.chatType,
    messageId: event.messageId,
    isPrivate: isPrivateChat(event.chatType),
    senderIsA2ABot,
    attachments
  };
  return route;
}

function isPrivateChat(chatType: string | undefined): boolean {
  return /^(p2p|private|single)$/i.test(chatType ?? "");
}

function isCodexUsageLimitText(value: string): boolean {
  return /usage limit|you've hit your usage limit|try again at/i.test(value);
}

function codexUsageCooldownUntil(value: string, nowMs: number): number {
  const retry = value.match(/try again at\s+(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if (!retry) {
    return nowMs + 30 * 60 * 1000;
  }
  const now = new Date(nowMs);
  let hour = Number(retry[1]);
  const minute = Number(retry[2]);
  const meridiem = retry[3].toUpperCase();
  if (meridiem === "PM" && hour < 12) {
    hour += 12;
  }
  if (meridiem === "AM" && hour === 12) {
    hour = 0;
  }
  const until = new Date(now);
  until.setHours(hour, minute + 1, 0, 0);
  if (until.getTime() <= nowMs) {
    until.setDate(until.getDate() + 1);
  }
  return until.getTime();
}

function prepareResponseForFeishu(response: string): string {
  const maxTotalLength = 9_000;
  if (response.length <= maxTotalLength) {
    return response;
  }
  const filePath = persistLongResponse(response);
  const headLength = Math.max(6_000, maxTotalLength - filePath.length - 260);
  return [
    response.slice(0, headLength).trimEnd(),
    "",
    "[Full output was saved to a local file; the Feishu message was truncated due to length limits.]",
    filePath
  ].join("\n");
}

function splitResponseForFeishu(response: string, bots: Array<{ name: string; openId: string }>): string[] {
  const maxLength = 2800;
  if (response.length <= maxLength) {
    return [response];
  }
  const chunks: string[] = [];
  let cursor = 0;
  while (cursor < response.length) {
    const next = findChunkEnd(response, cursor, maxLength);
    chunks.push(response.slice(cursor, next).trim());
    cursor = next;
  }
  if (chunks.length > 1) {
    for (let i = 0; i < chunks.length - 1; i += 1) {
      chunks[i] = neutralizeA2AMentions(chunks[i], bots);
    }
  }
  return chunks.filter(Boolean);
}

function findChunkEnd(value: string, start: number, maxLength: number): number {
  const hardEnd = Math.min(value.length, start + maxLength);
  if (hardEnd === value.length) {
    return hardEnd;
  }
  const window = value.slice(start, hardEnd);
  const candidates = [window.lastIndexOf("\n\n"), window.lastIndexOf("\n"), window.lastIndexOf("。"), window.lastIndexOf(". ")].filter((n) => n > 800);
  if (candidates.length === 0) {
    return hardEnd;
  }
  return start + Math.max(...candidates) + 1;
}

function neutralizeA2AMentions(value: string, bots: Array<{ name: string; openId: string }>): string {
  let text = value;
  for (const bot of bots) {
    text = text.replace(new RegExp(`@${escapeRegExp(bot.name)}`, "g"), `＠${bot.name}`);
    text = text.replace(new RegExp(`<at\\s+user_id=["']${escapeRegExp(bot.openId)}["']\\s*>[^<]*<\\/at>`, "g"), bot.name);
  }
  return text;
}

function sanitizeAgentText(response: string): string {
  const lines = response.split(/\r?\n/);
  const cleaned: string[] = [];
  let skippingAuthBlock = false;
  let skippingCliBlock = false;
  for (const line of lines) {
    const cliLeakHeader =
      /^\s*(?:lark-cli execution results|DRY_RUN planned commands|Planned commands|Execution policy)\s*:/i.test(line) ||
      /^\s*Codex CLI call failed:/i.test(line);
    if (cliLeakHeader) {
      skippingCliBlock = true;
      continue;
    }
    if (skippingCliBlock) {
      if (/^\s*(?:#{1,6}\s+|\*\*[^*]+\*\*|\d+[.、]\s+|[一二三四五六七八九十]+[、.]\s+)\S/.test(line)) {
        skippingCliBlock = false;
      } else {
        continue;
      }
    }
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
  const header = dryRun ? "计划的飞书操作：" : "飞书操作执行结果：";
  return [
    header,
    ...items.map(({ command, result }) => {
      const status = result.ok ? "成功" : "失败，内部错误已记录";
      return `- ${describeLarkOperation(command)}：${status}`;
    })
  ].join("\n");
}

function describeLarkOperation(command: string[]): string {
  const [domain, action] = command;
  if (domain === "im") {
    return "飞书消息操作";
  }
  if (domain === "task") {
    return "飞书任务操作";
  }
  if (domain === "apps") {
    return "飞书应用操作";
  }
  if (domain === "calendar") {
    return "飞书日历操作";
  }
  if (domain === "base") {
    return "飞书多维表格操作";
  }
  if (domain === "docs") {
    return "飞书文档操作";
  }
  return action ? `飞书 ${domain} ${action} 操作` : "飞书操作";
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

function isA2AResultNotification(event: FeishuMessageEvent, config: AppConfig): boolean {
  const senderIsA2ABot = Boolean(event.sender.openId && config.a2aBots.some((bot) => bot.openId === event.sender.openId));
  return senderIsA2ABot && /^\s*\[(?:结果回传|仅通知)\]/.test(event.plainText);
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

function safeAttachmentOutput(baseDir: string, messageId: string, attachment: MessageAttachment): string {
  const safeBase = normalizeRelativeOutputDir(baseDir);
  const safeMessageId = sanitizePathPart(messageId || "message");
  const safeKey = sanitizePathPart(attachment.key);
  const ext = extensionForAttachment(attachment);
  return path.posix.join(safeBase, safeMessageId, `${safeKey}${ext}`);
}

function normalizeRelativeOutputDir(value: string): string {
  const normalized = value.replace(/\\/g, "/").split("/").filter((part) => part && part !== "." && part !== ".." && !part.includes(":"));
  return normalized.join("/") || "runtime/attachments";
}

function sanitizePathPart(value: string): string {
  return value.replace(/[^A-Za-z0-9_.-]+/g, "_").slice(0, 120) || "resource";
}

function extensionForAttachment(attachment: MessageAttachment): string {
  const nameExt = attachment.name ? path.extname(attachment.name) : "";
  if (/^\.[A-Za-z0-9]{1,8}$/.test(nameExt)) {
    return nameExt;
  }
  if (attachment.kind === "image") {
    if (/webp/i.test(attachment.mimeType ?? "")) {
      return ".webp";
    }
    if (/jpe?g/i.test(attachment.mimeType ?? "")) {
      return ".jpg";
    }
    return ".png";
  }
  return "";
}

function findDownloadedPath(stdout: string, fallback: string): string {
  try {
    const parsed = JSON.parse(stdout) as unknown;
    const found = findPathValue(parsed);
    if (found) {
      return path.resolve(process.cwd(), found);
    }
  } catch {
    // Use the requested output path when the CLI returns non-JSON or no path field.
  }
  return fallback;
}

function findPathValue(value: unknown): string | null {
  if (typeof value === "string") {
    return looksLikeLocalPath(value) ? value : null;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findPathValue(item);
      if (found) {
        return found;
      }
    }
    return null;
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    for (const key of ["path", "file", "file_path", "filePath", "output", "saved_path", "savedPath"]) {
      const found = findPathValue(record[key]);
      if (found) {
        return found;
      }
    }
    for (const item of Object.values(record)) {
      const found = findPathValue(item);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

function looksLikeLocalPath(value: string): boolean {
  return /[\\/]/.test(value) || /\.(?:png|jpe?g|webp|gif|bmp|pdf|txt|md|csv|xlsx?|pptx?|docx?)$/i.test(value);
}

function botTriggerNames(config: AppConfig): string[] {
  const names = new Set<string>([config.botName]);
  if (config.botOpenId) {
    for (const bot of config.a2aBots) {
      if (bot.openId === config.botOpenId) {
        names.add(bot.name);
      }
    }
  }
  return [...names].filter(Boolean);
}
