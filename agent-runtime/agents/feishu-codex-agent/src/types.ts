export type MessageIdentity = {
  openId?: string;
  userId?: string;
  unionId?: string;
  senderType?: string;
};

export type FeishuMessageEvent = {
  chatId: string;
  messageId: string;
  sender: MessageIdentity;
  content: string;
  plainText: string;
  messageType: string;
  createTime?: string;
  chatType?: string;
  mentions: string[];
  raw: unknown;
};

export type RouteIntent =
  | "greeting"
  | "summarize"
  | "baseCreate"
  | "baseWrite"
  | "docSearch"
  | "docCreate"
  | "apps"
  | "task"
  | "calendar"
  | "unknown";

export type CommandPlan = {
  title: string;
  commands: string[][];
  executable: boolean;
  requiresConfirmation: boolean;
  confirmationReason?: string;
  responsePreview: string;
};

export type RouteResult = {
  intent: RouteIntent;
  cleanText: string;
  plan: CommandPlan;
  context?: {
    chatType?: string;
    isPrivate: boolean;
    senderIsA2ABot: boolean;
  };
};

export type CliResult = {
  ok: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
};

export type PendingConfirmation = {
  key: string;
  chatId: string;
  senderKey: string;
  createdAt: number;
  expiresAt: number;
  route: RouteResult;
};
