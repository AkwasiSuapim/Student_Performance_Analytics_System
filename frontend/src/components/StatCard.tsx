import type { ReactNode } from "react";

export function StatCard({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return (
    <dl className="card stat" style={{ marginBottom: 0 }}>
      <dt>{label}</dt>
      <dd>
        {value}
        {note && <small>{note}</small>}
      </dd>
    </dl>
  );
}
