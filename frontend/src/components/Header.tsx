import type { ScenarioPhase } from "../types/argus";
import "./Header.css";

interface HeaderProps {
  phase: ScenarioPhase | null;
  tick: number | null;
  connected: boolean;
}

const PHASE_LABEL: Record<ScenarioPhase, string> = {
  not_started: "STANDBY",
  in_progress: "ACTIVE",
  settled: "SETTLED",
};

export function Header({ phase, tick, connected }: HeaderProps) {
  const statusLabel = !connected
    ? "OFFLINE"
    : phase
      ? PHASE_LABEL[phase]
      : "INITIALIZING";

  const statusClass = !connected
    ? "offline"
    : phase === "in_progress"
      ? "active"
      : phase === "settled"
        ? "settled"
        : "standby";

  return (
    <header className="argus-header">
      <div className="argus-header__brand">
        <div className="argus-header__mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="argus-header__titles">
          <h1 className="argus-header__name">ARGUS</h1>
          <p className="argus-header__subtitle">
            Autonomous Multi-Agent Coordination System
          </p>
        </div>
      </div>

      <div className="argus-header__telemetry">
        <div className="argus-header__stat">
          <span className="argus-header__stat-label">Tick</span>
          <span className="argus-header__stat-value data">
            {tick !== null ? String(tick).padStart(4, "0") : "----"}
          </span>
        </div>
        <div className={`argus-header__status argus-header__status--${statusClass}`}>
          <span className="argus-header__status-dot" aria-hidden="true" />
          <span className="argus-header__status-label">{statusLabel}</span>
        </div>
      </div>
    </header>
  );
}
