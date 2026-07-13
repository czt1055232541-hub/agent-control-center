import { spawnCollect } from "./larkCli.js";
import type { AppConfig } from "./env.js";
import type { RouteResult } from "./types.js";
import { createCodexStreamWriter } from "./codexStream.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const coordinator = "\u9879\u76ee\u8c03\u5ea6\u5b98";
const developer = "\u4ee3\u7801\u6267\u884c\u5b98";
const opsValidator = "\u8fd0\u7ef4\u9a8c\u8bc1\u5b98";
const auditor = "\u8d28\u91cf\u5ba1\u8ba1\u5b98";
const archivist = "\u9879\u76ee\u6863\u6848\u5b98";

export async function draftAgentResponse(config: AppConfig, route: RouteResult): Promise<string> {
  if (config.agentProvider === "openai" && config.openaiApiKey) {
    infoLog("draft provider=openai");
    return draftWithOpenAI(config, route);
  }
  if (config.agentProvider === "codex") {
    infoLog("draft provider=codex");
    return draftWithCodex(config, route);
  }
  infoLog("draft provider=local");
  return localDraft(route);
}

function localDraft(route: RouteResult): string {
  if (route.intent === "greeting") {
    return route.plan.responsePreview;
  }
  const lines = [
    route.plan.responsePreview,
    "",
    "Execution policy: prefer lark-cli shortcuts; use API commands when needed; fallback to `lark-cli api METHOD /open-apis/...` only when necessary.",
    route.plan.commands.length
      ? `Planned commands:\n${route.plan.commands.map((cmd) => `- lark-cli ${cmd.join(" ")}`).join("\n")}`
      : "No immediate lark-cli command is required for this request."
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
          content: `You are ${developer} in a Feishu group. Reply concisely in Chinese. Do not fabricate execution results. Ask for explicit confirmation before high-risk actions.`
        },
        {
          role: "user",
          content: JSON.stringify(route, null, 2)
        }
      ]
    })
  });
  if (!response.ok) {
    return `${localDraft(route)}\n\nOpenAI call failed: HTTP ${response.status}`;
  }
  const json = (await response.json()) as { output_text?: string };
  return json.output_text || localDraft(route);
}

async function draftWithCodex(config: AppConfig, route: RouteResult): Promise<string> {
  const a2aSection = buildA2ASection(config);
  const conversationSection = buildConversationSection(route);
  const prompt = [
    `You are ${developer}. Reply concisely in Chinese according to the route plan below.`,
    "Do not fabricate lark-cli execution results. Ask the user to reply with confirmation before high-risk actions.",
    "Do not try to send Feishu group messages with lark-cli, and do not decide whether the Feishu bot needs auth login. The outer Feishu handler sends your final reply.",
    "For A2A collaboration tasks, report only task results, artifact paths, self-test results, and the next agent to notify. Never suggest running `lark-cli auth login`.",
    "For Lumerical, MODE, FDTD, lumapi, GUI startup, or license checkout tasks, expect long waits. Prefer small observable steps, write the script first, run only the requested step, and report any long-running GUI/license wait as progress instead of assuming failure.",
    "Do not kill GUI, Lumerical, MODE, FDTD, license, or simulation processes just because they are slow. If a process appears to be waiting, report the script path, command, visible output, elapsed time, and likely blocker.",
    conversationSection,
    ...(a2aSection ? [a2aSection] : []),
    JSON.stringify(route, null, 2)
  ].join("\n\n");
  const outputFile = path.join(os.tmpdir(), `feishu-codex-agent-${Date.now()}.md`);
  const codexCliBin = resolveCodexCliBin(config.codexCliBin);
  const codexEnv = { ...process.env, CODEX_CLI_BIN: codexCliBin, CODEX_CLI_PATH: codexCliBin };
  const stream = createCodexStreamWriter({
    messageId: route.context?.messageId,
    chatType: route.context?.chatType
  });
  const result = await spawnCollect(
    codexCliBin,
    [...config.codexAgentArgs, "--output-last-message", outputFile, "-"],
    prompt,
    "auto",
    codexEnv,
    config.codexCliTimeoutMs,
    {
      onStdout: (text) => stream.write({ phase: "stdout", stream: "stdout", text }),
      onStderr: (text) => stream.write({ phase: "stderr", stream: "stderr", text })
    }
  );
  if (!result.ok) {
    const failure = summarizeCodexFailure(result.stderr, result.code);
    stream.write({ phase: "error", stream: "stage", text: failure });
    infoLog(`draft provider=codex failed code=${result.code} stderr=${preview(failure, 800)}`);
    return formatCodexFailure(route, failure);
  }
  infoLog("draft provider=codex completed");
  const finalMessage = readOutputFile(outputFile);
  stream.write({ phase: "complete", stream: "stage", text: finalMessage ? "Codex CLI run completed with final message." : "Codex CLI run completed; using stdout/local fallback." });
  return finalMessage || result.stdout.trim() || localDraft(route);
}

export function resolveCodexCliBin(configuredBin: string): string {
  const configured = configuredBin || "codex";
  const configuredBase = path.basename(configured).toLowerCase();
  if (configuredBase && configuredBase !== "codex.exe" && configuredBase !== "codex") {
    return configured;
  }
  const current = readCodexCliPathFromConfig();
  if (current && fs.existsSync(current)) {
    return current;
  }
  return configured;
}

function readCodexCliPathFromConfig(): string | null {
  const codexHome = process.env.CODEX_HOME;
  if (!codexHome) {
    return null;
  }
  const configPath = path.join(codexHome, "config.toml");
  try {
    if (!fs.existsSync(configPath)) {
      return null;
    }
    const text = fs.readFileSync(configPath, "utf8");
    const match = /^\s*CODEX_CLI_PATH\s*=\s*(['"])(.*?)\1\s*$/m.exec(text);
    return match?.[2]?.replace(/\\\\/g, "\\") || null;
  } catch {
    return null;
  }
}

function readOutputFile(filePath: string): string {
  try {
    if (!fs.existsSync(filePath)) {
      return "";
    }
    const value = fs.readFileSync(filePath, "utf8").trim();
    fs.rmSync(filePath, { force: true });
    return value;
  } catch {
    return "";
  }
}

function summarizeCodexFailure(stderr: string, code: number | null): string {
  if (/Command timed out/i.test(stderr)) {
    return "execution timed out without a usable reply.";
  }
  const meaningful = stderr
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.includes("OpenAI Codex") && !line.startsWith("--------"))
    .slice(-5)
    .join("\n");
  return meaningful || `exit code ${code ?? "unknown"}`;
}

function formatCodexFailure(route: RouteResult, failure: string): string {
  const fromCoordinator = route.cleanText.includes(`机器人「${coordinator}」`) || route.cleanText.includes(`@${coordinator}`);
  return [
    fromCoordinator ? `@${coordinator}` : "",
    "代码执行官本轮没有产出有效结果。",
    "",
    `原因：Codex CLI 子进程失败：${failure}`,
    "",
    "建议：把任务拆成更小的单步执行项后重试；如果是 GUI/长耗时任务，先让我回报阶段状态，再执行下一步。"
  ]
    .filter(Boolean)
    .join("\n");
}

function preview(value: string, max: number): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > max ? `${normalized.slice(0, max)}...` : normalized;
}

function buildA2ASection(config: AppConfig): string | null {
  const bots = config.a2aBots;
  if (bots.length === 0) {
    return null;
  }
  const botListLines = bots
    .map((b) => {
      const desc = b.description ? ` - ${b.description}` : "";
      return `- @${b.name} (${b.openId})${desc}`;
    })
    .join("\n");

  return [
    "[5-Agent group workflow]",
    `You are ${developer}. Your job is local development, file edits, code implementation, and self-test reporting.`,
    "",
    "Current bots:",
    botListLines,
    "",
    "Workflow:",
    `1. The user mentions @${coordinator} with a request.`,
    `2. ${coordinator} breaks down the task and assigns one downstream agent at a time.`,
    `3. Development is handled by @${developer}. After completion, report back to @${coordinator}.`,
    `4. Ops validation is handled by @${opsValidator}. After completion, it reports back to @${coordinator}.`,
    `5. Quality audit is handled by @${auditor}. If it fails, ${coordinator} schedules rework.`,
    `6. Archival is handled by @${archivist} only after ${coordinator} requests it.`,
    "",
    "Boundaries:",
    `- Treat only @${coordinator} as the coordinator.`,
    `- @${opsValidator} is ops validation, not coordination.`,
    `- After development work, report to @${coordinator}; do not bypass it and deliver directly to the user.`,
    `- Do not split or assign tasks; that is ${coordinator}'s job.`,
    `- Do not perform ops validation; that is ${opsValidator}'s job.`,
    `- Do not audit your own work; that is ${auditor}'s job.`,
    "- Mention at most one agent per reply.",
    "",
    "A2A rules:",
    "- Cloud agents are isolated from local files. Do not ask cloud agents to read, validate, or modify local paths.",
    "- Local files, commands, logs, and runtime state must be reported by local agents.",
    `- When @${coordinator} assigns development work to you, report path, changes, run method, and self-test result back to @${coordinator}.`,
    `- If a non-coordinator agent mentions you, act only when it explicitly asks for code or file changes; otherwise say ${coordinator} should schedule the work.`,
    "- Use names without @ when merely referring to a bot.",
    "- When you need to notify another bot, write @name exactly; the sender converts it to Feishu post rich-text mention."
  ].join("\n");
}

function buildConversationSection(route: RouteResult): string {
  if (route.context?.isPrivate) {
    return [
      "[Private chat mode]",
      "You are in a one-to-one private chat with the user.",
      "Reply directly to the user. Do not mention or notify 项目调度官 unless the user explicitly asks you to draft a message for the coordinator.",
      "Do not assign work to other agents from private chat. If team coordination is needed, explain that the user should start that workflow in the group chat.",
      "Do not use @mentions in private replies unless the user explicitly asks for mention text."
    ].join("\n");
  }
  return [
    "[Group chat mode]",
    "You are in a Feishu group. Follow the configured multi-agent workflow and use @name only when another bot must be notified by the outer sender."
  ].join("\n");
}

function infoLog(message: string): void {
  if ((process.env.LOG_LEVEL || "info").toLowerCase() !== "silent") {
    console.error(`[agent] ${message}`);
  }
}
