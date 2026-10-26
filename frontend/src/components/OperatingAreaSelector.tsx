import type { GeoBounds, LatLng } from "../geo/coordinates";
import "./OperatingAreaSelector.css";

interface OperatingAreaSelectorProps {
  /** The first corner click, if any — passed up from GeoMap's
   * onAreaCornerClick so this panel can show progress ("1 of 2
   * corners placed") without owning the map's click wiring itself. */
  firstCorner: LatLng | null;
  draftArea: GeoBounds | null;
  onConfirm: () => void;
  onClear: () => void;
}

const WORLD_WIDTH = 40;
const WORLD_HEIGHT = 40;

/**
 * The panel guiding operating-area selection: click two opposite
 * corners on the map to define a rectangle, then confirm to move on
 * to fleet configuration (App.tsx's "configure-fleet" stage). This is
 * the very first interaction a user has with ARGUS — there is no
 * default/fake scenario shown before this. Confirming here does NOT
 * yet create anything on the backend — the real World (and its real
 * OpenStreetMap building data, via POST /scenarios/geo) is only
 * generated once the user has also configured a fleet and clicked
 * Connect Fleet (see FleetConfigurator.tsx).
 */
export function OperatingAreaSelector({
  firstCorner,
  draftArea,
  onConfirm,
  onClear,
}: OperatingAreaSelectorProps) {
  const step = draftArea ? "confirm" : firstCorner ? "second-corner" : "first-corner";

  return (
    <div className="area-selector">
      <h2 className="area-selector__title">Select an operating area</h2>
      <p className="area-selector__body">
        ARGUS builds its World from real OpenStreetMap building data for
        whatever area you choose. Click two opposite corners on the map
        to define a small operating rectangle inside Bengaluru.
      </p>

      <ol className="area-selector__steps">
        <li className={step !== "first-corner" ? "area-selector__step--done" : ""}>
          Click the first corner
        </li>
        <li
          className={
            step === "confirm"
              ? "area-selector__step--done"
              : step === "second-corner"
                ? "area-selector__step--active"
                : ""
          }
        >
          Click the opposite corner
        </li>
        <li className={step === "confirm" ? "area-selector__step--active" : ""}>
          Confirm, then configure your fleet
        </li>
      </ol>

      {draftArea && (
        <div className="area-selector__summary data">
          <div>
            SW ({draftArea.south.toFixed(4)}, {draftArea.west.toFixed(4)})
          </div>
          <div>
            NE ({draftArea.north.toFixed(4)}, {draftArea.east.toFixed(4)})
          </div>
        </div>
      )}

      <div className="area-selector__actions">
        <button
          type="button"
          className="area-selector__btn area-selector__btn--ghost"
          onClick={onClear}
          disabled={!firstCorner && !draftArea}
        >
          Clear
        </button>
        <button
          type="button"
          className="area-selector__btn area-selector__btn--primary"
          onClick={onConfirm}
          disabled={!draftArea}
        >
          Confirm area
        </button>
      </div>

      <p className="area-selector__note">
        World grid: {WORLD_WIDTH}×{WORLD_HEIGHT} cells. After confirming,
        you'll register a fleet of drones before ARGUS queries the
        public Overpass API for real building footprints inside the
        chosen rectangle — buildings that intersect a cell become
        obstacles for simulated agents (a simulation assumption, not a
        claim that every real building blocks every real flight
        altitude).
      </p>
    </div>
  );
}
