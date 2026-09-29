import type { ReactNode } from "react";

export function ErrorBanner({ title, message, children }: { title: string; message: string; children?: ReactNode }) {
  return (
    <div role="alert" className="banner banner-error">
      <strong>{title}</strong>
      <p style={{ margin: "0.25rem 0 0" }}>{message}</p>
      {children}
    </div>
  );
}
