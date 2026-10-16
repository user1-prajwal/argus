// import { useState } from "react";
// import type { ChangeEvent, FormEvent } from "react";
// import type { MissionCreate, MissionPriority } from "../types/argus";
// import "./MissionConfigurator.css";

// interface MissionConfiguratorProps {
//   missions: MissionCreate[];
//   /** The World cell most recently chosen by clicking the map in
//    * "place-mission" mode, not yet attached to a mission in the list —
//    * mirrors FleetConfigurator.tsx's pendingPosition pattern exactly. */
//   pendingPosition: { x: number; y: number } | null;
//   submitting: boolean;
//   onAddMission: (mission: MissionCreate) => void;
//   onUpdateMission: (id: string, mission: MissionCreate) => void;
//   onRemoveMission: (id: string) => void;
//   onBack: () => void;
//   onStart: () => void;
// }

// const PRIORITIES: MissionPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

// /**
//  * Mission staging: the user adds missions one at a time (name,
//  * priority, target chosen by clicking the operating-area map),
//  * reviews/edits/removes them, and only once satisfied starts the
//  * scenario. Missions are point-targets only in this phase — see
//  * project note on surveillance/area missions being a separate, later
//  * feature; this component does not draw or accept a region.
//  *
//  * There is no "assign to drone" control anywhere here by design: which
//  * drone takes which mission is PlanningEngine's decision alone, made
//  * automatically once the scenario is created and Start is pressed.
//  *
//  * Nothing is sent to the backend until onStart fires — this list is
//  * pure client-side staging, exactly like FleetConfigurator's drone
//  * list before Connect Fleet.
//  */
// export function MissionConfigurator({
//   missions,
//   pendingPosition,
//   submitting,
//   onAddMission,
//   onUpdateMission,
//   onRemoveMission,
//   onBack,
//   onStart,
// }: MissionConfiguratorProps) {
//   const [showForm, setShowForm] = useState(false);
//   const [editingId, setEditingId] = useState<string | null>(null);
//   const [name, setName] = useState("");
//   const [priority, setPriority] = useState<MissionPriority>("MEDIUM");
//   const [nameError, setNameError] = useState<string | null>(null);
//   // While editing an existing mission, its own original target is a
//   // valid position even if the user hasn't clicked the map again —
//   // only a brand new mission requires a fresh click.
//   const [editingTarget, setEditingTarget] = useState<[number, number] | null>(
//     null,
//   );

//   const nextSuggestedName = `Mission ${String(missions.length + 1).padStart(2, "0")}`;

//   const openAddForm = () => {
//     setEditingId(null);
//     setEditingTarget(null);
//     setName(nextSuggestedName);
//     setPriority("MEDIUM");
//     setNameError(null);
//     setShowForm(true);
//   };

//   const openEditForm = (mission: MissionCreate) => {
//     setEditingId(mission.id);
//     setEditingTarget(mission.target_cells[0] ?? null);
//     setName(mission.name);
//     setPriority(mission.priority);
//     setNameError(null);
//     setShowForm(true);
//   };

//   const effectiveTarget: [number, number] | null = pendingPosition
//     ? [pendingPosition.x, pendingPosition.y]
//     : editingTarget;

//   const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
//     e.preventDefault();
//     const trimmedName = name.trim();
//     if (!trimmedName) {
//       setNameError("Mission name is required.");
//       return;
//     }
//     if (!effectiveTarget) {
//       return;
//     }

//     if (editingId) {
//       const existing = missions.find((m) => m.id === editingId);
//       if (!existing) return;
//       onUpdateMission(editingId, {
//         ...existing,
//         name: trimmedName,
//         priority,
//         target_cells: [effectiveTarget],
//       });
//     } else {
//       onAddMission({
//         id: `mission-${Date.now()}-${Math.round(Math.random() * 1000)}`,
//         name: trimmedName,
//         description: `Mission target at world cell (${effectiveTarget[0]}, ${effectiveTarget[1]}).`,
//         priority,
//         target_cells: [effectiveTarget],
//         required_capabilities: [],
//       });
//     }
//     setShowForm(false);
//     setEditingId(null);
//     setEditingTarget(null);
//   };

//   return (
//     <div className="mission-config">
//       <div className="mission-config__header">
//         <h2 className="mission-config__title">Missions</h2>
//         {!showForm && (
//           <button
//             type="button"
//             className="mission-config__add-btn"
//             onClick={openAddForm}
//             disabled={submitting}
//           >
//             + Add Mission
//           </button>
//         )}
//       </div>

//       {!showForm && missions.length === 0 && (
//         <p className="mission-config__empty">No missions configured</p>
//       )}

//       {!showForm && missions.length > 0 && (
//         <ul className="mission-config__list">
//           {missions.map((mission) => (
//             <li key={mission.id} className="mission-config__item">
//               <div className="mission-config__item-header">
//                 <span className="mission-config__item-name">{mission.name}</span>
//                 <div className="mission-config__item-actions">
//                   <button
//                     type="button"
//                     className="mission-config__icon-btn"
//                     onClick={() => openEditForm(mission)}
//                     disabled={submitting}
//                     aria-label={`Edit ${mission.name}`}
//                   >
//                     Edit
//                   </button>
//                   <button
//                     type="button"
//                     className="mission-config__icon-btn mission-config__icon-btn--danger"
//                     onClick={() => onRemoveMission(mission.id)}
//                     disabled={submitting}
//                     aria-label={`Remove ${mission.name}`}
//                   >
//                     ×
//                   </button>
//                 </div>
//               </div>
//               <dl className="mission-config__item-fields">
//                 <div>
//                   <dt>Target</dt>
//                   <dd className="data">
//                     Selected on map ({mission.target_cells[0]?.[0]},{" "}
//                     {mission.target_cells[0]?.[1]})
//                   </dd>
//                 </div>
//                 <div>
//                   <dt>Priority</dt>
//                   <dd>{mission.priority}</dd>
//                 </div>
//               </dl>
//             </li>
//           ))}
//         </ul>
//       )}

//       {showForm && (
//         <form className="mission-config__form" onSubmit={handleSubmit}>
//           <label className="mission-config__field">
//             <span>Mission name</span>
//             <input
//               type="text"
//               value={name}
//               onChange={(e: ChangeEvent<HTMLInputElement>) => {
//                 setName(e.target.value);
//                 setNameError(null);
//               }}
//               placeholder="e.g. Perimeter Survey"
//               autoFocus
//               maxLength={80}
//             />
//             {nameError && (
//               <span className="mission-config__field-error">{nameError}</span>
//             )}
//           </label>

//           <label className="mission-config__field">
//             <span>Priority</span>
//             <select
//               value={priority}
//               onChange={(e: ChangeEvent<HTMLSelectElement>) =>
//                 setPriority(e.target.value as MissionPriority)
//               }
//             >
//               {PRIORITIES.map((p) => (
//                 <option key={p} value={p}>
//                   {p}
//                 </option>
//               ))}
//             </select>
//           </label>

//           <div className="mission-config__field">
//             <span>Target location</span>
//             {effectiveTarget ? (
//               <p className="mission-config__position-set data">
//                 ({effectiveTarget[0]}, {effectiveTarget[1]}) — click the map
//                 again to change
//               </p>
//             ) : (
//               <p className="mission-config__position-hint">
//                 Click the operating-area map to set this mission's target
//               </p>
//             )}
//           </div>

//           <div className="mission-config__form-actions">
//             <button
//               type="button"
//               className="mission-config__btn mission-config__btn--ghost"
//               onClick={() => {
//                 setShowForm(false);
//                 setEditingId(null);
//                 setEditingTarget(null);
//               }}
//             >
//               Cancel
//             </button>
//             <button
//               type="submit"
//               className="mission-config__btn mission-config__btn--primary"
//               disabled={!effectiveTarget || name.trim().length === 0}
//             >
//               {editingId ? "Save changes" : "Add mission"}
//             </button>
//           </div>
//         </form>
//       )}

//       {!showForm && (
//         <>
//           <div className="mission-config__divider" />
//           <div className="mission-config__actions">
//             <button
//               type="button"
//               className="mission-config__btn mission-config__btn--ghost"
//               onClick={onBack}
//               disabled={submitting}
//             >
//               Back
//             </button>
//             <button
//               type="button"
//               className="mission-config__btn mission-config__btn--primary"
//               onClick={onStart}
//               disabled={submitting}
//             >
//               {submitting
//                 ? "Starting…"
//                 : missions.length === 0
//                   ? "Start (0 missions)"
//                   : `Start (${missions.length} mission${missions.length === 1 ? "" : "s"})`}
//             </button>
//           </div>
//           <p className="mission-config__note">
//             PlanningEngine automatically decides which drone takes each
//             mission once the scenario starts — there is no manual
//             drone-to-mission assignment here.
//           </p>
//         </>
//       )}
//     </div>
//   );
// }





import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { MissionCreate, MissionPriority } from "../types/argus";
import "./MissionConfigurator.css";

/**
 * A single click sets a point target (target_cells has exactly one
 * cell, unchanged from before this feature). Two clicks -- opposite
 * corners of a small rectangle -- set an area-watch target
 * (target_cells has every cell inside that rectangle). Both are the
 * SAME Mission.target_cells field on the existing backend model (see
 * app/mission/mission.py's target_cells: frozenset[tuple[int,int]],
 * already unbounded in size) -- "watch" vs "point" is a frontend
 * presentation distinction only, inferred from how many cells the
 * mission actually has. There is no new backend field.
 *
 * SimulationEngine is unmodified: for either target type, the
 * assigned drone routes to whichever cell of target_cells is nearest
 * (see app/simulation/engine.py's _nearest_target_cell) and completes
 * the mission on arrival there -- an area-watch mission is "fly to
 * this zone," not a patrol, loiter, or multi-cell sweep. The UI must
 * not claim otherwise; see the area-mode note rendered in the form
 * below.
 */
type TargetMode = "point" | "area";

/** Cap on one side of a selected watch rectangle, in cells. A UI/UX
 * guard only -- keeps a "watch area" small and deliberate rather than
 * a second large operating-area-sized region, and keeps target_cells
 * small (at most AREA_MAX_SIDE^2 cells) for a trivially fast linear
 * scan in the existing, unmodified _nearest_target_cell. Not a
 * backend-enforced limit -- app/mission/mission.py's target_cells has
 * no size cap of its own. */
const AREA_MAX_SIDE = 6;

interface MissionConfiguratorProps {
  missions: MissionCreate[];
  /** The World cell most recently chosen by a single map click in
   * "point" mode, not yet attached to a mission in the list — mirrors
   * FleetConfigurator.tsx's pendingPosition pattern exactly. */
  pendingPosition: { x: number; y: number } | null;
  /** The two opposite corners chosen so far for an in-progress
   * area-watch selection, in "area" mode. Populated incrementally:
   * one corner after the first map click, both after the second. */
  pendingAreaCorners: [{ x: number; y: number }, { x: number; y: number } | null] | null;
  submitting: boolean;
  onAddMission: (mission: MissionCreate) => void;
  onUpdateMission: (id: string, mission: MissionCreate) => void;
  onRemoveMission: (id: string) => void;
  onBack: () => void;
  onStart: () => void;
  /** Called when the user switches between point/area target mode, so
   * App.tsx can reset in-progress corner-click state cleanly rather
   * than mixing a half-finished area selection with a point click or
   * vice versa. */
  onTargetModeChange: (mode: TargetMode) => void;
  targetMode: TargetMode;
}

const PRIORITIES: MissionPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function cellsInRectangle(
  a: { x: number; y: number },
  b: { x: number; y: number },
): [number, number][] {
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);
  const cells: [number, number][] = [];
  for (let x = minX; x <= maxX; x++) {
    for (let y = minY; y <= maxY; y++) {
      cells.push([x, y]);
    }
  }
  return cells;
}

/** Clamps a second corner so the rectangle it forms with the first
 * never exceeds AREA_MAX_SIDE cells on either side -- enforces the
 * documented limit (see AREA_MAX_SIDE above) rather than merely
 * stating it in the UI copy. Clamping (not rejecting) keeps the
 * interaction forgiving: a click past the limit still produces the
 * largest valid rectangle in that direction instead of silently doing
 * nothing. */
function clampSecondCorner(
  first: { x: number; y: number },
  second: { x: number; y: number },
): { x: number; y: number } {
  const maxSide = AREA_MAX_SIDE - 1; // inclusive cell span, e.g. 6 cells wide = offset of 5
  const clampAxis = (a: number, b: number): number => {
    if (b > a) return Math.min(b, a + maxSide);
    if (b < a) return Math.max(b, a - maxSide);
    return b;
  };
  return { x: clampAxis(first.x, second.x), y: clampAxis(first.y, second.y) };
}

/**
 * Mission staging: the user adds missions one at a time (name,
 * priority, target chosen by clicking the operating-area map),
 * reviews/edits/removes them, and only once satisfied starts the
 * scenario. A mission's target is either a single point or a small
 * rectangular watch area (see TargetMode above) — both are the same
 * underlying target_cells field.
 *
 * There is no "assign to drone" control anywhere here by design: which
 * drone takes which mission is PlanningEngine's decision alone, made
 * automatically once the scenario is created and Start is pressed.
 *
 * Nothing is sent to the backend until onStart fires — this list is
 * pure client-side staging, exactly like FleetConfigurator's drone
 * list before Connect Fleet.
 */
export function MissionConfigurator({
  missions,
  pendingPosition,
  pendingAreaCorners,
  submitting,
  onAddMission,
  onUpdateMission,
  onRemoveMission,
  onBack,
  onStart,
  onTargetModeChange,
  targetMode,
}: MissionConfiguratorProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [priority, setPriority] = useState<MissionPriority>("MEDIUM");
  const [nameError, setNameError] = useState<string | null>(null);
  // While editing an existing mission, its own original target is a
  // valid selection even if the user hasn't clicked the map again --
  // only a brand new mission requires a fresh click. Holds either a
  // single cell (point) or the full cell list (area) being edited.
  const [editingTargetCells, setEditingTargetCells] = useState<
    [number, number][] | null
  >(null);

  const nextSuggestedName = `Mission ${String(missions.length + 1).padStart(2, "0")}`;

  const openAddForm = () => {
    setEditingId(null);
    setEditingTargetCells(null);
    setName(nextSuggestedName);
    setPriority("MEDIUM");
    setNameError(null);
    setShowForm(true);
  };

  const openEditForm = (mission: MissionCreate) => {
    setEditingId(mission.id);
    setEditingTargetCells(mission.target_cells);
    onTargetModeChange(mission.target_cells.length > 1 ? "area" : "point");
    setName(mission.name);
    setPriority(mission.priority);
    setNameError(null);
    setShowForm(true);
  };

  const areaSelectionComplete =
    pendingAreaCorners !== null && pendingAreaCorners[1] !== null;

  const effectiveTargetCells: [number, number][] | null =
    targetMode === "point"
      ? pendingPosition
        ? [[pendingPosition.x, pendingPosition.y]]
        : editingTargetCells && editingTargetCells.length === 1
          ? editingTargetCells
          : null
      : areaSelectionComplete && pendingAreaCorners
        ? cellsInRectangle(pendingAreaCorners[0], pendingAreaCorners[1] as { x: number; y: number })
        : editingTargetCells && editingTargetCells.length > 1
          ? editingTargetCells
          : null;

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError("Mission name is required.");
      return;
    }
    if (!effectiveTargetCells || effectiveTargetCells.length === 0) {
      return;
    }

    if (editingId) {
      const existing = missions.find((m) => m.id === editingId);
      if (!existing) return;
      onUpdateMission(editingId, {
        ...existing,
        name: trimmedName,
        priority,
        target_cells: effectiveTargetCells,
      });
    } else {
      const isArea = effectiveTargetCells.length > 1;
      onAddMission({
        id: `mission-${Date.now()}-${Math.round(Math.random() * 1000)}`,
        name: trimmedName,
        description: isArea
          ? `Watch area of ${effectiveTargetCells.length} world cells; the assigned drone routes to the nearest cell in this zone and completes on arrival.`
          : `Mission target at world cell (${effectiveTargetCells[0][0]}, ${effectiveTargetCells[0][1]}).`,
        priority,
        target_cells: effectiveTargetCells,
        required_capabilities: [],
      });
    }
    setShowForm(false);
    setEditingId(null);
    setEditingTargetCells(null);
  };

  const targetSummary = (cells: [number, number][]) => {
    if (cells.length <= 1) {
      const [x, y] = cells[0] ?? [0, 0];
      return `(${x}, ${y})`;
    }
    const xs = cells.map((c) => c[0]);
    const ys = cells.map((c) => c[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    return `${cells.length} cells, (${minX},${minY})–(${maxX},${maxY})`;
  };

  return (
    <div className="mission-config">
      <div className="mission-config__header">
        <h2 className="mission-config__title">Missions</h2>
        {!showForm && (
          <button
            type="button"
            className="mission-config__add-btn"
            onClick={openAddForm}
            disabled={submitting}
          >
            + Add Mission
          </button>
        )}
      </div>

      {!showForm && missions.length === 0 && (
        <p className="mission-config__empty">No missions configured</p>
      )}

      {!showForm && missions.length > 0 && (
        <ul className="mission-config__list">
          {missions.map((mission) => (
            <li key={mission.id} className="mission-config__item">
              <div className="mission-config__item-header">
                <span className="mission-config__item-name">{mission.name}</span>
                <div className="mission-config__item-actions">
                  <button
                    type="button"
                    className="mission-config__icon-btn"
                    onClick={() => openEditForm(mission)}
                    disabled={submitting}
                    aria-label={`Edit ${mission.name}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="mission-config__icon-btn mission-config__icon-btn--danger"
                    onClick={() => onRemoveMission(mission.id)}
                    disabled={submitting}
                    aria-label={`Remove ${mission.name}`}
                  >
                    ×
                  </button>
                </div>
              </div>
              <dl className="mission-config__item-fields">
                <div>
                  <dt>{mission.target_cells.length > 1 ? "Watch area" : "Target"}</dt>
                  <dd className="data">{targetSummary(mission.target_cells)}</dd>
                </div>
                <div>
                  <dt>Priority</dt>
                  <dd>{mission.priority}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      {showForm && (
        <form className="mission-config__form" onSubmit={handleSubmit}>
          <label className="mission-config__field">
            <span>Mission name</span>
            <input
              type="text"
              value={name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                setName(e.target.value);
                setNameError(null);
              }}
              placeholder="e.g. Perimeter Survey"
              autoFocus
              maxLength={80}
            />
            {nameError && (
              <span className="mission-config__field-error">{nameError}</span>
            )}
          </label>

          <label className="mission-config__field">
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

          <div className="mission-config__field">
            <span>Target type</span>
            <div className="mission-config__mode-toggle" role="radiogroup">
              <button
                type="button"
                className={
                  targetMode === "point"
                    ? "mission-config__mode-btn mission-config__mode-btn--active"
                    : "mission-config__mode-btn"
                }
                onClick={() => onTargetModeChange("point")}
                aria-pressed={targetMode === "point"}
              >
                Point
              </button>
              <button
                type="button"
                className={
                  targetMode === "area"
                    ? "mission-config__mode-btn mission-config__mode-btn--active"
                    : "mission-config__mode-btn"
                }
                onClick={() => onTargetModeChange("area")}
                aria-pressed={targetMode === "area"}
              >
                Watch area
              </button>
            </div>
          </div>

          <div className="mission-config__field">
            <span>{targetMode === "area" ? "Watch area" : "Target location"}</span>
            {targetMode === "point" ? (
              effectiveTargetCells ? (
                <p className="mission-config__position-set data">
                  {targetSummary(effectiveTargetCells)} — click the map again to
                  change
                </p>
              ) : (
                <p className="mission-config__position-hint">
                  Click the operating-area map to set this mission's target
                </p>
              )
            ) : effectiveTargetCells ? (
              <p className="mission-config__position-set data">
                {targetSummary(effectiveTargetCells)} — click the map again to
                redraw
              </p>
            ) : pendingAreaCorners ? (
              <p className="mission-config__position-hint">
                Click the opposite corner to complete the watch area
              </p>
            ) : (
              <p className="mission-config__position-hint">
                Click one corner of the watch area on the map, then the
                opposite corner (max {AREA_MAX_SIDE}×{AREA_MAX_SIDE} cells)
              </p>
            )}
          </div>

          {targetMode === "area" && (
            <p className="mission-config__note">
              The assigned drone routes to the nearest cell inside this
              area and completes the mission on arrival — this is not a
              continuous patrol or hover; the simulation's movement and
              completion behavior is unchanged.
            </p>
          )}

          <div className="mission-config__form-actions">
            <button
              type="button"
              className="mission-config__btn mission-config__btn--ghost"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
                setEditingTargetCells(null);
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="mission-config__btn mission-config__btn--primary"
              disabled={
                !effectiveTargetCells ||
                effectiveTargetCells.length === 0 ||
                name.trim().length === 0
              }
            >
              {editingId ? "Save changes" : "Add mission"}
            </button>
          </div>
        </form>
      )}

      {!showForm && (
        <>
          <div className="mission-config__divider" />
          <div className="mission-config__actions">
            <button
              type="button"
              className="mission-config__btn mission-config__btn--ghost"
              onClick={onBack}
              disabled={submitting}
            >
              Back
            </button>
            <button
              type="button"
              className="mission-config__btn mission-config__btn--primary"
              onClick={onStart}
              disabled={submitting}
            >
              {submitting
                ? "Starting…"
                : missions.length === 0
                  ? "Start (0 missions)"
                  : `Start (${missions.length} mission${missions.length === 1 ? "" : "s"})`}
            </button>
          </div>
          <p className="mission-config__note">
            PlanningEngine automatically decides which drone takes each
            mission once the scenario starts — there is no manual
            drone-to-mission assignment here.
          </p>
        </>
      )}
    </div>
  );
}

export type { TargetMode };
export { AREA_MAX_SIDE, cellsInRectangle, clampSecondCorner };
