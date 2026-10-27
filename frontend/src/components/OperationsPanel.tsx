import type { AgentSummary, MissionSummary } from "../types/argus";
import "./OperationsPanel.css";

interface OperationsPanelProps {
  agentSummary: AgentSummary | null;
  missionSummary: MissionSummary | null;
}

function StatRow({
  label,
  value,
  colorVar,
}: {
  label: string;
  value: number;
  colorVar?: string;
}) {
  return (
    <div className="ops-panel__row">
      <span
        className="ops-panel__row-dot"
        style={colorVar ? { background: `var(${colorVar})` } : undefined}
      />
      <span className="ops-panel__row-label">{label}</span>
      <span className="ops-panel__row-value data">{value}</span>
    </div>
  );
}

export function OperationsPanel({
  agentSummary,
  missionSummary,
}: OperationsPanelProps) {
  const activity = agentSummary?.activity ?? {};
  const missionStatus = missionSummary?.status ?? {};

  return (
    <div className="ops-panel">
      <section className="ops-panel__section">
        <h2 className="ops-panel__heading">Fleet</h2>
        <div className="ops-panel__total data">{agentSummary?.total ?? 0}</div>
        <div className="ops-panel__rows">
          <StatRow
            label="Executing"
            value={activity.executing_mission ?? 0}
            colorVar="--status-executing"
          />
          <StatRow
            label="Returning"
            value={activity.returning ?? 0}
            colorVar="--status-returning"
          />
          <StatRow
            label="Idle"
            value={activity.idle ?? 0}
            colorVar="--status-idle"
          />
        </div>
      </section>

      <div className="ops-panel__divider" />

      <section className="ops-panel__section">
        <h2 className="ops-panel__heading">Missions</h2>
        <div className="ops-panel__total data">{missionSummary?.total ?? 0}</div>
        <div className="ops-panel__rows">
          <StatRow
            label="Pending"
            value={missionStatus.pending ?? 0}
            colorVar="--status-pending"
          />
          <StatRow
            label="In progress"
            value={missionStatus.in_progress ?? 0}
            colorVar="--status-in-progress"
          />
          <StatRow
            label="Completed"
            value={missionStatus.completed ?? 0}
            colorVar="--status-completed"
          />
          <StatRow
            label="Failed"
            value={missionStatus.failed ?? 0}
            colorVar="--status-failed"
          />
        </div>
      </section>
    </div>
  );
}
