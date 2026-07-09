import React from "react";
import { readJson } from "../api";
import type { ConfigSkillTreeResponse } from "../types";

export function useSkillTreeConfig() {
  const [data, setData] = React.useState<ConfigSkillTreeResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await readJson<ConfigSkillTreeResponse>("/api/skill-workshop/tree-config");
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "技能树配置加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  return { data, loading, error, refresh };
}
