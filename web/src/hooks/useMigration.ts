import React from "react";
import { readJson } from "../api";
import type { OperationResult, ThreadListItem } from "../types";

export function useMigration(token: string, refresh: () => Promise<void>) {
  const [migrationSessionId, setMigrationSessionId] = React.useState("");
  const [migrationTargetProvider, setMigrationTargetProvider] = React.useState("deepseek");
  const [threads, setThreads] = React.useState<ThreadListItem[]>([]);
  const [confirmDesktopStop, setConfirmDesktopStop] = React.useState(false);
  const [confirmDesktopRestart, setConfirmDesktopRestart] = React.useState(false);
  const [availableDeepSeekModels, setAvailableDeepSeekModels] = React.useState<string[]>([]);
  const [switchingDeepSeekModel, setSwitchingDeepSeekModel] = React.useState(false);

  const loadThreads = React.useCallback(async () => {
    const next = await readJson<{ threads: ThreadListItem[] }>(
      "/api/thread-migration/threads?limit=20"
    );
    setThreads(Array.isArray(next.threads) ? next.threads : []);
  }, []);

  const loadDeepSeekModels = React.useCallback(async () => {
    try {
      const data = await readJson<{ models: string[] }>("/api/deepseek/available-models");
      setAvailableDeepSeekModels(data.models ?? []);
    } catch {
      setAvailableDeepSeekModels([]);
    }
  }, []);

  const switchModel = React.useCallback(
    async (
      model: string,
      reasoningEffort: string,
      setError: (msg: string) => void,
      setResult: React.Dispatch<React.SetStateAction<OperationResult | null>>,
    ) => {
      if (!token) {
        setError("Control token is not ready.");
        return;
      }
      setSwitchingDeepSeekModel(true);
      try {
        const next = await readJson<OperationResult>("/api/codex-provider/deepseek", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Control-Token": token,
          },
          body: JSON.stringify({ model, reasoning_effort: reasoningEffort }),
        });
        setResult(next);
        await refresh();
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : String(exc));
      } finally {
        setSwitchingDeepSeekModel(false);
      }
    },
    [token, refresh],
  );

  return {
    migrationSessionId,
    migrationTargetProvider,
    threads,
    confirmDesktopStop,
    confirmDesktopRestart,
    availableDeepSeekModels,
    switchingDeepSeekModel,
    setMigrationSessionId,
    setMigrationTargetProvider,
    setConfirmDesktopStop,
    setConfirmDesktopRestart,
    loadThreads,
    loadDeepSeekModels,
    switchModel,
  };
}
