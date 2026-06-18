import type { CommandPlan, RouteIntent, RouteResult } from "./types.js";

export function routeCommand(cleanText: string): RouteResult {
  const text = cleanText.trim();
  const intent = detectIntent(text);
  const plan = buildPlan(intent, text);
  return { intent, cleanText: text, plan };
}

function detectIntent(text: string): RouteIntent {
  if (!text || /^(?:\u4f60\u597d|\u5728\u5417|\u5728\u4e0d\u5728|hi|hello|help|\u5e2e\u52a9|\u4ecb\u7ecd)/i.test(text)) {
    return "greeting";
  }
  if (/(?:\u591a\u7ef4\u8868\u683c|base|\u8868\u683c).*(?:\u521b\u5efa|\u65b0\u5efa)|(?:\u521b\u5efa|\u65b0\u5efa).*(?:\u591a\u7ef4\u8868\u683c|base|\u8868\u683c)/i.test(text)) {
    return "baseCreate";
  }
  if (/(?:\u5199\u5165|\u540c\u6b65|\u8ffd\u52a0).*(?:\u591a\u7ef4\u8868\u683c|base|\u8868\u683c|\u884c\u52a8\u9879)/i.test(text)) {
    return "baseWrite";
  }
  if (/(?:\u641c\u7d22|\u67e5\u627e).*(?:\u6587\u6863|wiki|\u77e5\u8bc6\u5e93|\u9879\u76ee\u8ba1\u5212)|(?:\u6587\u6863|wiki).*\u603b\u7ed3/i.test(text)) {
    return "docSearch";
  }
  if (/(?:\u6574\u7406|\u751f\u6210|\u521b\u5efa|\u65b0\u5efa).*(?:\u6587\u6863|\u98de\u4e66\u6587\u6863|wiki)/i.test(text)) {
    return "docCreate";
  }
  if (/(?:\u603b\u7ed3|\u7eaa\u8981|\u884c\u52a8\u9879|\u8ba8\u8bba)/.test(text)) {
    return "summarize";
  }
  if (/(?:\u5999\u642d|miaoda|spark|\u5e94\u7528|app|\u9759\u6001\u9875\u9762|html|\u53d1\u5e03)/i.test(text)) {
    return "apps";
  }
  if (/(?:\u4efb\u52a1|task|\u5f85\u529e|\u6e05\u5355)/i.test(text)) {
    return "task";
  }
  if (/(?:\u65e5\u5386|\u4f1a\u8bae|\u590d\u76d8\u4f1a|\u5b89\u6392|calendar|agenda)/i.test(text)) {
    return "calendar";
  }
  return "unknown";
}

function buildPlan(intent: RouteIntent, text: string): CommandPlan {
  switch (intent) {
    case "greeting":
      return {
        title: "\u80fd\u529b\u4ecb\u7ecd",
        commands: [],
        executable: true,
        requiresConfirmation: false,
        responsePreview: /^(?:\u5728\u5417|\u5728\u4e0d\u5728)/.test(text)
          ? "\u6211\u5728\u3002\u4f60\u53ef\u4ee5\u76f4\u63a5\u628a\u8981\u5904\u7406\u7684\u4efb\u52a1\u53d1\u7ed9\u6211\u3002"
          : "\u4f60\u597d\uff0c\u6211\u662f\u98de\u4e66\u91cc\u7684 Codex \u52a9\u624b\u3002\u4f60\u53ef\u4ee5\u8ba9\u6211\u603b\u7ed3\u7fa4\u804a\u3001\u521b\u5efa\u6216\u5199\u5165\u591a\u7ef4\u8868\u683c\u3001\u641c\u7d22/\u751f\u6210\u6587\u6863\u3001\u521b\u5efa\u4efb\u52a1\u3001\u67e5\u8be2\u65e5\u5386\uff0c\u6216\u51c6\u5907\u5999\u642d/Spark \u5e94\u7528\u64cd\u4f5c\u3002"
      };
    case "summarize":
      return {
        title: "\u7fa4\u804a\u603b\u7ed3",
        commands: [["im", "+chat-messages-list", "--chat-id", "$CHAT_ID", "--limit", "30", "--as", "bot"]],
        executable: true,
        requiresConfirmation: false,
        responsePreview: "\u6211\u4f1a\u57fa\u4e8e\u5f53\u524d\u6d88\u606f\u548c\u53ef\u83b7\u53d6\u7684\u6700\u8fd1\u4e0a\u4e0b\u6587\u8f93\u51fa\uff1a\u80cc\u666f\u3001\u5173\u952e\u7ed3\u8bba\u3001\u884c\u52a8\u9879\u3001\u8d1f\u8d23\u4eba\u3001\u622a\u6b62\u65f6\u95f4\u3002"
      };
    case "baseCreate":
      return {
        title: "\u521b\u5efa\u591a\u7ef4\u8868\u683c",
        commands: [["base", "+base-create"], ["base", "+table-create"]],
        executable: false,
        requiresConfirmation: false,
        responsePreview: `\u6211\u4f1a\u521b\u5efa\u9879\u76ee\u4efb\u52a1\u591a\u7ef4\u8868\u683c\uff0c\u5e76\u6309\u9700\u6c42\u8bbe\u7f6e\u5b57\u6bb5\u3002\u9700\u6c42\uff1a${text}`
      };
    case "baseWrite":
      return {
        title: "\u5199\u5165\u591a\u7ef4\u8868\u683c\u8bb0\u5f55",
        commands: [["base", "+record-batch-create"]],
        executable: false,
        requiresConfirmation: true,
        confirmationReason: "\u5199\u5165\u6216\u6279\u91cf\u66f4\u65b0\u591a\u7ef4\u8868\u683c\u8bb0\u5f55\u524d\u9700\u8981\u786e\u8ba4\u3002",
        responsePreview: `\u6211\u5c06\u628a\u884c\u52a8\u9879\u5199\u5165\u6307\u5b9a\u591a\u7ef4\u8868\u683c\u3002\u9700\u6c42\uff1a${text}`
      };
    case "docSearch":
      return {
        title: "\u641c\u7d22\u5e76\u603b\u7ed3\u6587\u6863",
        commands: [["docs", "+search"], ["docs", "+fetch"]],
        executable: false,
        requiresConfirmation: false,
        responsePreview: `\u6211\u4f1a\u641c\u7d22\u76f8\u5173\u6587\u6863\u5e76\u603b\u7ed3\u5173\u952e\u5185\u5bb9\u3002\u9700\u6c42\uff1a${text}`
      };
    case "docCreate":
      return {
        title: "\u751f\u6210\u98de\u4e66\u6587\u6863",
        commands: [["docs", "+create"]],
        executable: false,
        requiresConfirmation: false,
        responsePreview: `\u6211\u4f1a\u628a\u4e0a\u4e0b\u6587\u6574\u7406\u6210\u98de\u4e66\u6587\u6863\u5e76\u8fd4\u56de\u94fe\u63a5\u3002\u9700\u6c42\uff1a${text}`
      };
    case "apps":
      return {
        title: "\u5999\u642d/Spark/Apps \u64cd\u4f5c",
        commands: [["apps", "+create"], ["apps", "+html-publish"]],
        executable: false,
        requiresConfirmation: true,
        confirmationReason: "\u521b\u5efa\u6216\u53d1\u5e03\u5999\u642d/Spark/Miaoda \u5e94\u7528\u3001\u9759\u6001\u9875\u9762\u524d\u9700\u8981\u786e\u8ba4\u3002",
        responsePreview: `\u6211\u4f1a\u5148\u68c0\u7d22 lark-cli apps \u80fd\u529b\u5e76\u51c6\u5907\u5e94\u7528\u64cd\u4f5c\u3002\u9700\u6c42\uff1a${text}`
      };
    case "task":
      return {
        title: "\u521b\u5efa\u4efb\u52a1\u6e05\u5355",
        commands: [["task", "+create"]],
        executable: false,
        requiresConfirmation: /(?:\u591a\u4eba|\u6210\u5458|\u5206\u914d|\u8f6c\u4ea4|\u6279\u91cf)/.test(text),
        confirmationReason: "\u6d89\u53ca\u591a\u4eba\u4efb\u52a1\u3001\u8f6c\u4ea4\u6216\u6279\u91cf\u64cd\u4f5c\u524d\u9700\u8981\u786e\u8ba4\u3002",
        responsePreview: `\u6211\u4f1a\u6839\u636e\u8ba8\u8bba\u521b\u5efa\u4efb\u52a1\u3001\u8d1f\u8d23\u4eba\u548c\u622a\u6b62\u65f6\u95f4\u3002\u9700\u6c42\uff1a${text}`
      };
    case "calendar":
      return {
        title: "\u65e5\u5386\u4e0e\u4f1a\u8bae",
        commands: [["calendar", "+agenda"]],
        executable: true,
        requiresConfirmation: /(?:\u9080\u8bf7|\u6210\u5458|\u5927\u5bb6|\u591a\u4eba|\u4f1a\u8bae|\u590d\u76d8\u4f1a)/.test(text),
        confirmationReason: "\u521b\u5efa\u6d89\u53ca\u591a\u4eba\u53c2\u4e0e\u7684\u65e5\u5386\u4e8b\u4ef6\u524d\u9700\u8981\u786e\u8ba4\u3002",
        responsePreview: `\u6211\u4f1a\u67e5\u8be2\u65e5\u5386\u6216\u51c6\u5907\u4f1a\u8bae\u65e5\u7a0b\u3002\u9700\u6c42\uff1a${text}`
      };
    default:
      return {
        title: "\u901a\u7528\u8bf7\u6c42",
        commands: [],
        executable: true,
        requiresConfirmation: false,
        responsePreview: `\u6211\u4f1a\u5148\u7406\u89e3\u4f60\u7684\u8bf7\u6c42\uff0c\u518d\u9009\u62e9 lark-cli \u5feb\u6377\u547d\u4ee4\u6216 OpenAPI \u8c03\u7528\u3002\u8bf7\u6c42\uff1a${text}`
      };
  }
}
