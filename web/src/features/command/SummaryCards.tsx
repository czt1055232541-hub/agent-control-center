import { AlertTriangle, Bot, CheckCircle2, MessageSquare, Radio, ServerCog, Zap } from "lucide-react";
import type React from "react";
import type { DashboardSummary } from "../../types";
import { statusClasses, statusLabel } from "./statusStyles";

function Card({
  title,
  value,
  detail,
  icon,
  tone = "unknown",
}: {
  title: string;
  value: string;
  detail?: string;
  icon: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className={`rounded-lg border bg-white p-4 shadow-sm ${statusClasses(tone)}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{title}</span>
        {icon}
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-950">{value}</div>
      {detail ? <div className="mt-1 text-xs opacity-80">{detail}</div> : null}
    </div>
  );
}

export function SummaryCards({ summary }: { summary: DashboardSummary | null }) {
  const health = summary?.systemHealth ?? "unknown";
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
      <Card
        title="系统健康"
        value={statusLabel(health)}
        detail="全局状态"
        icon={health === "normal" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
        tone={health}
      />
      <Card title="当前 Provider" value={summary?.provider ?? "--"} icon={<ServerCog size={18} />} tone="executing" />
      <Card title="飞书连接" value={summary?.feishuStatus === "unknown" ? "--" : statusLabel(summary?.feishuStatus ?? "unknown")} icon={<Radio size={18} />} />
      <Card title="在线 Agent" value={`${summary?.onlineAgents ?? "--"} / ${summary?.totalAgents ?? "--"}`} icon={<Bot size={18} />} tone="running" />
      <Card title="活跃任务" value={summary?.activeTasks?.toString() ?? "--"} icon={<Zap size={18} />} tone="executing" />
      <Card title="今日消息" value={summary?.todayMessages?.toString() ?? "--"} icon={<MessageSquare size={18} />} />
      <Card title="失败请求" value={summary?.failedRequests?.toString() ?? "--"} icon={<AlertTriangle size={18} />} tone={(summary?.failedRequests ?? 0) > 0 ? "warning" : "normal"} />
    </section>
  );
}
