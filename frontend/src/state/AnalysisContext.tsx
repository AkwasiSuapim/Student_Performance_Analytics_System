import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, createAnalysis, loadBundle } from "../api/client";
import type { AnalysisBundle } from "../api/types";

export type Phase = "idle" | "uploading" | "loading" | "ready" | "error";

interface AnalysisState {
  phase: Phase;
  bundle: AnalysisBundle | null;
  error: ApiError | null;
  submit: (file: File) => Promise<boolean>;
  reset: () => void;
}

const STORAGE_KEY = "spa.analysisId";
const Context = createContext<AnalysisState | null>(null);

function readStoredId(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}
function writeStoredId(id: string | null) {
  try {
    if (id) sessionStorage.setItem(STORAGE_KEY, id);
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable: the dashboard simply will not survive a reload */
  }
}

const toApiError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError("unknown_error", "Something went wrong.");

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [bundle, setBundle] = useState<AnalysisBundle | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  // Restore the last analysis after a page reload.
  useEffect(() => {
    const id = readStoredId();
    if (!id) return;
    setPhase("loading");
    loadBundle(id)
      .then((restored) => {
        setBundle(restored);
        setPhase("ready");
      })
      .catch(() => {
        writeStoredId(null);
        setPhase("idle");
      });
  }, []);

  const submit = useCallback(async (file: File) => {
    setError(null);
    setPhase("uploading");
    try {
      const created = await createAnalysis(file);
      setPhase("loading");
      const loaded = await loadBundle(created.analysis_id, created);
      setBundle(loaded);
      writeStoredId(created.analysis_id);
      setPhase("ready");
      return true;
    } catch (caught) {
      setError(toApiError(caught));
      setPhase("error");
      return false;
    }
  }, []);

  const reset = useCallback(() => {
    writeStoredId(null);
    setBundle(null);
    setError(null);
    setPhase("idle");
  }, []);

  const value = useMemo(
    () => ({ phase, bundle, error, submit, reset }),
    [phase, bundle, error, submit, reset],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAnalysis(): AnalysisState {
  const value = useContext(Context);
  if (!value) throw new Error("useAnalysis must be used inside AnalysisProvider");
  return value;
}
