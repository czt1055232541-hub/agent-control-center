import type { AgentStatus } from "../../types";

export function statusLabel(status: AgentStatus | string) {
  const labels: Record<string, string> = {
    running: "已启动",
    stopped: "未启动",
    warning: "部分异常",
    error: "严重异常",
    executing: "执行中",
    unknown: "未知",
    normal: "正常",
  };
  return labels[status] ?? status;
}

export function statusClasses(status: AgentStatus | string) {
  const classes: Record<string, string> = {
    running: "border-emerald-300 bg-emerald-50 text-emerald-800",
    normal: "border-emerald-300 bg-emerald-50 text-emerald-800",
    stopped: "border-stone-300 bg-stone-50 text-stone-700",
    unknown: "border-stone-300 bg-stone-50 text-stone-700",
    warning: "border-amber-300 bg-amber-50 text-amber-800",
    error: "border-red-300 bg-red-50 text-red-800",
    executing: "border-sky-300 bg-sky-50 text-sky-800",
  };
  return classes[status] ?? classes.unknown;
}

export function statusDotClasses(status: AgentStatus | string) {
  const classes: Record<string, string> = {
    running: "bg-emerald-500",
    normal: "bg-emerald-500",
    stopped: "bg-stone-400",
    unknown: "bg-stone-400",
    warning: "bg-amber-500",
    error: "bg-red-500",
    executing: "bg-sky-500",
  };
  return classes[status] ?? classes.unknown;
}
