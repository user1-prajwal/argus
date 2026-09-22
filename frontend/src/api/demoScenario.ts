// /**
//  * The Version 1 scenario payload sent to POST /scenarios on load.
//  *
//  * There is no "list scenarios" or "load saved scenario" endpoint in
//  * Version 1 (docs/api-spec.md defines only the six session endpoints),
//  * so the console needs seed content to create a session against. This
//  * mirrors app/scenario/runner.py's build_demo_scenario() field-for-
//  * field — the same 12x12 world, wall, four agents, and four missions
//  * already used by the backend's own demo/integration scenario — rather
//  * than inventing new placeholder data. See docs/api-model.md, "State
//  * Serialization": the frontend never invents data the backend does not
//  * already model.
//  */

// import type { ScenarioCreateRequest } from "../types/argus";

// export const DEMO_SCENARIO: ScenarioCreateRequest = {
//   world: { width: 12, height: 12 },
//   obstacles: Array.from({ length: 9 }, (_, y) => ({
//     id: `wall-${y}`,
//     x: 6,
//     y,
//     type: "Wall",
//   })),
//   agents: [
//     {
//       id: "drone-thermal",
//       platform_type: "DRONE",
//       x: 0,
//       y: 0,
//       battery_level: 90,
//       capabilities: ["thermal_camera"],
//     },
//     {
//       id: "drone-lidar",
//       platform_type: "DRONE",
//       x: 0,
//       y: 11,
//       battery_level: 95,
//       capabilities: ["lidar"],
//     },
//     {
//       id: "generalist",
//       platform_type: "GROUND_ROBOT",
//       x: 5,
//       y: 5,
//       battery_level: 100,
//       capabilities: [],
//     },
//     {
//       id: "low-battery-unit",
//       platform_type: "AUTONOMOUS_VEHICLE",
//       x: 11,
//       y: 0,
//       battery_level: 8,
//       capabilities: [],
//     },
//   ],
//   missions: [
//     {
//       id: "open-recon",
//       name: "Open Area Recon",
//       description: "General reconnaissance; no special sensor required.",
//       priority: "CRITICAL",
//       target_cells: [[3, 3]],
//       required_capabilities: [],
//     },
//     {
//       id: "thermal-survey",
//       name: "Thermal Survey",
//       description: "Requires a thermal camera.",
//       priority: "HIGH",
//       target_cells: [[9, 3]],
//       required_capabilities: ["thermal_camera"],
//     },
//     {
//       id: "lidar-survey",
//       name: "LIDAR Survey",
//       description: "Requires LIDAR.",
//       priority: "MEDIUM",
//       target_cells: [[9, 9]],
//       required_capabilities: ["lidar"],
//     },
//     {
//       id: "distant-patrol",
//       name: "Distant Patrol",
//       description:
//         "Far from most agents; battery may not be enough for the round trip.",
//       priority: "LOW",
//       target_cells: [[11, 11]],
//       required_capabilities: [],
//     },
//   ],
// };


import type { ScenarioCreateRequest } from "../types/argus";

export const DEMO_SCENARIO: ScenarioCreateRequest = {
  world: { width: 40, height: 40 },
  obstacles: Array.from({ length: 30 }, (_, y) => ({
    id: `wall-${y}`,
    x: 20,
    y,
    type: "Wall",
  })),
  agents: [
    {
      id: "drone-thermal",
      platform_type: "DRONE",
      x: 0,
      y: 0,
      battery_level: 90,
      capabilities: ["thermal_camera"],
    },
    {
      id: "drone-lidar",
      platform_type: "DRONE",
      x: 0,
      y: 39,
      battery_level: 95,
      capabilities: ["lidar"],
    },
    {
      id: "generalist",
      platform_type: "GROUND_ROBOT",
      x: 20,
      y: 20,
      battery_level: 100,
      capabilities: [],
    },
    {
      id: "low-battery-unit",
      platform_type: "AUTONOMOUS_VEHICLE",
      x: 39,
      y: 0,
      battery_level: 8,
      capabilities: [],
    },
  ],
  missions: [
    {
      id: "open-recon",
      name: "Open Area Recon",
      description: "General reconnaissance; no special sensor required.",
      priority: "CRITICAL",
      target_cells: [[10, 10]],
      required_capabilities: [],
    },
    {
      id: "thermal-survey",
      name: "Thermal Survey",
      description: "Requires a thermal camera.",
      priority: "HIGH",
      target_cells: [[30, 10]],
      required_capabilities: ["thermal_camera"],
    },
    {
      id: "lidar-survey",
      name: "LIDAR Survey",
      description: "Requires LIDAR.",
      priority: "MEDIUM",
      target_cells: [[30, 30]],
      required_capabilities: ["lidar"],
    },
    {
      id: "distant-patrol",
      name: "Distant Patrol",
      description:
        "Far from most agents; battery may not be enough for the round trip.",
      priority: "LOW",
      target_cells: [[39, 39]],
      required_capabilities: [],
    },
  ],
};