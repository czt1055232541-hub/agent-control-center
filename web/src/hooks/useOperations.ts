import React from "react";
import { readJson } from "../api";
import type { OperationRecord, OperationResult } from "../types";

export function useOperations(token: string, refresh: () => Promise<void>, enabled = true) {
  const [operations, setOperations] = React.useState<OperationRecord[]>([]);
  const [result, setResult] = React.useState<OperationResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const loadOperations = React.useCallback(async () => {
    if (!enabled) return;
    const next = await readJson<{ operations: OperationRecord[] }>("/api/operations");
    setOperations(next.operations);
  }, [enabled]);

  // Load operations on mount
  React.useEffect(() => {
    loadOperations().catch(() => {});
  }, [loadOperations]);

  async function run(path: string, after?: () => Promise<void>, body?: unknown) {
    if (!token) {
      setError("Control token is not ready.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await readJson<OperationResult>(path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      setResult(next);
      await refresh();
      // After running an operation, reload operations list
      loadOperations().catch(() => {});
      await after?.();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return { operations, loadOperations, result, error, busy, run, setError, setResult };
}
