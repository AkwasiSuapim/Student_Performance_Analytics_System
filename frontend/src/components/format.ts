export const formatNumber = (value: number, digits = 1) => value.toFixed(digits);
export const formatPercent = (value: number, digits = 1) => `${value.toFixed(digits)}%`;
export const formatBytes = (bytes: number) =>
  bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(2)} MB`;
export const formatTimestamp = (iso: string) => new Date(iso).toLocaleString();
export const PENDING = "Pending";
