import { AlertTriangle, Bot, CheckCircle2, GripVertical, MessageSquare, Radio, ServerCog, Zap } from "lucide-react";
import React from "react";
import type { DashboardSummary } from "../../types";
import { statusClasses, statusLabel } from "../../components/common/statusStyles";
import { SortableGrid, type SortableGridItem } from "../../components/common/SortableGrid";

const CARD_ORDER_STORAGE_KEY = "acc.dashboard.summaryCardOrder";

type SummaryCardConfig = {
  id: string;
  title: string;
  value: string;
  detail?: string;
  icon: React.ReactNode;
  tone?: string;
};

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
    <div className={`h-full rounded-lg border bg-white p-4 shadow-sm ${statusClasses(tone)}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{title}</span>
        <span className="flex items-center gap-2">
          {icon}
          <GripVertical aria-hidden="true" className="text-current opacity-40" size={16} />
        </span>
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-950">{value}</div>
      {detail ? <div className="mt-1 text-xs opacity-80">{detail}</div> : null}
    </div>
  );
}

export function SummaryCards({ summary }: { summary: DashboardSummary | null }) {
  const health = summary?.systemHealth ?? "unknown";
  const cards = React.useMemo<SummaryCardConfig[]>(() => [
    {
      id: "health",
      title: "系统健康",
      value: statusLabel(health),
      detail: "全局状态",
      icon: health === "normal" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />,
      tone: health,
    },
    {
      id: "provider",
      title: "当前 Provider",
      value: summary?.provider ?? "--",
      icon: <ServerCog size={18} />,
      tone: "executing",
    },
    {
      id: "feishu",
      title: "飞书连接",
      value: summary?.feishuStatus === "unknown" ? "--" : statusLabel(summary?.feishuStatus ?? "unknown"),
      icon: <Radio size={18} />,
    },
    {
      id: "agents",
      title: "在线 Agent",
      value: `${summary?.onlineAgents ?? "--"} / ${summary?.totalAgents ?? "--"}`,
      icon: <Bot size={18} />,
      tone: "running",
    },
    {
      id: "tasks",
      title: "活跃任务",
      value: summary?.activeTasks?.toString() ?? "--",
      icon: <Zap size={18} />,
      tone: "executing",
    },
    {
      id: "messages",
      title: "今日消息",
      value: summary?.todayMessages?.toString() ?? "--",
      icon: <MessageSquare size={18} />,
    },
    {
      id: "failures",
      title: "失败请求",
      value: summary?.failedRequests?.toString() ?? "--",
      icon: <AlertTriangle size={18} />,
      tone: (summary?.failedRequests ?? 0) > 0 ? "warning" : "normal",
    },
  ], [health, summary]);
  const items = React.useMemo<SortableGridItem[]>(() => cards.map((card) => ({
    id: card.id,
    node: <Card {...card} />,
  })), [cards]);

  return (
    <SortableGrid
      ariaLabel="Dashboard summary cards"
      className="grid gap-3 md:grid-cols-2 xl:grid-cols-7"
      items={items}
      storageKey={CARD_ORDER_STORAGE_KEY}
    />
  );
}
