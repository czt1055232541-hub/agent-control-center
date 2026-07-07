import React from "react";
import { readJson } from "../api";
import type {
  SkillWorkshopSummary,
  SkillWorkshopSkill,
  SkillDriftReport,
  SkillRuntimeComparisonItem,
  SkillDriftReportItem,
  SkillBaselinePreview,
  SkillBaselineConfirmResult,
  SkillSnapshotResult,
} from "../types";

const FALLBACK_TIMEOUT_MS = 8000;
const MAX_FAILURES = 3;

async function readOptional<T>(path: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const init: RequestInit = signal ? { signal } : {};
    return await readJson<T>(path, init);
  } catch {
    return null;
  }
}

export interface SkillWorkshopState {
  summary: SkillWorkshopSummary | null;
  skills: SkillWorkshopSkill[];
  driftReport: SkillDriftReport | null;
  comparisonData: SkillRuntimeComparisonItem[];
  loading: boolean;
  error: string | null;
  backendAvailable: boolean;
  consecutiveFailures: number;
  baselinePreview: SkillBaselinePreview | null;
  writeBusy: boolean;
  writeError: string | null;
  lastWriteResult: SkillBaselineConfirmResult | SkillSnapshotResult | null;
}

export function useSkillWorkshop() {
  const [state, setState] = React.useState<SkillWorkshopState>({
    summary: null,
    skills: [],
    driftReport: null,
    comparisonData: [],
    loading: true,
    error: null,
    backendAvailable: true,
    consecutiveFailures: 0,
    baselinePreview: null,
    writeBusy: false,
    writeError: null,
    lastWriteResult: null,
  });

  const failureRef = React.useRef(0);

  const refresh = React.useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FALLBACK_TIMEOUT_MS);

    let ok = false;
    try {
      const [summary, skillsData, driftReport] = await Promise.all([
        readOptional<SkillWorkshopSummary>("/api/skill-workshop/summary", controller.signal),
        readOptional<{ skills: SkillWorkshopSkill[] }>("/api/skill-workshop/skills", controller.signal),
        readOptional<SkillDriftReport>("/api/skill-workshop/drift-report", controller.signal),
      ]);

      ok = summary !== null || skillsData !== null;

      if (ok) {
        const skills = skillsData?.skills ?? [];

        // Build comparison data: group same-named skills across runtimes
        const skillMap = new Map<string, SkillWorkshopSkill[]>();
        for (const skill of skills) {
          const key = skill.displayName;
          const existing = skillMap.get(key);
          if (existing) {
            existing.push(skill);
          } else {
            skillMap.set(key, [skill]);
          }
        }
        const comparisonData: SkillRuntimeComparisonItem[] = [];
        skillMap.forEach((instances) => {
          if (instances.length > 1) {
            const hasDrift = instances.some((s) => s.drift.status === "drift");
            comparisonData.push({
              skillId: instances[0].skillId,
              displayName: instances[0].displayName,
              instances,
              hasDrift,
              runtimeCount: instances.length,
            });
          }
        });

        failureRef.current = 0;
        setState({
          summary,
          skills,
          driftReport,
          comparisonData,
          loading: false,
          error: null,
          backendAvailable: true,
          consecutiveFailures: 0,
        });
      } else {
        throw new Error("No workshop data returned");
      }
    } catch (err) {
      failureRef.current += 1;
      const isUnavailable = failureRef.current >= MAX_FAILURES;
      setState((prev) => ({
        ...prev,
        loading: false,
        error: isUnavailable ? "后端技能工坊 API 不可用，已切换至静态技能树演示模式" : (err instanceof Error ? err.message : "获取技能工坊数据失败"),
        backendAvailable: !isUnavailable,
        consecutiveFailures: failureRef.current,
      }));
    } finally {
      clearTimeout(timeout);
    }
  }, []);

  React.useEffect(() => {
    refresh().catch(() => {});
    const timer = window.setInterval(() => {
      refresh().catch(() => {});
    }, 30000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const loadBaselinePreview = React.useCallback(async () => {
    const preview = await readJson<SkillBaselinePreview>("/api/skill-workshop/baseline/preview");
    setState((prev) => ({ ...prev, baselinePreview: preview }));
    return preview;
  }, []);

  const confirmBaseline = React.useCallback(async (token: string, confirmText: string, confirmedBy = "manual") => {
    if (!token) {
      setState((prev) => ({ ...prev, writeError: "Control token is not ready." }));
      return null;
    }
    setState((prev) => ({ ...prev, writeBusy: true, writeError: null }));
    try {
      const result = await readJson<SkillBaselineConfirmResult>("/api/skill-workshop/baseline/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: JSON.stringify({ confirmText, confirmedBy }),
      });
      setState((prev) => ({ ...prev, writeBusy: false, lastWriteResult: result }));
      await refresh();
      return result;
    } catch (err) {
      setState((prev) => ({
        ...prev,
        writeBusy: false,
        writeError: err instanceof Error ? err.message : "确认 baseline 失败",
      }));
      return null;
    }
  }, [refresh]);

  const createSnapshot = React.useCallback(async (token: string, confirmText: string, createdBy = "manual") => {
    if (!token) {
      setState((prev) => ({ ...prev, writeError: "Control token is not ready." }));
      return null;
    }
    setState((prev) => ({ ...prev, writeBusy: true, writeError: null }));
    try {
      const result = await readJson<SkillSnapshotResult>("/api/skill-workshop/snapshot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: JSON.stringify({ confirmText, createdBy }),
      });
      setState((prev) => ({ ...prev, writeBusy: false, lastWriteResult: result }));
      return result;
    } catch (err) {
      setState((prev) => ({
        ...prev,
        writeBusy: false,
        writeError: err instanceof Error ? err.message : "创建 snapshot 失败",
      }));
      return null;
    }
  }, []);

  return { ...state, refresh, loadBaselinePreview, confirmBaseline, createSnapshot };
}
