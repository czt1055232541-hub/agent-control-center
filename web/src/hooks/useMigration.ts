import React from "react";
import { readJson } from "../api";
import type { OperationResult, ThreadListItem } from "../types";

export function useMigration(token: string, refresh: () => Promise<void>) {
  const [migrationSessionId, setMigrationSessionId] = React.useState("");
  const [migrationTargetProvider, setMigrationTargetProvider] = React.useState("moonbridge");
  const [threads, setThreads] = React.useState<ThreadListItem[]>([]);
  const [confirmDesktopStop, setConfirmDesktopStop] = React.useState(false);
  const [confirmDesktopRestart, setConfirmDesktopRestart] = React.useState(false);
  const [availableMoonbridgeModels, setAvailableMoonbridgeModels] = React.useState<string[]>([]);
  const [switchingMoonbridgeModel, setSwitchingMoonbridgeModel] = React.useState(false);

  const loadThreads = React.useCallback(async () => {
    const next = await readJson<{ threads: ThreadListItem[] }>(
      "/api/thread-migration/threads?limit=20"
    );
    setThreads(Array.isArray(next.threads) ? next.threads : []);
  }, []);

  const loadMoonbridgeModels = React.useCallback(async () => {
    try {
      const data = await readJson<{ models: string[] }>("/api/moonbridge/available-models");
      setAvailableMoonbridgeModels(data.models ?? []);
    } catch {
      setAvailableMoonbridgeModels([]);
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
      setSwitchingMoonbridgeModel(true);
      try {
        const next = await readJson<OperationResult>("/api/codex-provider/moonbridge", {
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
        setSwitchingMoonbridgeModel(false);
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
    availableMoonbridgeModels,
    switchingMoonbridgeModel,
    setMigrationSessionId,
    setMigrationTargetProvider,
    setConfirmDesktopStop,
    setConfirmDesktopRestart,
    loadThreads,
    loadMoonbridgeModels,
    switchModel,
  };
}
