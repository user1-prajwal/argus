import type { AgentOut } from "../types/argus";
import "./DetailPanel.css";

interface AgentDetailPanelProps {
  agent: AgentOut;
  onClose: () => void;
}

const ACTIVITY_COLOR: Record<AgentOut["activity"], string> = {
  IDLE: "var(--status-idle)",
  ASSIGNED: "var(--status-assigned)",
  EXECUTING_MISSION: "var(--status-executing)",
  RETURNING: "var(--status-returning)",
  CHARGING: "var(--status-charging)",
};

const HEALTH_COLOR: Record<AgentOut["health_status"], string> = {
  ONLINE: "var(--status-online)",
  FAILED: "var(--status-failed)",
  OFFLINE: "var(--status-offline)",
};

function batteryColor(level: number): string {
  if (level <= 15) return "var(--status-failed)";
  if (level <= 40) return "var(--status-returning)";
  return "var(--status-completed)";
}

export function AgentDetailPanel({ agent, onClose }: AgentDetailPanelProps) {
  return (
    <div className="detail-panel" role="region" aria-label="Selected agent detail">
      <div className="detail-panel__header">
        <span className="detail-panel__eyebrow">Agent</span>
        <button
          className="detail-panel__close"
          onClick={onClose}
          aria-label="Close agent detail"
        >
          ×
        </button>
      </div>

      <h3 className="detail-panel__title data">{agent.id}</h3>
      <p className="detail-panel__subtitle">{agent.platform_type.replace(/_/g, " ")}</p>

      <dl className="detail-panel__fields">
        <div className="detail-panel__field">
          <dt>Position</dt>
          <dd className="data">
            ({agent.x}, {agent.y})
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Battery</dt>
          <dd>
            <div className="detail-panel__battery">
              <div className="detail-panel__battery-track">
                <div
                  className="detail-panel__battery-fill"
                  style={{
                    width: `${agent.battery_level}%`,
                    background: batteryColor(agent.battery_level),
                  }}
                />
              </div>
              <span className="data">{agent.battery_level}%</span>
            </div>
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Health</dt>
          <dd>
            <span
              className="detail-panel__pill"
              style={{ color: HEALTH_COLOR[agent.health_status] }}
            >
              {agent.health_status}
            </span>
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Activity</dt>
          <dd>
            <span
              className="detail-panel__pill"
              style={{ color: ACTIVITY_COLOR[agent.activity] }}
            >
              {agent.activity.replace(/_/g, " ")}
            </span>
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Capabilities</dt>
          <dd>
            {agent.capabilities.length > 0 ? (
              <div className="detail-panel__tags">
                {agent.capabilities.map((cap) => (
                  <span key={cap} className="detail-panel__tag">
                    {cap.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            ) : (
              <span className="detail-panel__empty">None</span>
            )}
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Current mission</dt>
          <dd className="data">
            {agent.current_mission_id ?? (
              <span className="detail-panel__empty">Unassigned</span>
            )}
          </dd>
        </div>
      </dl>
    </div>
  );
}
