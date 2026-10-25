import type { MissionOut } from "../types/argus";
import "./DetailPanel.css";

interface MissionDetailPanelProps {
  mission: MissionOut;
  onClose: () => void;
}

const STATUS_COLOR: Record<MissionOut["status"], string> = {
  PENDING: "var(--status-pending)",
  ASSIGNED: "var(--status-assigned)",
  IN_PROGRESS: "var(--status-in-progress)",
  COMPLETED: "var(--status-completed)",
  FAILED: "var(--status-failed)",
  CANCELLED: "var(--status-cancelled)",
};

const PRIORITY_COLOR: Record<MissionOut["priority"], string> = {
  LOW: "var(--priority-low)",
  MEDIUM: "var(--priority-medium)",
  HIGH: "var(--priority-high)",
  CRITICAL: "var(--priority-critical)",
};

export function MissionDetailPanel({ mission, onClose }: MissionDetailPanelProps) {
  return (
    <div className="detail-panel" role="region" aria-label="Selected mission detail">
      <div className="detail-panel__header">
        <span className="detail-panel__eyebrow">Mission</span>
        <button
          className="detail-panel__close"
          onClick={onClose}
          aria-label="Close mission detail"
        >
          ×
        </button>
      </div>

      <h3 className="detail-panel__title">{mission.name}</h3>
      <p className="detail-panel__subtitle data">{mission.id}</p>

      <dl className="detail-panel__fields">
        <div className="detail-panel__field">
          <dt>Priority</dt>
          <dd>
            <span
              className="detail-panel__pill"
              style={{ color: PRIORITY_COLOR[mission.priority] }}
            >
              {mission.priority}
            </span>
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Status</dt>
          <dd>
            <span
              className="detail-panel__pill"
              style={{ color: STATUS_COLOR[mission.status] }}
            >
              {mission.status.replace(/_/g, " ")}
            </span>
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Target{mission.target_cells.length > 1 ? "s" : ""}</dt>
          <dd className="data">
            {mission.target_cells.map(([x, y]) => `(${x}, ${y})`).join(", ")}
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Required capabilities</dt>
          <dd>
            {mission.required_capabilities.length > 0 ? (
              <div className="detail-panel__tags">
                {mission.required_capabilities.map((cap) => (
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
          <dt>Assigned agent{mission.assigned_agent_ids.length > 1 ? "s" : ""}</dt>
          <dd className="data">
            {mission.assigned_agent_ids.length > 0 ? (
              mission.assigned_agent_ids.join(", ")
            ) : (
              <span className="detail-panel__empty">Unassigned</span>
            )}
          </dd>
        </div>

        <div className="detail-panel__field">
          <dt>Description</dt>
          <dd className="detail-panel__description">{mission.description}</dd>
        </div>
      </dl>
    </div>
  );
}
