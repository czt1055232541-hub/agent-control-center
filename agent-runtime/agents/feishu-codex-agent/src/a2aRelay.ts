import type { AppConfig } from "./env.js";
import type { FeishuMessageEvent } from "./types.js";
import { LarkCli, type LarkPostContent } from "./larkCli.js";

export class A2ARelay {
  constructor(
    private readonly config: AppConfig,
    private readonly larkCli: LarkCli
  ) {}

  shouldHandle(event: FeishuMessageEvent, cleanText: string): boolean {
    if (!this.config.a2aRelay.enabled) {
      return false;
    }
    if (!this.config.a2aRelay.groupChatId || event.chatId !== this.config.a2aRelay.groupChatId) {
      return false;
    }
    if (!/^(group|chat)$/i.test(event.chatType ?? "group")) {
      return false;
    }
    if (/^\s*\[(?:\u7ed3\u679c\u56de\u4f20|\u4ec5\u901a\u77e5)\]/.test(cleanText)) {
      return false;
    }
    return /(?:A2A\s*relay|relay\s*test|bot-to-bot|bot2bot|\u4e92\u76f8\s*@\s*\u6d4b\u8bd5|\u673a\u5668\u4eba\s*@\s*\u673a\u5668\u4eba)/i.test(cleanText);
  }

  async run(event: FeishuMessageEvent, cleanText: string): Promise<string> {
    const peerName = this.config.a2aRelay.peerName || "\u8d28\u91cf\u5ba1\u8ba1\u5b98";
    const peerOpenId = this.config.a2aRelay.peerOpenId || this.config.a2aBots.find((bot) => bot.name === peerName)?.openId;
    const codexOpenId = this.config.botOpenId;
    if (!peerOpenId || !codexOpenId) {
      const missing = !peerOpenId ? "peer open_id" : "Codex open_id";
      const response = `A2A relay \u914d\u7f6e\u7f3a\u5c11 ${missing}\uff0c\u65e0\u6cd5\u53d1\u8d77\u7fa4\u5185\u4e92 @\u3002`;
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }

    const task = cleanText.replace(/^.*?(?:A2A\s*relay|relay\s*test|bot-to-bot|bot2bot|\u4e92\u76f8\s*@\s*\u6d4b\u8bd5|\u673a\u5668\u4eba\s*@\s*\u673a\u5668\u4eba)/i, "").trim() || cleanText;
    const summary = `\u5df2\u5b8c\u6210\u4e00\u8f6e A2A relay \u53ef\u89c1\u6027\u6d4b\u8bd5\uff1aCodex \u5df2 @ ${peerName}\uff0c${peerName} \u5df2 @ \u56de Codex\uff0c\u5e76\u7ed9\u51fa\u7ed3\u679c\u3002`;

    infoLog(`relay start chat_id=${event.chatId} peer=${peerName}`);
    const codexResult = await this.larkCli.sendPost(event.chatId, makePost([
      text("[\u9700\u8981\u534f\u4f5c] "),
      at(peerOpenId, peerName),
      text(` \u8bf7\u53c2\u4e0e\u8fd9\u4e2a relay \u6d4b\u8bd5\u5e76\u7ed9\u51fa\u4e00\u4e2a\u7b80\u77ed\u7ed3\u679c\uff1a${task}`)
    ]));
    if (!codexResult.ok) {
      const response = `Codex \u53d1\u8d77\u7fa4\u5185 @ \u5931\u8d25\uff1a${codexResult.stderr || codexResult.stdout}`;
      infoLog(`relay codex->peer failed ${preview(response)}`);
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }
    infoLog(`relay codex->peer sent chat_id=${event.chatId}`);

    const peerResult = await this.sendAsPeer(
      event.chatId,
      makePost([
        text("[\u7ed3\u679c\u56de\u4f20] "),
        at(codexOpenId, "Codex"),
        text(" \u6211\u5df2\u6536\u5230 relay \u6d4b\u8bd5\u8bf7\u6c42\u3002\u7ed3\u8bba\uff1abot-to-bot @ \u6295\u9012\u94fe\u8def\u53ef\u89c1\u3002")
      ])
    );
    if (!peerResult.ok) {
      const response = `Codex \u5df2\u53d1\u8d77\u7fa4\u5185 @\uff0c\u4f46 ${peerName} \u8eab\u4efd\u53d1\u9001\u5931\u8d25\uff1a${peerResult.stderr || peerResult.stdout}`;
      infoLog(`relay peer->codex failed ${preview(response)}`);
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }
    infoLog(`relay peer->codex sent chat_id=${event.chatId}`);
    await this.larkCli.sendText(event.chatId, summary);
    infoLog(`relay summary sent chat_id=${event.chatId}`);
    return summary;
  }

  private sendAsPeer(chatId: string, content: LarkPostContent) {
    const home = this.config.a2aRelay.peerCliHome;
    const env = home
      ? {
          ...process.env,
          HOME: home,
          USERPROFILE: home,
          APPDATA: `${home}\\AppData\\Roaming`,
          LOCALAPPDATA: `${home}\\AppData\\Local`
        }
      : process.env;
    return this.larkCli.sendPost(chatId, content, { env, identity: "bot" });
  }
}

function infoLog(message: string): void {
  if ((process.env.LOG_LEVEL || "info").toLowerCase() !== "silent") {
    console.error(`[agent] ${message}`);
  }
}

function preview(value: string, max = 500): string {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function makePost(elements: LarkPostContent["zh_cn"]["content"][number]): LarkPostContent {
  return {
    zh_cn: {
      content: [elements]
    }
  };
}

function text(value: string): { tag: "text"; text: string } {
  return { tag: "text", text: value };
}

function at(userId: string, userName: string): { tag: "at"; user_id: string; user_name: string } {
  return { tag: "at", user_id: userId, user_name: userName };
}
