import type { PendingConfirmation, RouteResult } from "./types.js";

export class ConfirmationStore {
  private readonly pending = new Map<string, PendingConfirmation>();

  constructor(private readonly timeoutMs: number) {}

  create(chatId: string, senderKey: string, route: RouteResult, now = Date.now()): PendingConfirmation {
    this.prune(now);
    const key = `${chatId}:${senderKey}`;
    const item: PendingConfirmation = {
      key,
      chatId,
      senderKey,
      createdAt: now,
      expiresAt: now + this.timeoutMs,
      route
    };
    this.pending.set(key, item);
    return item;
  }

  consumeIfConfirmed(chatId: string, senderKey: string, text: string, now = Date.now()): PendingConfirmation | null {
    this.prune(now);
    if (text.trim() !== "\u786e\u8ba4") {
      return null;
    }
    const key = `${chatId}:${senderKey}`;
    const item = this.pending.get(key);
    if (!item) {
      return null;
    }
    this.pending.delete(key);
    return item;
  }

  prune(now = Date.now()): void {
    for (const [key, item] of this.pending) {
      if (item.expiresAt <= now) {
        this.pending.delete(key);
      }
    }
  }
}
