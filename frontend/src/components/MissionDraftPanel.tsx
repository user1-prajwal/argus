import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { Capability, MissionCreate, MissionPriority } from "../types/argus";
import "./DetailPanel.css";
import "./MissionDraftPanel.css";

interface MissionDraftPanelProps {
  targetCell: { x: number; y: number };
  onCancel: () => void;
  onSubmit: (mission: MissionCreate) => void;
  submitting: boolean;
}

const PRIORITIES: MissionPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const CAPABILITIES: Capability[] = [
  "thermal_camera",
  "standard_camera",
  "lidar",
  "gps",
];

/**
 * The panel shown after a map click stages a candidate mission target
 * (see GeoMap.tsx's onMapClick and App.tsx's draftTargetCell state).
 * Submitting here does not call a live "add mission" endpoint — none
 * exists (see useScenario.ts's addMissionAndRecreate doc comment) — it
 * recreates the session with this mission included. That tradeoff is
 * stated plainly in the panel copy rather than left implicit.
 */
export function MissionDraftPanel({
  targetCell,
  onCancel,
  onSubmit,
  submitting,
}: MissionDraftPanelProps) {
  const [name, setName] = useState("");
  const [priority, setPriority] = useState<MissionPriority>("MEDIUM");
  const [requiredCapability, setRequiredCapability] = useState<Capability | "">("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;

    const mission: MissionCreate = {
      id: `mission-${targetCell.x}-${targetCell.y}-${Date.now()}`,
      name: trimmed,
      description: `Mission target placed on the map at world cell (${targetCell.x}, ${targetCell.y}).`,
      priority,
      target_cells: [[targetCell.x, targetCell.y]],
      required_capabilities: requiredCapability ? [requiredCapability] : [],
    };
    onSubmit(mission);
  };

  return (
    <div className="detail-panel" role="region" aria-label="New mission target">
      <div className="detail-panel__header">
        <span className="detail-panel__eyebrow">New mission target</span>
        <button
          className="detail-panel__close"
          onClick={onCancel}
          aria-label="Cancel mission placement"
        >
          ×
        </button>
      </div>

      <p className="mission-draft__coords data">
        World cell ({targetCell.x}, {targetCell.y})
      </p>

      <form className="mission-draft__form" onSubmit={handleSubmit}>
        <label className="mission-draft__field">
          <span>Name</span>
          <input
            type="text"
            value={name}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
            placeholder="e.g. Perimeter Survey"
            autoFocus
            maxLength={80}
          />
        </label>

        <label className="mission-draft__field">
          <span>Priority</span>
          <select
            value={priority}
            onChange={(e: ChangeEvent<HTMLSelectElement>) =>
              setPriority(e.target.value as MissionPriority)
            }
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>

        <label className="mission-draft__field">
          <span>Required capability</span>
          <select
            value={requiredCapability}
            onChange={(e: ChangeEvent<HTMLSelectElement>) =>
              setRequiredCapability(e.target.value as Capability | "")
            }
          >
            <option value="">None</option>
            {CAPABILITIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </label>

        <p className="mission-draft__note">
          Creating this mission regenerates the World from the same
          operating area (same real building data) with this mission
          included — there is no live endpoint to add a mission to an
          in-progress session, so any other tick progress is reset.
        </p>

        <div className="mission-draft__actions">
          <button
            type="button"
            className="mission-draft__btn mission-draft__btn--ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="mission-draft__btn mission-draft__btn--primary"
            disabled={submitting || name.trim().length === 0}
          >
            {submitting ? "Creating…" : "Create mission"}
          </button>
        </div>
      </form>
    </div>
  );
}
