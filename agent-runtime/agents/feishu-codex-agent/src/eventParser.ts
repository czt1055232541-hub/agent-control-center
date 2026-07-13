import type { AppConfig } from "./env.js";
import type { FeishuMessageEvent } from "./types.js";

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
  if (!text) {
    return false;
  }
  const botName = escapeRegExp(config.botName);
  const isPrivate = /^(p2p|private|single)$/i.test(event.chatType ?? "");
  const mentioned = event.mentions.some((mention) => mention.toLowerCase().includes(config.botName.toLowerCase())) ||
    new RegExp(`@\\s*${botName}`, "i").test(text);
  const startsWithCodex = new RegExp(`^\\s*(?:/codex|${botName})\\b`, "i").test(text);
  return isPrivate || mentioned || startsWithCodex;
}

export function cleanTriggerText(text: string, botName = "Codex"): string {
  const bot = escapeRegExp(botName);
  return text
    .replace(new RegExp(`^\\s*@\\s*${bot}\\s*`, "i"), "")
    .replace(new RegExp(`^\\s*(?:/codex|${bot})\\b[:\\uFF1A,\\uFF0C\\s]*`, "i"), "")
    .trim();
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
    for (const key of ["name", "key", "id", "tenant_key"]) {
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
