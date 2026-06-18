import { spawnCollect } from "./larkCli.js";
import type { AppConfig } from "./env.js";
import type { RouteResult } from "./types.js";

export async function draftAgentResponse(config: AppConfig, route: RouteResult): Promise<string> {
  if (config.agentProvider === "openai" && config.openaiApiKey) {
    return draftWithOpenAI(config, route);
  }
  if (config.agentProvider === "codex") {
    return draftWithCodex(config, route);
  }
  return localDraft(route);
}

function localDraft(route: RouteResult): string {
  const lines = [
    route.plan.responsePreview,
    "",
    "\u6267\u884c\u7b56\u7565\uff1a\u4f18\u5148\u4f7f\u7528 lark-cli \u5feb\u6377\u547d\u4ee4\uff1b\u4e0d\u8db3\u65f6\u4f7f\u7528 API \u547d\u4ee4\uff1b\u6700\u540e fallback \u5230 `lark-cli api METHOD /open-apis/...`\u3002",
    route.plan.commands.length
      ? `\u8ba1\u5212\u547d\u4ee4\uff1a\n${route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")}`
      : "\u5f53\u524d\u8bf7\u6c42\u4e0d\u9700\u8981\u7acb\u5373\u8c03\u7528 lark-cli\u3002"
  ];
  return lines.join("\n");
}

async function draftWithOpenAI(config: AppConfig, route: RouteResult): Promise<string> {
  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.openaiApiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: config.openaiModel,
      input: [
        {
          role: "system",
          content:
            "\u4f60\u662f\u98de\u4e66\u7fa4\u804a\u91cc\u7684 Codex \u52a9\u624b\u3002\u6839\u636e\u7528\u6237\u8bf7\u6c42\u548c\u8ba1\u5212\uff0c\u7528\u4e2d\u6587\u7b80\u6d01\u56de\u590d\u3002\u4e0d\u8981\u4f2a\u9020\u6267\u884c\u7ed3\u679c\uff1b\u9700\u8981\u786e\u8ba4\u7684\u9ad8\u98ce\u9669\u64cd\u4f5c\u5fc5\u987b\u8981\u6c42\u7528\u6237\u56de\u590d\u201c\u786e\u8ba4\u201d\u3002"
        },
        {
          role: "user",
          content: JSON.stringify(route, null, 2)
        }
      ]
    })
  });
  if (!response.ok) {
    return `${localDraft(route)}\n\nOpenAI \u8c03\u7528\u5931\u8d25\uff1aHTTP ${response.status}`;
  }
  const json = (await response.json()) as { output_text?: string };
  return json.output_text || localDraft(route);
}

 async function draftWithCodex(config: AppConfig, route: RouteResult): Promise<string> {
   const a2aSection = buildA2ASection(config);
   const prompt = [
     "\u4f60\u662f\u98de\u4e66\u7fa4\u804a\u91cc\u7684 Codex \u52a9\u624b\u3002\u6839\u636e\u4ee5\u4e0b\u8def\u7531\u8ba1\u5212\uff0c\u7528\u4e2d\u6587\u7b80\u6d01\u56de\u590d\u3002",
     "\u4e0d\u8981\u4f2a\u9020 lark-cli \u6267\u884c\u7ed3\u679c\uff1b\u9700\u8981\u786e\u8ba4\u7684\u9ad8\u98ce\u9669\u64cd\u4f5c\u5fc5\u987b\u8981\u6c42\u7528\u6237\u56de\u590d\u201c\u786e\u8ba4\u201d\u3002",
     ...(a2aSection ? [a2aSection] : []),
     JSON.stringify(route, null, 2)
   ].join("\n\n");
  const result = await spawnCollect(config.codexCliBin, [...config.codexAgentArgs, prompt]);
  if (!result.ok) {
    return `${localDraft(route)}\n\nCodex CLI \u8c03\u7528\u5931\u8d25\uff1a${result.stderr || result.code}`;
  }
   return result.stdout.trim() || localDraft(route);
 }

 function buildA2ASection(config: AppConfig): string | null {
   const bots = config.a2aBots;
   if (bots.length === 0) {
     return null;
   }
   const botListLines = bots
     .map((b) => {
       const desc = b.description ? ` \u2014 ${b.description}` : "";
       return `- @${b.name}${desc}`;
     })
     .join("\n");
   return [
     "[A2A \u7fa4\u5185\u534f\u4f5c\u89c4\u5219]",
     "",
     "\u672c\u7fa4\u4e2d\u6709\u5176\u4ed6\u673a\u5668\u4eba\u53ef\u4ee5\u534f\u4f5c\uff1a",
     botListLines,
     "",
     "\u534f\u4f5c\u89c4\u5219\uff1a",
     "- \u9ed8\u8ba4\u4e0d\u4e3b\u52a8 @ \u5176\u4ed6\u673a\u5668\u4eba\uff0c\u9664\u975e\u7528\u6237\u660e\u786e\u8981\u6c42\u6216\u89e6\u53d1\u534f\u4f5c\u5173\u952e\u5b57\uff08\u201c\u7fa4\u5185\u534f\u4f5c\u201d\u201c\u5206\u914d\u4efb\u52a1\u201d\u201c\u8ba9 xx \u770b\u770b\u201d\uff09",
     "- \u6bcf\u6b21\u56de\u590d\u6700\u591a @ 1 \u4e2a\u673a\u5668\u4eba",
     "- \u53ea\u662f\u63d0\u5230\u67d0\u4e2a\u673a\u5668\u4eba\u65f6\uff0c\u7528\u540d\u5b57\u5373\u53ef\uff0c\u4e0d\u8981\u7528 @",
     "- \u5f53\u5176\u4ed6\u673a\u5668\u4eba @ \u4f60\u5e76\u8bf7\u4f60\u6267\u884c\u4efb\u52a1\u65f6\uff0c\u5904\u7406\u5b8c\u540e\u5fc5\u987b @ \u56de\u53d1\u8d77\u8005\u6c47\u62a5\u7ed3\u679c",
     "- \u5982\u679c\u5bf9\u65b9\u53ea\u662f\u901a\u77e5\u4f60\uff08\u5e26\u6709 [\u4ec5\u901a\u77e5] \u6807\u8bb0\uff09\uff0c\u4e0d\u9700\u8981 @ \u56de\u5bf9\u65b9",
     "- \u6536\u5230\u7ed3\u679c\u56de\u4f20\u540e\u4e0d\u8981\u518d @ \u56de\u5bf9\u65b9\uff0c\u76f4\u63a5\u6574\u7406\u7ed3\u679c\u56de\u590d\u7528\u6237",
     "- @ \u5176\u4ed6\u673a\u5668\u4eba\u65f6\uff0c\u76f4\u63a5\u5199 @\u540d\u5b57 \u5373\u53ef\uff08\u4f8b\u5982\uff1a@\u9f99\u867e\u9171 \u8bf7\u5e2e\u5fd9\u5206\u6790\u4e00\u4e0b\uff09",
     "- \u4ec5\u901a\u77e5\u65f6\u52a0\u4e0a [\u4ec5\u901a\u77e5] \u6807\u8bb0\uff08\u4f8b\u5982\uff1a[\u4ec5\u901a\u77e5] @\u9f99\u867e\u9171 \u6392\u671f\u5df2\u786e\u8ba4\uff09"
   ].join("\n");
 }
