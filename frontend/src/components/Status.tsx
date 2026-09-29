import type { ApiError } from "../api/client";
import { ErrorBanner } from "./ErrorBanner";

export function LoadState({ loading, error, onRetry, label = "Loading…" }: { loading: boolean; error: ApiError | null; onRetry?: () => void; label?: string }) {
  if (error) {
    return (
      <ErrorBanner title="Could not load this view" message={error.message}>
        {onRetry && (
          <p style={{ margin: "0.5rem 0 0" }}>
            <button type="button" className="btn" onClick={onRetry}>Retry</button>
          </p>
        )}
      </ErrorBanner>
    );
  }
  return loading ? <p role="status" className="muted">{label}</p> : null;
}

export const dash = (value: number | null | undefined, digits = 1, suffix = "") =>
  value === null || value === undefined ? "—" : `${value.toFixed(digits)}${suffix}`;
