// import { useEffect, useRef } from "react";
// import L from "leaflet";
// import "leaflet/dist/leaflet.css";
// import {
//   BENGALURU_CENTER,
//   BENGALURU_DEFAULT_ZOOM,
//   boundsToLeafletCorners,
//   geoToWorld,
//   worldToGeo,
// } from "../geo/coordinates";
// import type { GeoBounds } from "../geo/coordinates";
// import { platformGlyphSvg } from "../geo/platformGlyphs";
// import type { AgentOut, AgentRouteResponse, MissionOut } from "../types/argus";
// import "./GeoMap.css";

// interface GeoMapProps {
//   /**
//    * The scenario's actual World bounds/dimensions, as echoed back by
//    * the backend (GET /scenarios/{id}'s geo_bounds, or
//    * POST /scenarios/geo's own response) — null before any scenario
//    * exists yet, in which case this map has nothing to draw and is
//    * showing only the base Bengaluru view for area selection instead.
//    * There is no fixed/fallback bounds this component could use on its
//    * own; every conversion below takes these as explicit parameters,
//    * mirroring geo/coordinates.ts's own parameterized design.
//    */
//   bounds: GeoBounds | null;
//   worldWidth: number | null;
//   worldHeight: number | null;
//   agents: AgentOut[];
//   missions: MissionOut[];
//   /** Real backend routes per agent id — see useScenario.ts's refresh()
//    * and the active-route API endpoint. Never computed client-side. */
//   routes: Map<string, AgentRouteResponse>;
//   selectedAgentId: string | null;
//   selectedMissionId: string | null;
//   onSelectAgent: (id: string) => void;
//   onSelectMission: (id: string) => void;
//   /**
//    * "select-area": clicking the map places/updates the two corners of
//    *   a candidate operating-area rectangle (see
//    *   OperatingAreaSelector.tsx, which owns the two-click state this
//    *   mode reports through onAreaCornerClick).
//    * "place-drone": clicking the map sets a candidate drone's starting
//    *   World cell, converted against the CONFIRMED draft operating
//    *   area (the `draftArea` prop) rather than the (still-null)
//    *   session `bounds` — no session/scenario exists yet at this
//    *   stage, so there is nothing else to convert against. See
//    *   FleetConfigurator.tsx.
//    * "place-mission": clicking the map sets a candidate mission's
//    *   target World cell, converted against the same draft operating
//    *   area as "place-drone" — missions, like drones, are staged
//    *   entirely before the scenario is created (see
//    *   MissionConfigurator.tsx and the project's "submit all
//    *   configured missions together" requirement). There is no
//    *   separate post-session mission-placement mode; every mission
//    *   target is chosen before POST /scenarios/geo ever fires.
//    */
//   mode: "select-area" | "place-drone" | "place-mission";
//   onAreaCornerClick?: (latLng: { lat: number; lng: number }) => void;
//   onMapClick?: (cell: { x: number; y: number }) => void;
//   /** The confirmed operating-area rectangle, used as the conversion
//    * bounds for "place-drone" and "place-mission" clicks (no
//    * session/backend-echoed bounds exist yet at those stages — see
//    * `mode`'s own doc comment above). Also drawn as a highlighted
//    * overlay while mode is "select-area". */
//   draftArea?: GeoBounds | null;
//   /** World dimensions to convert against while mode is "place-drone"
//    * or "place-mission" (no session/backend-echoed dimensions exist
//    * yet at those stages). Ignored in "select-area". */
//   draftWorldWidth?: number;
//   draftWorldHeight?: number;
//   /** World cell of a not-yet-submitted mission draft, if any, shown as
//    * a distinct pending marker so the user can see what they clicked
//    * before deciding to include it. */
//   draftTargetCell: { x: number; y: number } | null;
//   /** Configured drones not yet connected to the backend (fleet
//    * configuration stage — see FleetConfigurator.tsx), shown as
//    * distinct pending markers at their chosen World cells, converted
//    * against draftArea/draftWorldWidth/draftWorldHeight the same way a
//    * mission draft is converted against the live session's bounds. */
//   draftDrones?: { id: string; x: number; y: number }[];
//   /** Configured missions not yet submitted to the backend (mission
//    * staging stage — see MissionConfigurator.tsx), shown as distinct
//    * pending diamond markers at their chosen World cells, converted
//    * against draftArea/draftWorldWidth/draftWorldHeight the same way
//    * draftDrones is. */
//   draftMissions?: { id: string; name: string; x: number; y: number }[];
// }

// const ACTIVITY_COLOR: Record<AgentOut["activity"], string> = {
//   IDLE: "--status-idle",
//   ASSIGNED: "--status-assigned",
//   EXECUTING_MISSION: "--status-executing",
//   RETURNING: "--status-returning",
//   CHARGING: "--status-charging",
// };

// const PRIORITY_COLOR: Record<MissionOut["priority"], string> = {
//   LOW: "--priority-low",
//   MEDIUM: "--priority-medium",
//   HIGH: "--priority-high",
//   CRITICAL: "--priority-critical",
// };

// function resolveToken(token: string): string {
//   if (typeof window === "undefined") return token;
//   const value = getComputedStyle(document.documentElement)
//     .getPropertyValue(token)
//     .trim();
//   return value || token;
// }

// function agentDivIcon(agent: AgentOut, isSelected: boolean): L.DivIcon {
//   const color = resolveToken(ACTIVITY_COLOR[agent.activity]);
//   const glyph = platformGlyphSvg(agent.platform_type);
//   return L.divIcon({
//     className: `geo-map__agent-icon${isSelected ? " geo-map__agent-icon--selected" : ""}`,
//     html: `
//       <div class="geo-map__agent-icon-inner" style="color: ${color};">
//         ${isSelected ? '<span class="geo-map__agent-ring"></span>' : ""}
//         <span class="geo-map__agent-glyph">${glyph}</span>
//         ${agent.health_status !== "ONLINE" ? '<span class="geo-map__agent-flag">!</span>' : ""}
//       </div>
//     `,
//     iconSize: [30, 30],
//     iconAnchor: [15, 15],
//   });
// }

// function missionDivIcon(mission: MissionOut, isSelected: boolean): L.DivIcon {
//   const color = resolveToken(PRIORITY_COLOR[mission.priority]);
//   return L.divIcon({
//     className: `geo-map__mission-icon${isSelected ? " geo-map__mission-icon--selected" : ""}`,
//     html: `
//       <div class="geo-map__mission-icon-inner" style="--marker-color: ${color};">
//         ${isSelected ? '<span class="geo-map__mission-ring"></span>' : ""}
//         <span class="geo-map__mission-diamond"></span>
//       </div>
//     `,
//     iconSize: [26, 26],
//     iconAnchor: [13, 13],
//   });
// }

// function draftDivIcon(): L.DivIcon {
//   return L.divIcon({
//     className: "geo-map__draft-icon",
//     html: `<div class="geo-map__draft-icon-inner"><span class="geo-map__draft-diamond"></span></div>`,
//     iconSize: [26, 26],
//     iconAnchor: [13, 13],
//   });
// }

// /**
//  * Primary map view: real OpenStreetMap tiles via Leaflet, with agents,
//  * mission targets, and real backend routes drawn at their geographic
//  * position (see geo/coordinates.ts for the World <-> geo mapping this
//  * all rests on). Replaces the SVG grid (WorldMap.tsx, still present
//  * but no longer the primary view) as ARGUS's dominant visual surface.
//  *
//  * Before a scenario exists (bounds === null), this same map is reused
//  * for operating-area selection (mode="select-area") — there is no
//  * separate "picker" map component, so the user's very first
//  * interaction with ARGUS is the same real Bengaluru map they will see
//  * agents move on afterward.
//  *
//  * Built on Leaflet's own imperative API directly (map/marker/polyline
//  * objects held in refs), not a React wrapper library — Leaflet manages
//  * its own DOM subtree internally, so this component's job is only to
//  * keep that subtree in sync with props on every render, via a small
//  * diff pass in each effect below.
//  */
// export function GeoMap({
//   bounds,
//   worldWidth,
//   worldHeight,
//   agents,
//   missions,
//   routes,
//   selectedAgentId,
//   selectedMissionId,
//   onSelectAgent,
//   onSelectMission,
//   mode,
//   onAreaCornerClick,
//   onMapClick,
//   draftArea,
//   draftWorldWidth,
//   draftWorldHeight,
//   draftTargetCell,
//   draftDrones,
//   draftMissions,
// }: GeoMapProps) {
//   const containerRef = useRef<HTMLDivElement>(null);
//   const mapRef = useRef<L.Map | null>(null);
//   const agentMarkersRef = useRef<Map<string, L.Marker>>(new Map());
//   const missionMarkersRef = useRef<Map<string, L.Marker>>(new Map());
//   const routeLayersRef = useRef<Map<string, L.Polyline[]>>(new Map());
//   const draftMarkerRef = useRef<L.Marker | null>(null);
//   const draftAreaLayerRef = useRef<L.Rectangle | null>(null);
//   const draftDroneMarkersRef = useRef<Map<string, L.Marker>>(new Map());
//   const draftMissionMarkersRef = useRef<Map<string, L.Marker>>(new Map());
//   const hasFitBoundsRef = useRef(false);

//   const modeRef = useRef(mode);
//   modeRef.current = mode;
//   const draftAreaRef = useRef(draftArea);
//   draftAreaRef.current = draftArea;
//   const draftWorldWidthRef = useRef(draftWorldWidth);
//   draftWorldWidthRef.current = draftWorldWidth;
//   const draftWorldHeightRef = useRef(draftWorldHeight);
//   draftWorldHeightRef.current = draftWorldHeight;
//   const onAreaCornerClickRef = useRef(onAreaCornerClick);
//   onAreaCornerClickRef.current = onAreaCornerClick;
//   const onMapClickRef = useRef(onMapClick);
//   onMapClickRef.current = onMapClick;
//   const onSelectAgentRef = useRef(onSelectAgent);
//   onSelectAgentRef.current = onSelectAgent;
//   const onSelectMissionRef = useRef(onSelectMission);
//   onSelectMissionRef.current = onSelectMission;

//   // Map initialization — runs once. Starts centered on Bengaluru
//   // (no scenario exists yet at mount time); re-centers onto the
//   // scenario's real bounds once one is created, in the effect below.
//   useEffect(() => {
//     if (!containerRef.current || mapRef.current) return;

//     const map = L.map(containerRef.current, {
//       zoomControl: true,
//       attributionControl: true,
//     }).setView([BENGALURU_CENTER.lat, BENGALURU_CENTER.lng], BENGALURU_DEFAULT_ZOOM);

//     L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
//       maxZoom: 19,
//       attribution: "&copy; OpenStreetMap contributors",
//     }).addTo(map);

//     map.on("click", (e: L.LeafletMouseEvent) => {
//       if (modeRef.current === "select-area") {
//         onAreaCornerClickRef.current?.({ lat: e.latlng.lat, lng: e.latlng.lng });
//         return;
//       }
//       if (modeRef.current === "place-drone" || modeRef.current === "place-mission") {
//         const areaBounds = draftAreaRef.current;
//         const areaWidth = draftWorldWidthRef.current;
//         const areaHeight = draftWorldHeightRef.current;
//         if (!areaBounds || !areaWidth || !areaHeight) return;
//         const cell = geoToWorld(e.latlng.lat, e.latlng.lng, areaBounds, areaWidth, areaHeight);
//         onMapClickRef.current?.(cell);
//         return;
//       }
//     });

//     mapRef.current = map;

//     return () => {
//       map.remove();
//       mapRef.current = null;
//     };
//   }, []);

//   // Re-center/fit the map onto the scenario's real bounds the first
//   // time they become available. Does not re-fit on every render
//   // afterward — once the user has panned or zoomed, further state
//   // refreshes should not yank the view back.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map || !bounds || hasFitBoundsRef.current) return;
//     map.fitBounds(boundsToLeafletCorners(bounds));
//     hasFitBoundsRef.current = true;
//   }, [bounds]);

//   // Draft operating-area rectangle, shown while selecting an area.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map) return;

//     if (draftAreaLayerRef.current) {
//       draftAreaLayerRef.current.remove();
//       draftAreaLayerRef.current = null;
//     }

//     if (draftArea) {
//       draftAreaLayerRef.current = L.rectangle(boundsToLeafletCorners(draftArea), {
//         className: "geo-map__draft-area",
//       }).addTo(map);
//     }
//   }, [draftArea]);

//   // Agents — add/update/remove markers to match the current agent
//   // list every render. Position, icon, and popup content all come
//   // directly from the AgentOut the backend returned this tick.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map || !bounds || !worldWidth || !worldHeight) return;
//     const markers = agentMarkersRef.current;
//     const seen = new Set<string>();

//     for (const agent of agents) {
//       seen.add(agent.id);
//       const { lat, lng } = worldToGeo(agent.x, agent.y, bounds, worldWidth, worldHeight);
//       const isSelected = selectedAgentId === agent.id;
//       const icon = agentDivIcon(agent, isSelected);

//       let marker = markers.get(agent.id);
//       if (!marker) {
//         marker = L.marker([lat, lng], { icon, keyboard: true });
//         marker.on("click", () => onSelectAgentRef.current(agent.id));
//         marker.addTo(map);
//         markers.set(agent.id, marker);
//       } else {
//         marker.setLatLng([lat, lng]);
//         marker.setIcon(icon);
//       }
//       marker.bindTooltip(
//         `${agent.id} — ${agent.platform_type.replace(/_/g, " ")} — ${agent.activity.replace(/_/g, " ")} — ${agent.battery_level}%`,
//         { direction: "top", offset: [0, -16] },
//       );
//     }

//     for (const [id, marker] of markers) {
//       if (!seen.has(id)) {
//         marker.remove();
//         markers.delete(id);
//       }
//     }
//   }, [agents, selectedAgentId, bounds, worldWidth, worldHeight]);

//   // Missions — same add/update/remove pattern as agents.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map || !bounds || !worldWidth || !worldHeight) return;
//     const markers = missionMarkersRef.current;
//     const seen = new Set<string>();

//     for (const mission of missions) {
//       if (mission.target_cells.length === 0) continue;
//       seen.add(mission.id);
//       const [tx, ty] = mission.target_cells[0];
//       const { lat, lng } = worldToGeo(tx, ty, bounds, worldWidth, worldHeight);
//       const isSelected = selectedMissionId === mission.id;
//       const icon = missionDivIcon(mission, isSelected);

//       let marker = markers.get(mission.id);
//       if (!marker) {
//         marker = L.marker([lat, lng], { icon, keyboard: true });
//         marker.on("click", () => onSelectMissionRef.current(mission.id));
//         marker.addTo(map);
//         markers.set(mission.id, marker);
//       } else {
//         marker.setLatLng([lat, lng]);
//         marker.setIcon(icon);
//       }
//       marker.bindTooltip(
//         `${mission.name} — ${mission.priority} — ${mission.status.replace(/_/g, " ")}`,
//         { direction: "top", offset: [0, -14] },
//       );
//     }

//     for (const [id, marker] of markers) {
//       if (!seen.has(id)) {
//         marker.remove();
//         markers.delete(id);
//       }
//     }
//   }, [missions, selectedMissionId, bounds, worldWidth, worldHeight]);

//   // Routes — real backend route per agent, split into traveled/ahead
//   // segments exactly as WorldMap.tsx does, redrawn from scratch each
//   // time since route length/progress changes tick to tick.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map || !bounds || !worldWidth || !worldHeight) return;
//     const layers = routeLayersRef.current;

//     for (const existing of layers.values()) {
//       for (const line of existing) line.remove();
//     }
//     layers.clear();

//     for (const agent of agents) {
//       const route = routes.get(agent.id);
//       if (!route || route.cells.length < 2) continue;

//       const currentIndex = route.cells.findIndex(
//         ([cx, cy]) => cx === agent.x && cy === agent.y,
//       );
//       const splitAt = currentIndex === -1 ? 0 : currentIndex;
//       const traveled = route.cells.slice(0, splitAt + 1);
//       const remaining = route.cells.slice(splitAt);
//       const isSelected =
//         selectedAgentId === agent.id ||
//         (selectedMissionId !== null && selectedMissionId === agent.current_mission_id);

//       const toLatLngs = (cells: [number, number][]) =>
//         cells.map(([cx, cy]) => {
//           const { lat, lng } = worldToGeo(cx, cy, bounds, worldWidth, worldHeight);
//           return [lat, lng] as [number, number];
//         });

//       const created: L.Polyline[] = [];
//       if (traveled.length >= 2) {
//         created.push(
//           L.polyline(toLatLngs(traveled), {
//             className: isSelected
//               ? "geo-map__route-traveled geo-map__route-traveled--selected"
//               : "geo-map__route-traveled",
//             weight: isSelected ? 4 : 3,
//           }).addTo(map),
//         );
//       }
//       if (remaining.length >= 2) {
//         created.push(
//           L.polyline(toLatLngs(remaining), {
//             className: isSelected
//               ? "geo-map__route geo-map__route--selected"
//               : "geo-map__route",
//             weight: isSelected ? 3 : 2,
//             dashArray: "4 6",
//           }).addTo(map),
//         );
//       }
//       layers.set(agent.id, created);
//     }
//   }, [agents, routes, selectedAgentId, selectedMissionId, bounds, worldWidth, worldHeight]);

//   // Draft mission target — the pending, not-yet-submitted click.
//   useEffect(() => {
//     const map = mapRef.current;
//     if (!map || !bounds || !worldWidth || !worldHeight) return;

//     if (draftMarkerRef.current) {
//       draftMarkerRef.current.remove();
//       draftMarkerRef.current = null;
//     }

//     if (draftTargetCell) {
//       const { lat, lng } = worldToGeo(
//         draftTargetCell.x,
//         draftTargetCell.y,
//         bounds,
//         worldWidth,
//         worldHeight,
//       );
//       draftMarkerRef.current = L.marker([lat, lng], {
//         icon: draftDivIcon(),
//         keyboard: false,
//       }).addTo(map);
//     }
//   }, [draftTargetCell, bounds, worldWidth, worldHeight]);

//   // Configured-but-not-yet-connected drones (fleet configuration
//   // stage) — converted against the DRAFT operating area, since no
//   // session/backend-echoed bounds exist until Connect Fleet actually
//   // creates one. Uses the same drone glyph a connected agent uses
//   // (dimmed via CSS), so a drone looks the same before and after
//   // connection rather than switching visual language.
//   useEffect(() => {
//     const map = mapRef.current;
//     const markers = draftDroneMarkersRef.current;
//     if (!map || !draftArea || !draftWorldWidth || !draftWorldHeight || !draftDrones) {
//       for (const marker of markers.values()) marker.remove();
//       markers.clear();
//       return;
//     }

//     const seen = new Set<string>();
//     for (const drone of draftDrones) {
//       seen.add(drone.id);
//       const { lat, lng } = worldToGeo(
//         drone.x,
//         drone.y,
//         draftArea,
//         draftWorldWidth,
//         draftWorldHeight,
//       );
//       const icon = L.divIcon({
//         className: "geo-map__draft-drone-icon",
//         html: `
//           <div class="geo-map__draft-drone-icon-inner">
//             <span class="geo-map__draft-drone-glyph">${platformGlyphSvg("DRONE")}</span>
//           </div>
//         `,
//         iconSize: [30, 30],
//         iconAnchor: [15, 15],
//       });

//       let marker = markers.get(drone.id);
//       if (!marker) {
//         marker = L.marker([lat, lng], { icon, keyboard: false });
//         marker.addTo(map);
//         markers.set(drone.id, marker);
//       } else {
//         marker.setLatLng([lat, lng]);
//         marker.setIcon(icon);
//       }
//       marker.bindTooltip(drone.id, { direction: "top", offset: [0, -16] });
//     }

//     for (const [id, marker] of markers) {
//       if (!seen.has(id)) {
//         marker.remove();
//         markers.delete(id);
//       }
//     }
//   }, [draftDrones, draftArea, draftWorldWidth, draftWorldHeight]);

//   // Configured-but-not-yet-submitted missions (mission staging stage)
//   // — same pattern as draft drones: converted against the DRAFT
//   // operating area, using the same diamond glyph a connected mission
//   // target uses (dashed/dimmed via CSS) so a mission looks the same
//   // before and after the scenario is actually created.
//   useEffect(() => {
//     const map = mapRef.current;
//     const markers = draftMissionMarkersRef.current;
//     if (!map || !draftArea || !draftWorldWidth || !draftWorldHeight || !draftMissions) {
//       for (const marker of markers.values()) marker.remove();
//       markers.clear();
//       return;
//     }

//     const seen = new Set<string>();
//     for (const mission of draftMissions) {
//       seen.add(mission.id);
//       const { lat, lng } = worldToGeo(
//         mission.x,
//         mission.y,
//         draftArea,
//         draftWorldWidth,
//         draftWorldHeight,
//       );
//       const icon = draftDivIcon();

//       let marker = markers.get(mission.id);
//       if (!marker) {
//         marker = L.marker([lat, lng], { icon, keyboard: false });
//         marker.addTo(map);
//         markers.set(mission.id, marker);
//       } else {
//         marker.setLatLng([lat, lng]);
//         marker.setIcon(icon);
//       }
//       marker.bindTooltip(mission.name, { direction: "top", offset: [0, -14] });
//     }

//     for (const [id, marker] of markers) {
//       if (!seen.has(id)) {
//         marker.remove();
//         markers.delete(id);
//       }
//     }
//   }, [draftMissions, draftArea, draftWorldWidth, draftWorldHeight]);

//   return (
//     <div className="geo-map">
//       <div ref={containerRef} className="geo-map__container" />
//     </div>
//   );
// }


import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  BENGALURU_CENTER,
  BENGALURU_DEFAULT_ZOOM,
  boundsToLeafletCorners,
  geoToWorld,
  worldToGeo,
} from "../geo/coordinates";
import type { GeoBounds } from "../geo/coordinates";
import { platformGlyphSvg } from "../geo/platformGlyphs";
import type { AgentOut, AgentRouteResponse, MissionOut } from "../types/argus";
import "./GeoMap.css";

interface GeoMapProps {
  bounds: GeoBounds | null;
  worldWidth: number | null;
  worldHeight: number | null;
  agents: AgentOut[];
  missions: MissionOut[];
  routes: Map<string, AgentRouteResponse>;
  selectedAgentId: string | null;
  selectedMissionId: string | null;
  onSelectAgent: (id: string) => void;
  onSelectMission: (id: string) => void;
  mode: "select-area" | "place-drone" | "place-mission";
  onAreaCornerClick?: (latLng: { lat: number; lng: number }) => void;
  onMapClick?: (cell: { x: number; y: number }) => void;
  draftArea?: GeoBounds | null;
  draftWorldWidth?: number;
  draftWorldHeight?: number;
  draftTargetCell: { x: number; y: number } | null;
  draftDrones?: { id: string; x: number; y: number }[];
  /** Configured missions not yet submitted to the backend (mission
   * staging stage — see MissionConfigurator.tsx), shown as distinct
   * pending diamond markers at their chosen World cells. POINT
   * missions only -- area-watch mission drafts are handled separately
   * by draftMissionAreas below. */
  draftMissions?: { id: string; name: string; x: number; y: number }[];
  /** Configured area-watch missions not yet submitted, each as its
   * full set of target World cells (see MissionConfigurator.tsx's
   * cellsInRectangle) — rendered as a highlighted rectangle overlay,
   * the same visual language as the operating-area draft rectangle,
   * so a "watch area" reads as a real zone rather than a marker. */
  draftMissionAreas?: { id: string; name: string; cells: [number, number][] }[];
  /** The in-progress watch-area corner selection while creating or
   * editing an area-watch mission: the first clicked corner, and the
   * second once chosen (still null while only one corner is set).
   * Drawn as a live preview rectangle the same way draftArea is drawn
   * during operating-area selection. */
  pendingMissionAreaCorners?: [
    { x: number; y: number },
    { x: number; y: number } | null,
  ] | null;
}

const ACTIVITY_COLOR: Record<AgentOut["activity"], string> = {
  IDLE: "--status-idle",
  ASSIGNED: "--status-assigned",
  EXECUTING_MISSION: "--status-executing",
  RETURNING: "--status-returning",
  CHARGING: "--status-charging",
};

const PRIORITY_COLOR: Record<MissionOut["priority"], string> = {
  LOW: "--priority-low",
  MEDIUM: "--priority-medium",
  HIGH: "--priority-high",
  CRITICAL: "--priority-critical",
};

function resolveToken(token: string): string {
  if (typeof window === "undefined") return token;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim();
  return value || token;
}

function agentDivIcon(agent: AgentOut, isSelected: boolean): L.DivIcon {
  const color = resolveToken(ACTIVITY_COLOR[agent.activity]);
  const glyph = platformGlyphSvg(agent.platform_type);
  return L.divIcon({
    className: `geo-map__agent-icon${isSelected ? " geo-map__agent-icon--selected" : ""}`,
    html: `
      <div class="geo-map__agent-icon-inner" style="color: ${color};">
        ${isSelected ? '<span class="geo-map__agent-ring"></span>' : ""}
        <span class="geo-map__agent-glyph">${glyph}</span>
        ${agent.health_status !== "ONLINE" ? '<span class="geo-map__agent-flag">!</span>' : ""}
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function missionDivIcon(mission: MissionOut, isSelected: boolean): L.DivIcon {
  const color = resolveToken(PRIORITY_COLOR[mission.priority]);
  return L.divIcon({
    className: `geo-map__mission-icon${isSelected ? " geo-map__mission-icon--selected" : ""}`,
    html: `
      <div class="geo-map__mission-icon-inner" style="--marker-color: ${color};">
        ${isSelected ? '<span class="geo-map__mission-ring"></span>' : ""}
        <span class="geo-map__mission-diamond"></span>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

/** One of an Area Watch mission's ~4 coverage waypoints (see
 * mission.coverage_waypoints), numbered in visiting order. `status`
 * reflects the assigned agent's real backend progress
 * (AgentRouteResponse.current_waypoint) -- "upcoming" when no agent is
 * yet executing this mission's coverage route. */
function waypointDivIcon(order: number, status: "visited" | "current" | "upcoming"): L.DivIcon {
  return L.divIcon({
    className: `geo-map__waypoint-icon geo-map__waypoint-icon--${status}`,
    html: `<div class="geo-map__waypoint-icon-inner">${order}</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function draftDivIcon(): L.DivIcon {
  return L.divIcon({
    className: "geo-map__draft-icon",
    html: `<div class="geo-map__draft-icon-inner"><span class="geo-map__draft-diamond"></span></div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

/** Bounding rectangle (in geo coords) of a set of target World cells,
 * expanded by half a cell on each side so the drawn rectangle visibly
 * contains the full cells, not just their center points. */
function cellsToGeoBounds(
  cells: [number, number][],
  worldBounds: GeoBounds,
  worldWidth: number,
  worldHeight: number,
): GeoBounds {
  const xs = cells.map((c) => c[0]);
  const ys = cells.map((c) => c[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const sw = worldToGeo(minX, minY, worldBounds, worldWidth, worldHeight);
  const ne = worldToGeo(maxX, maxY, worldBounds, worldWidth, worldHeight);
  const cellWidthDeg = (worldBounds.east - worldBounds.west) / worldWidth;
  const cellHeightDeg = (worldBounds.north - worldBounds.south) / worldHeight;

  return {
    south: sw.lat - cellHeightDeg / 2,
    west: sw.lng - cellWidthDeg / 2,
    north: ne.lat + cellHeightDeg / 2,
    east: ne.lng + cellWidthDeg / 2,
  };
}

/**
 * Primary map view: real OpenStreetMap tiles via Leaflet, with agents,
 * mission targets, and real backend routes drawn at their geographic
 * position. Before a scenario exists (bounds === null), this same map
 * is reused for operating-area selection (mode="select-area"). The
 * same rectangle-drawing approach is reused for area-watch mission
 * targets (see draftMissionAreas, pendingMissionAreaCorners, and each
 * live mission's own multi-cell target_cells) so a watch zone reads
 * as a real zone, not a marker.
 *
 * Built on Leaflet's own imperative API directly (map/marker/polyline
 * objects held in refs), not a React wrapper library.
 */
export function GeoMap({
  bounds,
  worldWidth,
  worldHeight,
  agents,
  missions,
  routes,
  selectedAgentId,
  selectedMissionId,
  onSelectAgent,
  onSelectMission,
  mode,
  onAreaCornerClick,
  onMapClick,
  draftArea,
  draftWorldWidth,
  draftWorldHeight,
  draftTargetCell,
  draftDrones,
  draftMissions,
  draftMissionAreas,
  pendingMissionAreaCorners,
}: GeoMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const agentMarkersRef = useRef<Map<string, L.Marker>>(new Map());
  const missionMarkersRef = useRef<Map<string, L.Marker>>(new Map());
  const missionAreaLayersRef = useRef<Map<string, L.Rectangle>>(new Map());
  const waypointMarkersRef = useRef<Map<string, L.Marker[]>>(new Map());
  const routeLayersRef = useRef<Map<string, L.Polyline[]>>(new Map());
  const draftMarkerRef = useRef<L.Marker | null>(null);
  const draftAreaLayerRef = useRef<L.Rectangle | null>(null);
  const draftDroneMarkersRef = useRef<Map<string, L.Marker>>(new Map());
  const draftMissionMarkersRef = useRef<Map<string, L.Marker>>(new Map());
  const draftMissionAreaLayersRef = useRef<Map<string, L.Rectangle>>(new Map());
  const pendingMissionAreaLayerRef = useRef<L.Rectangle | null>(null);
  const hasFitBoundsRef = useRef(false);

  const modeRef = useRef(mode);
  modeRef.current = mode;
  const draftAreaRef = useRef(draftArea);
  draftAreaRef.current = draftArea;
  const draftWorldWidthRef = useRef(draftWorldWidth);
  draftWorldWidthRef.current = draftWorldWidth;
  const draftWorldHeightRef = useRef(draftWorldHeight);
  draftWorldHeightRef.current = draftWorldHeight;
  const onAreaCornerClickRef = useRef(onAreaCornerClick);
  onAreaCornerClickRef.current = onAreaCornerClick;
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;
  const onSelectAgentRef = useRef(onSelectAgent);
  onSelectAgentRef.current = onSelectAgent;
  const onSelectMissionRef = useRef(onSelectMission);
  onSelectMissionRef.current = onSelectMission;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    }).setView([BENGALURU_CENTER.lat, BENGALURU_CENTER.lng], BENGALURU_DEFAULT_ZOOM);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    map.on("click", (e: L.LeafletMouseEvent) => {
      if (modeRef.current === "select-area") {
        onAreaCornerClickRef.current?.({ lat: e.latlng.lat, lng: e.latlng.lng });
        return;
      }
      if (modeRef.current === "place-drone" || modeRef.current === "place-mission") {
        const areaBounds = draftAreaRef.current;
        const areaWidth = draftWorldWidthRef.current;
        const areaHeight = draftWorldHeightRef.current;
        if (!areaBounds || !areaWidth || !areaHeight) return;
        const cell = geoToWorld(e.latlng.lat, e.latlng.lng, areaBounds, areaWidth, areaHeight);
        onMapClickRef.current?.(cell);
        return;
      }
    });

    // Agent markers get a CSS transition (see GeoMap.css) so a tick's
    // position update glides instead of teleporting. Leaflet
    // repositions every marker the same way while the user pans or
    // zooms, though, so without this the agent markers would visibly
    // lag behind the map tiles during a drag/zoom gesture instead of
    // tracking it directly. Suspend the transition for the duration
    // of any such gesture; movestart/moveend cover panning, and
    // zoomstart/zoomend cover zoom-driven repositioning.
    const container = map.getContainer();
    const suspendMarkerTransitions = () => container.classList.add("geo-map--interacting");
    const resumeMarkerTransitions = () => container.classList.remove("geo-map--interacting");
    map.on("movestart", suspendMarkerTransitions);
    map.on("moveend", resumeMarkerTransitions);
    map.on("zoomstart", suspendMarkerTransitions);
    map.on("zoomend", resumeMarkerTransitions);

    mapRef.current = map;

    return () => {
      map.off("movestart", suspendMarkerTransitions);
      map.off("moveend", resumeMarkerTransitions);
      map.off("zoomstart", suspendMarkerTransitions);
      map.off("zoomend", resumeMarkerTransitions);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds || hasFitBoundsRef.current) return;
    map.fitBounds(boundsToLeafletCorners(bounds));
    hasFitBoundsRef.current = true;
  }, [bounds]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (draftAreaLayerRef.current) {
      draftAreaLayerRef.current.remove();
      draftAreaLayerRef.current = null;
    }

    if (draftArea) {
      draftAreaLayerRef.current = L.rectangle(boundsToLeafletCorners(draftArea), {
        className: "geo-map__draft-area",
      }).addTo(map);
    }
  }, [draftArea]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds || !worldWidth || !worldHeight) return;
    const markers = agentMarkersRef.current;
    const seen = new Set<string>();

    for (const agent of agents) {
      seen.add(agent.id);
      const { lat, lng } = worldToGeo(agent.x, agent.y, bounds, worldWidth, worldHeight);
      const isSelected = selectedAgentId === agent.id;
      const icon = agentDivIcon(agent, isSelected);

      let marker = markers.get(agent.id);
      if (!marker) {
        marker = L.marker([lat, lng], { icon, keyboard: true });
        marker.on("click", () => onSelectAgentRef.current(agent.id));
        marker.addTo(map);
        markers.set(agent.id, marker);
      } else {
        marker.setLatLng([lat, lng]);
        marker.setIcon(icon);
      }
      // Area Watch coverage progress, when this agent's active route
      // reports it (see AgentRouteResponse.current_waypoint/
      // total_waypoints) — absent for a point mission or return leg.
      const activeRoute = routes.get(agent.id);
      const waypointText =
        activeRoute?.current_waypoint != null && activeRoute.total_waypoints != null
          ? ` — waypoint ${activeRoute.current_waypoint}/${activeRoute.total_waypoints}`
          : "";
      marker.bindTooltip(
        `${agent.id} — ${agent.platform_type.replace(/_/g, " ")} — ${agent.activity.replace(/_/g, " ")} — ${agent.battery_level}%${waypointText}`,
        { direction: "top", offset: [0, -16] },
      );
    }

    for (const [id, marker] of markers) {
      if (!seen.has(id)) {
        marker.remove();
        markers.delete(id);
      }
    }
  }, [agents, selectedAgentId, bounds, worldWidth, worldHeight, routes]);

  // Missions — a mission with exactly one target cell gets a marker
  // (unchanged point-mission behavior); a mission with MORE than one
  // target cell (an area-watch mission) gets a rectangle covering its
  // full target_cells instead, plus a small marker at the rectangle's
  // center so it is still clickable/selectable the same way a point
  // mission is. Both draw from the same live mission.target_cells the
  // backend returned -- nothing here is invented or recomputed.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds || !worldWidth || !worldHeight) return;
    const markers = missionMarkersRef.current;
    const areaLayers = missionAreaLayersRef.current;
    const waypointGroups = waypointMarkersRef.current;
    const seenMarkers = new Set<string>();
    const seenAreas = new Set<string>();
    const seenWaypointGroups = new Set<string>();

    for (const mission of missions) {
      if (mission.target_cells.length === 0) continue;
      const isSelected = selectedMissionId === mission.id;
      const isArea = mission.target_cells.length > 1;

      if (isArea) {
        seenAreas.add(mission.id);
        const areaBounds = cellsToGeoBounds(mission.target_cells, bounds, worldWidth, worldHeight);
        let layer = areaLayers.get(mission.id);
        const className = isSelected
          ? "geo-map__mission-area geo-map__mission-area--selected"
          : "geo-map__mission-area";
        if (!layer) {
          layer = L.rectangle(boundsToLeafletCorners(areaBounds), { className }).addTo(map);
          layer.on("click", () => onSelectMissionRef.current(mission.id));
          areaLayers.set(mission.id, layer);
        } else {
          layer.setBounds(boundsToLeafletCorners(areaBounds));
        }
        layer.bindTooltip(
          `${mission.name} — ${mission.priority} — ${mission.status.replace(/_/g, " ")} — watch area`,
          { direction: "top" },
        );
      }

      // The ~4 Area Watch coverage waypoints, drawn as small numbered
      // markers so the coverage route itself is visible on the map --
      // not just the rectangle it happens inside. mission.coverage_waypoints
      // comes straight from the backend (coverage_waypoints_for), in
      // the exact order a drone visits them. Progress (which waypoint
      // is current/already visited) comes from whichever agent is
      // actually assigned to this mission, if any -- real backend
      // state (AgentRouteResponse.current_waypoint), never guessed.
      if (isArea && mission.coverage_waypoints && mission.coverage_waypoints.length > 0) {
        seenWaypointGroups.add(mission.id);
        const assignedAgent = agents.find((a) => a.current_mission_id === mission.id);
        const activeRoute = assignedAgent ? routes.get(assignedAgent.id) : undefined;
        const currentWaypoint =
          activeRoute?.current_waypoint != null ? activeRoute.current_waypoint : null;

        const existingGroup = waypointGroups.get(mission.id) ?? [];
        const nextGroup: L.Marker[] = [];

        mission.coverage_waypoints.forEach((cell, index) => {
          const order = index + 1;
          const status: "visited" | "current" | "upcoming" =
            currentWaypoint === null
              ? "upcoming"
              : order < currentWaypoint
                ? "visited"
                : order === currentWaypoint
                  ? "current"
                  : "upcoming";

          const { lat, lng } = worldToGeo(cell[0], cell[1], bounds, worldWidth, worldHeight);
          const icon = waypointDivIcon(order, status);

          let waypointMarker = existingGroup[index];
          if (!waypointMarker) {
            waypointMarker = L.marker([lat, lng], { icon, keyboard: false, interactive: false });
            waypointMarker.addTo(map);
          } else {
            waypointMarker.setLatLng([lat, lng]);
            waypointMarker.setIcon(icon);
          }
          const statusLabel =
            status === "current" ? " (current)" : status === "visited" ? " (visited)" : "";
          waypointMarker.bindTooltip(
            `${mission.name} — coverage waypoint ${order} of ${mission.coverage_waypoints!.length}${statusLabel}`,
            { direction: "top", offset: [0, -10] },
          );
          nextGroup.push(waypointMarker);
        });

        // A mission's coverage waypoint count is fixed once the
        // mission exists (target_cells never changes after creation),
        // so this only ever runs on the very first render of this
        // group -- kept for safety rather than an expected case.
        for (let i = nextGroup.length; i < existingGroup.length; i++) {
          existingGroup[i]?.remove();
        }
        waypointGroups.set(mission.id, nextGroup);
      }

      seenMarkers.add(mission.id);
      const targetCell = isArea
        ? (() => {
            const xs = mission.target_cells.map((c) => c[0]);
            const ys = mission.target_cells.map((c) => c[1]);
            return [
              Math.round((Math.min(...xs) + Math.max(...xs)) / 2),
              Math.round((Math.min(...ys) + Math.max(...ys)) / 2),
            ] as [number, number];
          })()
        : mission.target_cells[0];
      const { lat, lng } = worldToGeo(targetCell[0], targetCell[1], bounds, worldWidth, worldHeight);
      const icon = missionDivIcon(mission, isSelected);

      let marker = markers.get(mission.id);
      if (!marker) {
        marker = L.marker([lat, lng], { icon, keyboard: true });
        marker.on("click", () => onSelectMissionRef.current(mission.id));
        marker.addTo(map);
        markers.set(mission.id, marker);
      } else {
        marker.setLatLng([lat, lng]);
        marker.setIcon(icon);
      }
      if (!isArea) {
        marker.bindTooltip(
          `${mission.name} — ${mission.priority} — ${mission.status.replace(/_/g, " ")}`,
          { direction: "top", offset: [0, -14] },
        );
      }
    }

    for (const [id, marker] of markers) {
      if (!seenMarkers.has(id)) {
        marker.remove();
        markers.delete(id);
      }
    }
    for (const [id, layer] of areaLayers) {
      if (!seenAreas.has(id)) {
        layer.remove();
        areaLayers.delete(id);
      }
    }
    for (const [id, group] of waypointGroups) {
      if (!seenWaypointGroups.has(id)) {
        for (const waypointMarker of group) waypointMarker.remove();
        waypointGroups.delete(id);
      }
    }
  }, [missions, selectedMissionId, bounds, worldWidth, worldHeight, agents, routes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds || !worldWidth || !worldHeight) return;
    const layers = routeLayersRef.current;

    for (const existing of layers.values()) {
      for (const line of existing) line.remove();
    }
    layers.clear();

    for (const agent of agents) {
      const route = routes.get(agent.id);
      if (!route || route.cells.length < 2) continue;

      const currentIndex = route.cells.findIndex(
        ([cx, cy]) => cx === agent.x && cy === agent.y,
      );
      const splitAt = currentIndex === -1 ? 0 : currentIndex;
      const traveled = route.cells.slice(0, splitAt + 1);
      const remaining = route.cells.slice(splitAt);
      const isSelected =
        selectedAgentId === agent.id ||
        (selectedMissionId !== null && selectedMissionId === agent.current_mission_id);

      const toLatLngs = (cells: [number, number][]) =>
        cells.map(([cx, cy]) => {
          const { lat, lng } = worldToGeo(cx, cy, bounds, worldWidth, worldHeight);
          return [lat, lng] as [number, number];
        });

      const created: L.Polyline[] = [];
      if (traveled.length >= 2) {
        created.push(
          L.polyline(toLatLngs(traveled), {
            className: isSelected
              ? "geo-map__route-traveled geo-map__route-traveled--selected"
              : "geo-map__route-traveled",
            weight: isSelected ? 4 : 3,
          }).addTo(map),
        );
      }
      if (remaining.length >= 2) {
        created.push(
          L.polyline(toLatLngs(remaining), {
            className: isSelected
              ? "geo-map__route geo-map__route--selected"
              : "geo-map__route",
            weight: isSelected ? 3 : 2,
            dashArray: "4 6",
          }).addTo(map),
        );
      }
      layers.set(agent.id, created);
    }
  }, [agents, routes, selectedAgentId, selectedMissionId, bounds, worldWidth, worldHeight]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds || !worldWidth || !worldHeight) return;

    if (draftMarkerRef.current) {
      draftMarkerRef.current.remove();
      draftMarkerRef.current = null;
    }

    if (draftTargetCell) {
      const { lat, lng } = worldToGeo(
        draftTargetCell.x,
        draftTargetCell.y,
        bounds,
        worldWidth,
        worldHeight,
      );
      draftMarkerRef.current = L.marker([lat, lng], {
        icon: draftDivIcon(),
        keyboard: false,
      }).addTo(map);
    }
  }, [draftTargetCell, bounds, worldWidth, worldHeight]);

  useEffect(() => {
    const map = mapRef.current;
    const markers = draftDroneMarkersRef.current;
    if (!map || !draftArea || !draftWorldWidth || !draftWorldHeight || !draftDrones) {
      for (const marker of markers.values()) marker.remove();
      markers.clear();
      return;
    }

    const seen = new Set<string>();
    for (const drone of draftDrones) {
      seen.add(drone.id);
      const { lat, lng } = worldToGeo(
        drone.x,
        drone.y,
        draftArea,
        draftWorldWidth,
        draftWorldHeight,
      );
      const icon = L.divIcon({
        className: "geo-map__draft-drone-icon",
        html: `
          <div class="geo-map__draft-drone-icon-inner">
            <span class="geo-map__draft-drone-glyph">${platformGlyphSvg("DRONE")}</span>
          </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });

      let marker = markers.get(drone.id);
      if (!marker) {
        marker = L.marker([lat, lng], { icon, keyboard: false });
        marker.addTo(map);
        markers.set(drone.id, marker);
      } else {
        marker.setLatLng([lat, lng]);
        marker.setIcon(icon);
      }
      marker.bindTooltip(drone.id, { direction: "top", offset: [0, -16] });
    }

    for (const [id, marker] of markers) {
      if (!seen.has(id)) {
        marker.remove();
        markers.delete(id);
      }
    }
  }, [draftDrones, draftArea, draftWorldWidth, draftWorldHeight]);

  // Configured-but-not-yet-submitted POINT missions only -- area-watch
  // mission drafts are handled separately below (draftMissionAreas).
  useEffect(() => {
    const map = mapRef.current;
    const markers = draftMissionMarkersRef.current;
    if (!map || !draftArea || !draftWorldWidth || !draftWorldHeight || !draftMissions) {
      for (const marker of markers.values()) marker.remove();
      markers.clear();
      return;
    }

    const seen = new Set<string>();
    for (const mission of draftMissions) {
      seen.add(mission.id);
      const { lat, lng } = worldToGeo(
        mission.x,
        mission.y,
        draftArea,
        draftWorldWidth,
        draftWorldHeight,
      );
      const icon = draftDivIcon();

      let marker = markers.get(mission.id);
      if (!marker) {
        marker = L.marker([lat, lng], { icon, keyboard: false });
        marker.addTo(map);
        markers.set(mission.id, marker);
      } else {
        marker.setLatLng([lat, lng]);
        marker.setIcon(icon);
      }
      marker.bindTooltip(mission.name, { direction: "top", offset: [0, -14] });
    }

    for (const [id, marker] of markers) {
      if (!seen.has(id)) {
        marker.remove();
        markers.delete(id);
      }
    }
  }, [draftMissions, draftArea, draftWorldWidth, draftWorldHeight]);

  // Configured-but-not-yet-submitted AREA-WATCH missions — rendered as
  // a full rectangle (same visual language as the operating-area
  // draft rectangle), converted against the draft operating area,
  // covering every cell in that mission's own cells list.
  useEffect(() => {
    const map = mapRef.current;
    const layers = draftMissionAreaLayersRef.current;
    if (!map || !draftArea || !draftWorldWidth || !draftWorldHeight || !draftMissionAreas) {
      for (const layer of layers.values()) layer.remove();
      layers.clear();
      return;
    }

    const seen = new Set<string>();
    for (const mission of draftMissionAreas) {
      if (mission.cells.length === 0) continue;
      seen.add(mission.id);
      const geoBounds = cellsToGeoBounds(mission.cells, draftArea, draftWorldWidth, draftWorldHeight);

      let layer = layers.get(mission.id);
      if (!layer) {
        layer = L.rectangle(boundsToLeafletCorners(geoBounds), {
          className: "geo-map__draft-mission-area",
        }).addTo(map);
        layers.set(mission.id, layer);
      } else {
        layer.setBounds(boundsToLeafletCorners(geoBounds));
      }
      layer.bindTooltip(`${mission.name} — watch area`, { direction: "top" });
    }

    for (const [id, layer] of layers) {
      if (!seen.has(id)) {
        layer.remove();
        layers.delete(id);
      }
    }
  }, [draftMissionAreas, draftArea, draftWorldWidth, draftWorldHeight]);

  // Live preview of an in-progress watch-area corner selection: shown
  // between the first and second corner clicks while creating or
  // editing an area-watch mission.
  useEffect(() => {
    const map = mapRef.current;
    if (pendingMissionAreaLayerRef.current) {
      pendingMissionAreaLayerRef.current.remove();
      pendingMissionAreaLayerRef.current = null;
    }
    if (
      !map ||
      !draftArea ||
      !draftWorldWidth ||
      !draftWorldHeight ||
      !pendingMissionAreaCorners ||
      !pendingMissionAreaCorners[1]
    ) {
      return;
    }
    const [corner1, corner2] = pendingMissionAreaCorners;
    if (!corner2) return;
    const minX = Math.min(corner1.x, corner2.x);
    const maxX = Math.max(corner1.x, corner2.x);
    const minY = Math.min(corner1.y, corner2.y);
    const maxY = Math.max(corner1.y, corner2.y);
    const cells: [number, number][] = [];
    for (let x = minX; x <= maxX; x++) {
      for (let y = minY; y <= maxY; y++) cells.push([x, y]);
    }
    const geoBounds = cellsToGeoBounds(cells, draftArea, draftWorldWidth, draftWorldHeight);
    pendingMissionAreaLayerRef.current = L.rectangle(boundsToLeafletCorners(geoBounds), {
      className: "geo-map__draft-mission-area",
    }).addTo(map);
  }, [pendingMissionAreaCorners, draftArea, draftWorldWidth, draftWorldHeight]);

  return (
    <div className="geo-map">
      <div ref={containerRef} className="geo-map__container" />
    </div>
  );
}
