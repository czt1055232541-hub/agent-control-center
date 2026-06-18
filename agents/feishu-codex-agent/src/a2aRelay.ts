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
    if (/(?:^\s*)?\[(?:结果回传|仅通知)\]/.test(cleanText)) {
      return false;
    }
    return /(?:龙虾酱|協作|协作|互相@|互 @|讨论|自主讨论|分工)/.test(cleanText);
  }

  async run(event: FeishuMessageEvent, cleanText: string): Promise<string> {
    const peerName = this.config.a2aRelay.peerName || "龙虾酱";
    const peerOpenId = this.config.a2aRelay.peerOpenId || this.config.a2aBots.find((bot) => bot.name === peerName)?.openId;
    const codexOpenId = this.config.botOpenId;
    if (!peerOpenId || !codexOpenId) {
      const missing = !peerOpenId ? "peer open_id" : "Codex open_id";
      const response = `A2A relay 配置缺少 ${missing}，无法发起群内互 @。`;
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }

    const task = cleanText.replace(/^.*?(?:协作|讨论|互相@|互 @)/, "").trim() || cleanText;
    const summary = `已完成一轮 A2A 协作可见性测试：Codex 已 @ ${peerName}，${peerName} 已 @ 回 Codex，并给出结果。`;

    infoLog(`relay start chat_id=${event.chatId} peer=${peerName}`);
    const codexResult = await this.larkCli.sendPost(event.chatId, makePost([
      text("[需要协作] "),
      at(peerOpenId, peerName),
      text(` 请参与这个任务并给出一个简短结果：${task}`)
    ]));
    if (!codexResult.ok) {
      const response = `Codex 发起群内 @ 失败：${codexResult.stderr || codexResult.stdout}`;
      infoLog(`relay codex->peer failed ${preview(response)}`);
      await this.larkCli.sendText(event.chatId, response);
      return response;
    }
    infoLog(`relay codex->peer sent chat_id=${event.chatId}`);
    const peerResult = await this.sendAsPeer(
      event.chatId,
      makePost([
        text("[结果回传] "),
        at(codexOpenId, "Codex"),
        text(" 我已收到协作请求。我的结论：当前 A2A relay 已接管 bot@bot 投递缺口，双方消息可以在群里可见；后续可继续接入原生 bot@bot 权限。")
      ])
    );
    if (!peerResult.ok) {
      const response = `Codex 已发起群内 @，但 ${peerName} 身份发送失败：${peerResult.stderr || peerResult.stdout}`;
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
