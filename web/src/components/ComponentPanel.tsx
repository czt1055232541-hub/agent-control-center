import { FolderOpen, Play, RefreshCcw, Square, Terminal } from "lucide-react";
import { isRunning } from "../api";
import type { ComponentStatus } from "../types";
import { ActionButton } from "./ActionButton";
import { StatusPill } from "./StatusPill";

export function ComponentPanel({
  component,
  title,
  disabled,
  onAction,
  onLogs,
  onOpenUi,
}: {
  component: ComponentStatus;
  title: string;
  disabled: boolean;
  onAction: (action: string) => void;
  onLogs: () => void;
  onOpenUi?: () => void;
}) {
  const running = isRunning(component);
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">
            PID {component.pid ?? "none"} {component.port ? `| Port ${component.port}` : ""}
          </p>
        </div>
        <StatusPill active={running} label={running ? "Running" : "Stopped"} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <ActionButton disabled={disabled} icon={<Play size={16} />} label="Start" onClick={() => onAction("start")} />
        <ActionButton disabled={disabled} icon={<Square size={16} />} label="Stop" onClick={() => onAction("stop")} />
        <ActionButton disabled={disabled} icon={<RefreshCcw size={16} />} label="Restart" onClick={() => onAction("restart")} />
        <ActionButton disabled={disabled} icon={<Terminal size={16} />} label="Logs" onClick={onLogs} />
        {onOpenUi ? <ActionButton disabled={disabled || !component.port} icon={<FolderOpen size={16} />} label="Open UI" onClick={onOpenUi} /> : null}
      </div>
    </section>
  );
}
