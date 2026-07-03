import type { AppConfig } from "./env.js";
import fs from "node:fs";
import path from "node:path";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "./eventParser.js";
import { routeCommand } from "./router.js";
import { draftAgentResponse } from "./agent.js";
import { ConfirmationStore } from "./confirmationStore.js";
import type { CliResult, FeishuMessageEvent, RouteResult } from "./types.js";
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
    const senderIsA2ABot = this.a2aBotOpenIds.has(event.sender.openId || "");
    const route = senderIsA2ABot
      ? routeCommandAsAgentTask(cleanText)
      : routeCommand(cleanText);
    attachConversationContext(route, event, senderIsA2ABot);
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
    const progress = this.startProgressReporter(chatId, route, generation);
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
      const sendResult = await this.sendResponse(chatId, response, route);
      if (!sendResult.ok) {
        console.error(`[agent] failed to reply chat_id=${chatId} code=${sendResult.code} stderr=${preview(sendResult.stderr || sendResult.stdout, 1000)}`);
      } else {
        infoLog(`replied chat_id=${chatId}`);
      }
      return response;
    } finally {
      progress.stop();
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

  private startProgressReporter(chatId: string, route: RouteResult, generation: number): { stop: () => void } {
    if (this.config.agentProvider !== "codex" || !shouldSendProgress(route)) {
      return { stop: () => undefined };
    }
    let stopped = false;
    let timer: NodeJS.Timeout | undefined;
    let interval: NodeJS.Timeout | undefined;
    let count = 0;
    const sendProgress = async (kind: "received" | "working") => {
      if (stopped || !this.isCurrentReplyGeneration(chatId, generation)) {
        return;
      }
      const text =
        kind === "received"
          ? progressReceivedText(route)
          : progressWorkingText(route, ++count);
      try {
        const result = await this.larkCli.sendText(chatId, text);
        if (!result.ok) {
          debugLog(`progress send failed chat_id=${chatId} code=${result.code} stderr=${preview(result.stderr || result.stdout, 500)}`);
        }
      } catch (error) {
        debugLog(`progress send threw chat_id=${chatId} error=${error instanceof Error ? error.message : String(error)}`);
      }
    };
    void sendProgress("received");
    timer = setTimeout(() => {
      void sendProgress("working");
      interval = setInterval(() => void sendProgress("working"), this.config.codexProgressIntervalMs);
    }, this.config.codexProgressInitialMs);
    return {
      stop: () => {
        stopped = true;
        if (timer) {
          clearTimeout(timer);
        }
        if (interval) {
          clearInterval(interval);
        }
      }
    };
  }

  private async sendResponse(chatId: string, response: string, route: RouteResult): Promise<CliResult> {
    const outbound = ensureCoordinatorMentionForA2AReply(response, route, this.config.a2aBots);
    const chunks = splitResponseForFeishu(outbound, this.config.a2aBots);
    let lastResult: CliResult = { ok: true, code: 0, stdout: "", stderr: "" };
    for (let index = 0; index < chunks.length; index += 1) {
      const isLast = index === chunks.length - 1;
      const chunk = chunks[index];
      const richResponse = isLast ? this.toRichTextWithA2AMentions(chunk) : null;
      lastResult = richResponse
        ? await this.larkCli.sendPost(chatId, richResponse)
        : await this.larkCli.sendText(chatId, isLast ? chunk : neutralizeA2AMentions(chunk, this.config.a2aBots));
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
    let hasMention = false;
    for (const match of value.matchAll(mentionPattern)) {
      const matchText = match[0];
      const index = match.index ?? 0;
      if (index > cursor) {
        elements.push({ tag: "text", text: value.slice(cursor, index) });
      }
      const bot = resolveMentionBot(matchText, this.config.a2aBots);
      if (bot && !hasMention) {
        elements.push({ tag: "at", user_id: bot.openId, user_name: bot.name });
        hasMention = true;
      } else if (bot) {
        elements.push({ tag: "text", text: neutralizedMentionText(matchText, bot) });
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

function attachConversationContext(route: RouteResult, event: FeishuMessageEvent, senderIsA2ABot: boolean): RouteResult {
  route.context = {
    chatType: event.chatType,
    isPrivate: isPrivateChat(event.chatType),
    senderIsA2ABot
  };
  return route;
}

function isPrivateChat(chatType: string | undefined): boolean {
  return /^(p2p|private|single)$/i.test(chatType ?? "");
}

function shouldSendProgress(route: RouteResult): boolean {
  if (route.intent !== "unknown") {
    return false;
  }
  return route.plan.executable || /(?:Phase\s*\d+|开发|实现|修复|返工|GUI|Lumerical|FDTD|仿真|本地文件|代码|自测|产物)/i.test(route.cleanText);
}

function progressReceivedText(route: RouteResult): string {
  if (route.context?.isPrivate) {
    return "[代码执行官处理中] 已收到私聊任务，开始执行。本条是进度提示；最终结果会直接回复你。";
  }
  return "[代码执行官处理中] 已收到任务，开始执行。本条是进度提示；最终结果完成后再按协作流程回报项目调度官。";
}

function progressWorkingText(route: RouteResult, count: number): string {
  const suffix = route.context?.isPrivate
    ? "我会在最终结果里说明已完成项、阻塞点和下一步，并直接回复你。"
    : "我会在最终结果里说明已完成项、阻塞点和下一步。";
  return `[代码执行官处理中] 仍在执行第 ${count} 轮检查/处理。若任务涉及 GUI 或长耗时步骤，${suffix}`;
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
