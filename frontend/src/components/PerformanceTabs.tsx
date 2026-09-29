import { NavLink } from "react-router-dom";

/** Second-level navigation for the Performance section. */
export function PerformanceTabs() {
  return (
    <nav className="subnav" aria-label="Performance views">
      <NavLink to="/performance">Analysis</NavLink>
      <NavLink to="/students">Students</NavLink>
      <NavLink to="/classes">Classes</NavLink>
    </nav>
  );
}
