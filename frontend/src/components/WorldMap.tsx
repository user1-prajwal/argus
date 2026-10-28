import { useMemo } from "react";
import type { KeyboardEvent } from "react";
import type { AgentOut, AgentRouteResponse, MissionOut, WorldSummaryOut } from "../types/argus";
import "./WorldMap.css";

interface WorldMapProps {
  world: WorldSummaryOut;
  agents: AgentOut[];
  missions: MissionOut[];
  /**
   * Obstacle cells. The state endpoint only reports an obstacle
   * *count* (world.obstacles), not positions — docs/api-spec.md's
   * GET /scenarios response shows world as a summary object, and
   * docs/api-model.md is explicit that "World -> its... summary...
   * rather than every cell." Version 1 has no endpoint that returns
   * obstacle coordinates. This console always creates its own session
   * from a known seed payload, so App.tsx reads these coordinates back
   * from that same payload rather than from the backend — see the
   * comment at OBSTACLE_CELLS in App.tsx and the README's "Known scope
   * gap" section for what this means for an externally-created session.
   */
  obstacleCells: [number, number][];
  /**
   * The real route each executing/returning agent is following, keyed
   * by agent id — fetched from
   * GET /scenarios/{session_id}/agents/{agent_id}/route (see
   * useScenario.ts's refresh()). This is PathPlanner's actual A*
   * output as SimulationEngine is currently following it, not a
   * client-side approximation — the map only draws what this map
   * contains, never a straight agent-to-target line.
   */
  routes: Map<string, AgentRouteResponse>;
  selectedAgentId: string | null;
  selectedMissionId: string | null;
  onSelectAgent: (id: string) => void;
  onSelectMission: (id: string) => void;
}

const CELL = 34;
const PADDING = 28;

interface GridLine {
  key: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

const ACTIVITY_COLOR: Record<AgentOut["activity"], string> = {
  IDLE: "var(--status-idle)",
  ASSIGNED: "var(--status-assigned)",
  EXECUTING_MISSION: "var(--status-executing)",
  RETURNING: "var(--status-returning)",
  CHARGING: "var(--status-charging)",
};

const PRIORITY_COLOR: Record<MissionOut["priority"], string> = {
  LOW: "var(--priority-low)",
  MEDIUM: "var(--priority-medium)",
  HIGH: "var(--priority-high)",
  CRITICAL: "var(--priority-critical)",
};

function cellCenter(x: number, y: number, height: number) {
  // World Y increases north (see app/world/world.py's neighbor-offset
  // comment: "'Up' is +y (north)"), so screen-row is flipped: larger y
  // renders higher on screen, matching the backend's own coordinate
  // convention rather than inverting it.
  return {
    cx: PADDING + x * CELL + CELL / 2,
    cy: PADDING + (height - 1 - y) * CELL + CELL / 2,
  };
}

export function WorldMap({
  world,
  agents,
  missions,
  obstacleCells,
  routes,
  selectedAgentId,
  selectedMissionId,
  onSelectAgent,
  onSelectMission,
}: WorldMapProps) {
  const width = world.width * CELL + PADDING * 2;
  const height = world.height * CELL + PADDING * 2;

  const gridLines = useMemo(() => {
    const lines: GridLine[] = [];
    for (let x = 0; x <= world.width; x++) {
      lines.push({
        key: `v${x}`,
        x1: PADDING + x * CELL,
        y1: PADDING,
        x2: PADDING + x * CELL,
        y2: PADDING + world.height * CELL,
      });
    }
    for (let y = 0; y <= world.height; y++) {
      lines.push({
        key: `h${y}`,
        x1: PADDING,
        y1: PADDING + y * CELL,
        x2: PADDING + world.width * CELL,
        y2: PADDING + y * CELL,
      });
    }
    return lines;
  }, [world.width, world.height]);

  return (
    <div className="world-map">
      <svg
        className="world-map__svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Operational grid, ${world.width} by ${world.height} cells, showing ${agents.length} agents and ${missions.length} missions`}
      >
        <rect x={0} y={0} width={width} height={height} className="world-map__bg" />

        {/* Grid */}
        <g className="world-map__grid">
          {gridLines.map((l: GridLine) => (
            <line key={l.key} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
        </g>

        {/* Obstacles */}
        <g className="world-map__obstacles">
          {obstacleCells.map(([ox, oy]) => {
            const { cx, cy } = cellCenter(ox, oy, world.height);
            return (
              <rect
                key={`obstacle-${ox}-${oy}`}
                x={cx - CELL / 2}
                y={cy - CELL / 2}
                width={CELL}
                height={CELL}
                className="world-map__obstacle-cell"
              />
            );
          })}
        </g>

        {/* Real routes: PathPlanner's actual A* output, as
            SimulationEngine is currently following it — fetched per
            agent from GET /scenarios/{id}/agents/{agent_id}/route.
            Not a straight guide line and not recomputed here; an
            agent absent from `routes` (idle, unassigned, or just
            arrived) simply draws no line. Split at the agent's current
            cell so the traveled segment reads visually differently
            from what's still ahead — "route progress," not just the
            static path. */}
        <g className="world-map__routes">
          {agents.map((agent) => {
            const route = routes.get(agent.id);
            if (!route || route.cells.length < 2) return null;

            const currentIndex = route.cells.findIndex(
              ([cx, cy]) => cx === agent.x && cy === agent.y,
            );
            const splitAt = currentIndex === -1 ? 0 : currentIndex;

            const toPoints = (cells: [number, number][]) =>
              cells
                .map(([cx, cy]) => {
                  const { cx: px, cy: py } = cellCenter(cx, cy, world.height);
                  return `${px},${py}`;
                })
                .join(" ");

            const traveled = route.cells.slice(0, splitAt + 1);
            const remaining = route.cells.slice(splitAt);

            const isSelected =
              selectedAgentId === agent.id ||
              (selectedMissionId !== null &&
                selectedMissionId === agent.current_mission_id);

            return (
              <g key={`route-${agent.id}`}>
                {traveled.length >= 2 && (
                  <polyline
                    points={toPoints(traveled)}
                    className={
                      isSelected
                        ? "world-map__route-traveled world-map__route-traveled--selected"
                        : "world-map__route-traveled"
                    }
                  />
                )}
                {remaining.length >= 2 && (
                  <polyline
                    points={toPoints(remaining)}
                    className={
                      isSelected
                        ? "world-map__route world-map__route--selected"
                        : "world-map__route"
                    }
                  />
                )}
              </g>
            );
          })}
        </g>

        {/* Mission targets */}
        <g className="world-map__missions">
          {missions.map((mission) => {
            if (mission.target_cells.length === 0) return null;
            const [tx, ty] = mission.target_cells[0];
            const { cx, cy } = cellCenter(tx, ty, world.height);
            const isSelected = selectedMissionId === mission.id;
            return (
              <g
                key={mission.id}
                className={
                  isSelected
                    ? "world-map__mission-marker world-map__mission-marker--selected"
                    : "world-map__mission-marker"
                }
                style={{ ["--priority-color" as string]: PRIORITY_COLOR[mission.priority] }}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                aria-label={`Mission ${mission.name}, priority ${mission.priority}, status ${mission.status}`}
                onClick={() => onSelectMission(mission.id)}
                onKeyDown={(e: KeyboardEvent<SVGGElement>) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectMission(mission.id);
                  }
                }}
              >
                {isSelected && (
                  <circle cx={cx} cy={cy} r={13} className="world-map__selection-ring" />
                )}
                <path
                  d={`M ${cx} ${cy - 9} L ${cx + 9} ${cy} L ${cx} ${cy + 9} L ${cx - 9} ${cy} Z`}
                  className="world-map__mission-diamond"
                />
              </g>
            );
          })}
        </g>

        {/* Agents */}
        <g className="world-map__agents">
          {agents.map((agent) => {
            const { cx, cy } = cellCenter(agent.x, agent.y, world.height);
            const isSelected = selectedAgentId === agent.id;
            return (
              <g
                key={agent.id}
                className={
                  isSelected
                    ? "world-map__agent-marker world-map__agent-marker--selected"
                    : "world-map__agent-marker"
                }
                style={{ ["--activity-color" as string]: ACTIVITY_COLOR[agent.activity] }}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                aria-label={`Agent ${agent.id}, ${agent.platform_type}, ${agent.activity}, battery ${agent.battery_level} percent`}
                onClick={() => onSelectAgent(agent.id)}
                onKeyDown={(e: KeyboardEvent<SVGGElement>) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectAgent(agent.id);
                  }
                }}
              >
                {isSelected && (
                  <circle cx={cx} cy={cy} r={13} className="world-map__selection-ring" />
                )}
                <circle cx={cx} cy={cy} r={7} className="world-map__agent-dot" />
                {agent.health_status !== "ONLINE" && (
                  <text x={cx} y={cy - 12} className="world-map__agent-flag">
                    !
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
