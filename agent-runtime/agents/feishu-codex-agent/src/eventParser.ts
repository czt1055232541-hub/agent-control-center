import type { AppConfig } from "./env.js";
import type { FeishuMessageEvent, MessageAttachment } from "./types.js";

export function parseMessageEvent(raw: unknown): FeishuMessageEvent | null {
  const root = asRecord(raw);
  const event = asRecord(root.event ?? root.data ?? root);
  const message = asRecord(event.message ?? event);
  const sender = asRecord(event.sender ?? message.sender ?? root.sender);
  const senderId = asRecord(sender.sender_id ?? sender.senderId ?? sender);
  const chatId = stringValue(message.chat_id ?? message.chatId ?? event.chat_id);
  const messageId = stringValue(message.message_id ?? message.messageId ?? message.id ?? event.message_id ?? event.id);
  if (!chatId || !messageId) {
    return null;
  }
  const rawContent = stringValue(message.content ?? event.content) ?? "";
  const plainText = extractPlainText(rawContent);
  const attachments = extractAttachments(rawContent, stringValue(message.message_type ?? message.messageType));
  const mentions = extractMentions(message, plainText);
  return {
    chatId,
    messageId,
    sender: {
      openId: stringValue(senderId.open_id ?? senderId.openId ?? message.sender_id ?? event.sender_id),
      userId: stringValue(senderId.user_id ?? senderId.userId),
      unionId: stringValue(senderId.union_id ?? senderId.unionId),
      senderType: stringValue(sender.sender_type ?? sender.senderType ?? sender.type)
    },
    content: rawContent,
    plainText,
    messageType: stringValue(message.message_type ?? message.messageType) ?? "unknown",
    attachments,
    createTime: stringValue(message.create_time ?? message.createTime ?? event.create_time),
    chatType: stringValue(message.chat_type ?? message.chatType ?? event.chat_type),
    mentions,
    raw
  };
}

export function shouldIgnoreSelf(event: FeishuMessageEvent, config: AppConfig): boolean {
   const configuredA2ABotIds = new Set(config.a2aBots.map((bot) => bot.openId));
   if (config.botOpenId && event.sender.openId === config.botOpenId) {
     return true;
   }
   if (config.botUserId && event.sender.userId === config.botUserId) {
     return true;
   }
   if (config.botUnionId && event.sender.unionId === config.botUnionId) {
     return true;
   }
   if (event.sender.senderType === "bot" && (!event.sender.openId || !configuredA2ABotIds.has(event.sender.openId))) {
     return true;
   }
   return false;
 }

export function shouldRespond(event: FeishuMessageEvent, config: AppConfig): boolean {
  if (shouldIgnoreSelf(event, config)) {
    return false;
  }
  const text = event.plainText.trim();
  if (!text && (event.attachments ?? []).length === 0) {
    return false;
  }
  const isPrivate = /^(p2p|private|single)$/i.test(event.chatType ?? "");
  const triggerNames = ownBotTriggerNames(config);
  const mentioned = eventMentionsThisBot(event, config, triggerNames) ||
    triggerNames.some((name) => new RegExp(`@\\s*${escapeRegExp(name)}`, "i").test(text));
  const startsWithTrigger = triggerNames.some((name) => new RegExp(`^\\s*(?:/codex|${escapeRegExp(name)})\\b`, "i").test(text));
  return isPrivate || mentioned || startsWithTrigger;
}

export function cleanTriggerText(text: string, botName: string | string[] = "Codex"): string {
  const names = Array.isArray(botName) ? botName : [botName];
  let cleaned = text;
  for (const name of names) {
    const bot = escapeRegExp(name);
    cleaned = cleaned
      .replace(new RegExp(`^\\s*@\\s*${bot}\\s*`, "i"), "")
      .replace(new RegExp(`^\\s*(?:/codex|${bot})\\b[:\\uFF1A,\\uFF0C\\s]*`, "i"), "")
      .trim();
  }
  return cleaned;
}

function extractPlainText(rawContent: string): string {
  if (!rawContent) {
    return "";
  }
  try {
    const parsed = JSON.parse(rawContent) as unknown;
    const record = asRecord(parsed);
    const text = stringValue(record.text ?? record.title ?? record.content);
    if (text) {
      return text;
    }
    const postText = extractPostPlainText(record);
    return postText || rawContent;
  } catch {
    return rawContent;
  }
}

function extractPostPlainText(record: Record<string, unknown>): string {
  const locale = asRecord(record.zh_cn ?? record.en_us ?? record.ja_jp);
  const blocks = Array.isArray(locale.content) ? locale.content : [];
  const lines: string[] = [];
  for (const block of blocks) {
    const elements = Array.isArray(block) ? block : [];
    const line = elements.map((element) => {
      const item = asRecord(element);
      const tag = stringValue(item.tag);
      if (tag === "text") {
        return stringValue(item.text) ?? "";
      }
      if (tag === "at") {
        return `@${stringValue(item.user_name) ?? stringValue(item.user_id) ?? ""}`;
      }
      return stringValue(item.text) ?? "";
    }).join("");
    if (line) {
      lines.push(line);
    }
  }
  return lines.join("\n").trim();
}

function extractMentions(message: Record<string, unknown>, plainText: string): string[] {
  const values = new Set<string>();
  const mentions = Array.isArray(message.mentions) ? message.mentions : [];
  for (const mention of mentions) {
    const item = asRecord(mention);
    for (const key of ["name", "user_name", "key", "id", "open_id", "openId", "user_id", "userId", "union_id", "unionId", "tenant_key"]) {
      const value = stringValue(item[key]);
      if (value) {
        values.add(value);
      }
    }
  }
  for (const match of plainText.matchAll(/@\s*([A-Za-z0-9_\-\u4e00-\u9fa5]+)/g)) {
    values.add(match[1]);
  }
  return [...values];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractAttachments(rawContent: string, messageType: string | undefined): MessageAttachment[] {
  if (!rawContent) {
    return [];
  }
  try {
    const parsed = JSON.parse(rawContent) as unknown;
    const found: MessageAttachment[] = [];
    collectAttachments(parsed, messageType, found);
    return dedupeAttachments(found);
  } catch {
    return [];
  }
}

function collectAttachments(value: unknown, messageType: string | undefined, found: MessageAttachment[]): void {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectAttachments(item, messageType, found);
    }
    return;
  }
  const record = asRecord(value);
  if (Object.keys(record).length === 0) {
    return;
  }
  const tag = stringValue(record.tag);
  const imageKey = stringValue(record.image_key ?? record.imageKey);
  if (imageKey) {
    found.push({
      kind: "image",
      key: imageKey,
      name: stringValue(record.file_name ?? record.fileName ?? record.name),
      mimeType: stringValue(record.mime_type ?? record.mimeType)
    });
  }
  const fileKey = stringValue(record.file_key ?? record.fileKey);
  if (fileKey) {
    found.push({
      kind: /image/i.test(messageType ?? "") || tag === "img" ? "image" : "file",
      key: fileKey,
      name: stringValue(record.file_name ?? record.fileName ?? record.name),
      mimeType: stringValue(record.mime_type ?? record.mimeType)
    });
  }
  for (const item of Object.values(record)) {
    if (item && typeof item === "object") {
      collectAttachments(item, messageType, found);
    }
  }
}

function dedupeAttachments(items: MessageAttachment[]): MessageAttachment[] {
  const seen = new Set<string>();
  const deduped: MessageAttachment[] = [];
  for (const item of items) {
    const id = `${item.kind}:${item.key}`;
    if (!seen.has(id)) {
      seen.add(id);
      deduped.push(item);
    }
  }
  return deduped;
}

function ownBotTriggerNames(config: AppConfig): string[] {
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

function eventMentionsThisBot(event: FeishuMessageEvent, config: AppConfig, triggerNames: string[]): boolean {
  const mentionValues = event.mentions.map((mention) => mention.trim()).filter(Boolean);
  const lowerTriggerNames = triggerNames.map((name) => name.toLowerCase());
  const ownIds = [config.botOpenId, config.botUserId, config.botUnionId].filter(Boolean) as string[];
  return mentionValues.some((mention) => {
    const lower = mention.toLowerCase();
    return lowerTriggerNames.some((name) => lower.includes(name)) || ownIds.includes(mention);
  });
}
