import { StatusPill } from "./StatusPill";

export function DiagnosticCard({
  title,
  ok,
  body,
  footer,
}: {
  title: string;
  ok: boolean;
  body: string;
  footer: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-slate-950">{title}</span>
        <StatusPill active={ok} label={ok ? "OK" : "Check"} />
      </div>
      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{body || "(no output)"}</p>
      <p className="mt-2 text-xs text-slate-500">{footer}</p>
    </div>
  );
}
