import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { AgentCreate, Capability } from "../types/argus";
import "./FleetConfigurator.css";

interface FleetConfiguratorProps {
  drones: AgentCreate[];
  /** The World cell most recently chosen by clicking the map in
   * "place-drone" mode, not yet attached to a drone in the list — the
   * Add Drone form binds to this rather than owning its own map-click
   * state, mirroring how MissionDraftPanel.tsx consumes App.tsx's
   * draftTargetCell. */
  pendingPosition: { x: number; y: number } | null;
  connecting: boolean;
  onAddDrone: (drone: AgentCreate) => void;
  onRemoveDrone: (id: string) => void;
  onConnectFleet: () => void;
  onCancel: () => void;
}

const CAPABILITIES: Capability[] = [
  "thermal_camera",
  "standard_camera",
  "lidar",
  "gps",
];

/**
 * Fleet registration: the user adds drones one at a time (id,
 * capability, position chosen by clicking the operating-area map),
 * reviews the list, and only once satisfied clicks Connect Fleet to
 * actually create them as backend agents (POST /scenarios/geo's
 * `agents`). Nothing is created automatically — an empty list is a
 * valid, expected state ("No drones connected"), not an error, and
 * Connect Fleet with zero drones configured produces a scenario with
 * zero agents (see backend/app/geo/scenario_builder.py's "FLEET IS
 * USER-CONFIGURED, NEVER AUTO-GENERATED").
 *
 * "Ready" status below describes a drone's registration state in this
 * simulated fleet, not a claim about physical hardware — see this
 * component's note about simulation-only Version 1 scope.
 */
export function FleetConfigurator({
  drones,
  pendingPosition,
  connecting,
  onAddDrone,
  onRemoveDrone,
  onConnectFleet,
  onCancel,
}: FleetConfiguratorProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [droneId, setDroneId] = useState("");
  const [capability, setCapability] = useState<Capability | "">("");
  const [idError, setIdError] = useState<string | null>(null);

  const nextSuggestedId = `DRONE-${String(drones.length + 1).padStart(2, "0")}`;

  const openAddForm = () => {
    setDroneId(nextSuggestedId);
    setCapability("");
    setIdError(null);
    setShowAddForm(true);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmedId = droneId.trim();
    if (!trimmedId) {
      setIdError("Drone ID is required.");
      return;
    }
    if (drones.some((d) => d.id === trimmedId)) {
      setIdError("This ID is already used by another drone in this fleet.");
      return;
    }
    if (!pendingPosition) {
      return;
    }

    onAddDrone({
      id: trimmedId,
      platform_type: "DRONE",
      x: pendingPosition.x,
      y: pendingPosition.y,
      battery_level: 100,
      capabilities: capability ? [capability] : [],
    });
    setShowAddForm(false);
  };

  return (
    <div className="fleet-config">
      <div className="fleet-config__header">
        <h2 className="fleet-config__title">Drone Fleet</h2>
        {!showAddForm && (
          <button
            type="button"
            className="fleet-config__add-btn"
            onClick={openAddForm}
            disabled={connecting}
          >
            + Add Drone
          </button>
        )}
      </div>

      {!showAddForm && drones.length === 0 && (
        <p className="fleet-config__empty">No drones connected</p>
      )}

      {!showAddForm && drones.length > 0 && (
        <ul className="fleet-config__list">
          {drones.map((drone) => (
            <li key={drone.id} className="fleet-config__item">
              <div className="fleet-config__item-header">
                <span className="fleet-config__item-id data">{drone.id}</span>
                <button
                  type="button"
                  className="fleet-config__remove-btn"
                  onClick={() => onRemoveDrone(drone.id)}
                  disabled={connecting}
                  aria-label={`Remove ${drone.id}`}
                >
                  ×
                </button>
              </div>
              <dl className="fleet-config__item-fields">
                <div>
                  <dt>Capability</dt>
                  <dd>
                    {drone.capabilities && drone.capabilities.length > 0
                      ? drone.capabilities.map((c) => c.replace(/_/g, " ")).join(", ")
                      : "None"}
                  </dd>
                </div>
                <div>
                  <dt>Initial position</dt>
                  <dd className="data">
                    Selected on map ({drone.x}, {drone.y})
                  </dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <span className="fleet-config__status-pill">Ready</span>
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      {showAddForm && (
        <form className="fleet-config__form" onSubmit={handleSubmit}>
          <label className="fleet-config__field">
            <span>Drone ID</span>
            <input
              type="text"
              value={droneId}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                setDroneId(e.target.value);
                setIdError(null);
              }}
              placeholder="DRONE-01"
              autoFocus
              maxLength={40}
            />
            {idError && <span className="fleet-config__field-error">{idError}</span>}
          </label>

          <label className="fleet-config__field">
            <span>Capability</span>
            <select
              value={capability}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setCapability(e.target.value as Capability | "")
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

          <div className="fleet-config__field">
            <span>Initial position</span>
            {pendingPosition ? (
              <p className="fleet-config__position-set data">
                ({pendingPosition.x}, {pendingPosition.y}) — click the map
                again to change
              </p>
            ) : (
              <p className="fleet-config__position-hint">
                Click the operating-area map to set this drone's starting
                position
              </p>
            )}
          </div>

          <div className="fleet-config__form-actions">
            <button
              type="button"
              className="fleet-config__btn fleet-config__btn--ghost"
              onClick={() => setShowAddForm(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="fleet-config__btn fleet-config__btn--primary"
              disabled={!pendingPosition || droneId.trim().length === 0}
            >
              Add to fleet
            </button>
          </div>
        </form>
      )}

      {!showAddForm && (
        <>
          <div className="fleet-config__divider" />
          <div className="fleet-config__actions">
            <button
              type="button"
              className="fleet-config__btn fleet-config__btn--ghost"
              onClick={onCancel}
              disabled={connecting}
            >
              Back
            </button>
            <button
              type="button"
              className="fleet-config__btn fleet-config__btn--primary"
              onClick={onConnectFleet}
              disabled={connecting}
            >
              {connecting
                ? "Connecting…"
                : drones.length === 0
                  ? "Connect Fleet (0 drones)"
                  : `Connect Fleet (${drones.length})`}
            </button>
          </div>
          <p className="fleet-config__note">
            Drones are simulated agents in this version — registering
            here does not connect to physical hardware. PlanningEngine
            decides which drone is assigned to each mission once the
            fleet is connected and a mission exists; drones are not
            manually assigned here.
          </p>
        </>
      )}
    </div>
  );
}
