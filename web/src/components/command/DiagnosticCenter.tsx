import { AlertTriangle, CheckCircle2, FileText, Play, ServerCog } from "lucide-react";
import type { ExplainedDiagnosticItem } from "../../types";
import { ActionButton } from "../ActionButton";
import { statusClasses } from "./statusStyles";

export function DiagnosticCenter({
  items,
  busy,
  onRun,
  onLogs,
}: {
  items: ExplainedDiagnosticItem[];
  busy: boolean;
  onRun: (path: string) => void;
  onLogs: (component?: string) => void;
}) {
  const visible = items.slice(0, 3);
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-slate-950">当前异常与关键诊断</h2>
        <p className="mt-1 text-sm text-slate-600">中文化原因、建议操作和相关日志入口。</p>
      </div>
      <div className="grid gap-3">
        {visible.map((item) => (
          <article key={item.id} className={`rounded-lg border p-3 ${statusClasses(item.level)}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 font-semibold text-slate-950">
                  {item.level === "normal" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
                  <span>{item.title}</span>
                </div>
                <p className="mt-1 text-sm opacity-80">{item.status}</p>
              </div>
              <span className="rounded-md bg-white/70 px-2 py-1 text-xs">{item.level}</span>
            </div>
            {item.rawError ? <p className="mt-3 rounded-md bg-white/70 p-2 text-xs text-slate-700">{item.rawError}</p> : null}
            {item.possibleCauses.length ? (
              <div className="mt-3">
                <div className="text-xs font-medium uppercase tracking-wide opacity-70">可能原因</div>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                  {item.possibleCauses.slice(0, 4).map((cause) => <li key={cause}>{cause}</li>)}
                </ul>
              </div>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {item.actions.map((action) => (
                <ActionButton
                  key={action.id}
                  disabled={busy || (!action.endpoint && !action.logComponent)}
                  danger={action.danger}
                  icon={action.endpoint ? <Play size={16} /> : action.logComponent ? <FileText size={16} /> : <ServerCog size={16} />}
                  label={action.label}
                  onClick={() => {
                    if (action.endpoint) onRun(action.endpoint);
                    else if (action.logComponent) onLogs(action.logComponent);
                  }}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
