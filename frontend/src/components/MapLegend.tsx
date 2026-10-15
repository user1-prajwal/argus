import "./MapLegend.css";

const ACTIVITY_ENTRIES: { label: string; color: string }[] = [
  { label: "Executing", color: "var(--status-executing)" },
  { label: "Returning", color: "var(--status-returning)" },
  { label: "Assigned", color: "var(--status-assigned)" },
  { label: "Idle", color: "var(--status-idle)" },
];

export function MapLegend() {
  return (
    <div className="map-legend" aria-hidden="true">
      <div className="map-legend__group">
        <span className="map-legend__swatch map-legend__swatch--agent" />
        <span className="map-legend__text">Drone</span>
      </div>
      <div className="map-legend__group">
        <span className="map-legend__swatch map-legend__swatch--diamond" />
        <span className="map-legend__text">Mission target</span>
      </div>
      <div className="map-legend__group">
        <span className="map-legend__swatch map-legend__swatch--waypoint">1</span>
        <span className="map-legend__text">Coverage waypoint</span>
      </div>
      <div className="map-legend__group">
        <span className="map-legend__swatch map-legend__swatch--route-traveled" />
        <span className="map-legend__text">Route (traveled)</span>
      </div>
      <div className="map-legend__group">
        <span className="map-legend__swatch map-legend__swatch--route-remaining" />
        <span className="map-legend__text">Route (ahead)</span>
      </div>
      <div className="map-legend__divider" />
      {ACTIVITY_ENTRIES.map((entry) => (
        <div className="map-legend__group" key={entry.label}>
          <span
            className="map-legend__swatch map-legend__swatch--dot"
            style={{ background: entry.color }}
          />
          <span className="map-legend__text">{entry.label}</span>
        </div>
      ))}
    </div>
  );
}
