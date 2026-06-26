import { CheckCircle2, XCircle } from "lucide-react";

export function StatusPill({ active, label }: { active: boolean; label: string }) {
  const Icon = active ? CheckCircle2 : XCircle;
  return (
    <div
      className={`inline-flex h-8 items-center gap-2 rounded-md border px-3 text-sm ${
        active
          ? "border-emerald-300 bg-emerald-50 text-emerald-800"
          : "border-stone-300 bg-stone-50 text-stone-700"
      }`}
    >
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
