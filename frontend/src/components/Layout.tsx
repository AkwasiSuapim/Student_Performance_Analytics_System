import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Upload Data", end: true },
  { to: "/overview", label: "Overview" },
  { to: "/performance", label: "Performance", group: ["/performance", "/students", "/classes"] },
  { to: "/support", label: "Support Analysis" },
  { to: "/alerts", label: "Alerts" },
  { to: "/predictions", label: "Predictions & Reports" },
];

export function Layout() {
  const { pathname } = useLocation();
  return (
    <>
      <a className="skip-link" href="#main">Skip to main content</a>
      <header className="app-header">
        <div className="app-header-inner">
          <p className="brand">Student Performance Analytics</p>
          <nav className="nav" aria-label="Main sections">
            {LINKS.map((link) =>
              link.group ? (
                // A section that spans several routes: active on any of them.
                <Link
                  key={link.to}
                  to={link.to}
                  aria-current={link.group.some((p) => pathname.startsWith(p)) ? "page" : undefined}
                >
                  {link.label}
                </Link>
              ) : (
                <NavLink key={link.to} to={link.to} end={link.end}>
                  {link.label}
                </NavLink>
              ),
            )}
          </nav>
        </div>
      </header>
      <main id="main" className="page">
        <Outlet />
      </main>
    </>
  );
}
