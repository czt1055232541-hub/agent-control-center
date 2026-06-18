import type { AppConfig } from "./env.js";
import { cleanTriggerText, parseMessageEvent, shouldRespond } from "./eventParser.js";
import { routeCommand } from "./router.js";
import { draftAgentResponse } from "./agent.js";
import { ConfirmationStore } from "./confirmationStore.js";
import type { FeishuMessageEvent, RouteResult } from "./types.js";
import { LarkCli } from "./larkCli.js";

 export class MessageHandler {
   private readonly confirmations: ConfirmationStore;
   private readonly a2aBotOpenIds: Set<string>;

   constructor(
     private readonly config: AppConfig,
     private readonly larkCli: LarkCli
   ) {
     this.confirmations = new ConfirmationStore(config.confirmTimeoutMs);
     this.a2aBotOpenIds = new Set(config.a2aBots.map((b) => b.openId));
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
    await this.handleEvent(event);
  }

  async handleEvent(event: FeishuMessageEvent): Promise<string> {
    const cleanText = cleanTriggerText(event.plainText, this.config.botName);
    const senderKey = senderKeyFor(event);
    const confirmed = this.confirmations.consumeIfConfirmed(event.chatId, senderKey, cleanText);
    if (confirmed) {
      return this.executeAndReply(event.chatId, confirmed.route, true);
    }
    const route = routeCommand(cleanText);
    if (route.plan.requiresConfirmation) {
      this.confirmations.create(event.chatId, senderKey, route);
      const response = formatConfirmation(route);
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }
    return this.executeAndReply(event.chatId, route, false);
  }

   private async executeAndReply(chatId: string, route: RouteResult, confirmed: boolean): Promise<string> {
     const agentText = await draftAgentResponse(this.config, route);
     const shouldRunCommands = this.config.dryRun || route.plan.executable;
     const commandResults = [];
     if (shouldRunCommands) {
       for (const command of route.plan.commands) {
         const result = await this.larkCli.run(resolveCommand(command, chatId));
         commandResults.push({ command: resolveCommand(command, chatId), result });
       }
     }
     let response = [
       confirmed ? "\u5df2\u6536\u5230\u786e\u8ba4\uff0c\u7ee7\u7eed\u6267\u884c\u3002" : "",
       agentText,
       !shouldRunCommands && route.plan.commands.length ? formatPlanOnly(route) : "",
       commandResults.length ? formatCommandResults(commandResults, this.config.dryRun) : ""
     ]
       .filter(Boolean)
       .join("\n\n");
     if (this.config.a2aBots.length > 0) {
       response = this.convertAtTags(response);
     }
     const sendResult = await this.larkCli.sendText(chatId, response);
    if (!sendResult.ok) {
      console.error(`[agent] failed to reply chat_id=${chatId} code=${sendResult.code} stderr=${preview(sendResult.stderr || sendResult.stdout, 1000)}`);
    } else {
      infoLog(`replied chat_id=${chatId}`);
    }
     return response;
   }

   private convertAtTags(text: string): string {
     let result = text;
     for (const bot of this.config.a2aBots) {
       const escapedName = bot.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
       const pattern = new RegExp(`@${escapedName}`, "g");
       result = result.replace(pattern, `<at user_id="${bot.openId}">${bot.name}</at>`);
     }
     return result;
   }
 }

function resolveCommand(command: string[], chatId: string): string[] {
  return command.map((part) => (part === "$CHAT_ID" ? chatId : part));
}

function formatConfirmation(route: RouteResult): string {
  return [
    "\u6211\u5c06\u6267\u884c\u4ee5\u4e0b\u64cd\u4f5c\uff0c\u8bf7\u56de\u590d \u786e\u8ba4 \u7ee7\u7eed",
    "",
    `\u64cd\u4f5c\uff1a${route.plan.title}`,
    route.plan.confirmationReason ? `\u539f\u56e0\uff1a${route.plan.confirmationReason}` : "",
    route.plan.commands.length ? `\u8ba1\u5212\u547d\u4ee4\uff1a\n${route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")}` : "",
    "\u5982\u679c 10 \u5206\u949f\u5185\u672a\u786e\u8ba4\uff0c\u672c\u6b21\u64cd\u4f5c\u5c06\u53d6\u6d88\u3002"
  ]
    .filter(Boolean)
    .join("\n");
}

function formatPlanOnly(route: RouteResult): string {
  return [
    "\u5df2\u751f\u6210\u6267\u884c\u8ba1\u5212\uff0c\u4f46\u8be5\u7c7b\u64cd\u4f5c\u9700\u8981\u8865\u9f50\u76ee\u6807\u6587\u6863\u3001\u591a\u7ef4\u8868\u683c token\u3001\u5b57\u6bb5\u6216\u53d1\u5e03\u53c2\u6570\u540e\u624d\u80fd\u771f\u6b63\u6267\u884c\u3002",
    route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")
  ].join("\n");
}

function formatCommandResults(items: Array<{ command: string[]; result: { ok: boolean; stdout: string; stderr: string } }>, dryRun: boolean): string {
  const header = dryRun ? "DRY_RUN \u8ba1\u5212\u547d\u4ee4\uff1a" : "lark-cli \u6267\u884c\u7ed3\u679c\uff1a";
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
