/**
 * A compact, schematic drone glyph for agent markers on the map.
 *
 * Version 1 of the Bengaluru scenario spawns drones exclusively (see
 * backend/app/geo/scenario_builder.py's _AGENT_START_FRACTIONS
 * comment) — one platform type done well rather than several done
 * thinly. This module used to export a glyph per PlatformType value;
 * that variety is gone by product decision, not by necessity. The
 * PlatformType enum itself is untouched on the backend (still four
 * values, app/agent/enums.py) — this is a display-layer scope choice,
 * not a claim that ARGUS only supports drones architecturally.
 *
 * Colored entirely via CSS currentColor so the same shape can be
 * recolored per activity status without duplicating markup. Drawn in
 * a 0-24 viewBox, centered, at a size tuned for legibility on a small
 * (~30px) map marker rather than as a large standalone icon.
 */

import type { PlatformType } from "../types/argus";

/**
 * Quadrotor, viewed from above: a center hub, four arms, and open
 * (unfilled) rotor rings — reads clearly as "drone" even at marker
 * scale, and stays visually distinct from the mission-target diamond
 * and the plain circles this project moved away from.
 */
const DRONE_GLYPH = `
  <line x1="12" y1="12" x2="4.5" y2="4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  <line x1="12" y1="12" x2="19.5" y2="4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  <line x1="12" y1="12" x2="4.5" y2="19.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  <line x1="12" y1="12" x2="19.5" y2="19.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  <circle cx="4.5" cy="4.5" r="2.8" fill="none" stroke="currentColor" stroke-width="1.8" />
  <circle cx="19.5" cy="4.5" r="2.8" fill="none" stroke="currentColor" stroke-width="1.8" />
  <circle cx="4.5" cy="19.5" r="2.8" fill="none" stroke="currentColor" stroke-width="1.8" />
  <circle cx="19.5" cy="19.5" r="2.8" fill="none" stroke="currentColor" stroke-width="1.8" />
  <circle cx="12" cy="12" r="3.2" fill="currentColor" />
`;

/**
 * Returns a complete standalone SVG markup string (viewBox 0 0 24 24)
 * for the drone glyph, colored via CSS `color` on the containing
 * element. Intended for use inside a Leaflet L.divIcon's html string.
 *
 * Takes platformType for call-site compatibility with GeoMap.tsx (an
 * agent's declared type is still whatever the backend reports, even
 * though this Version 1 scenario only ever generates DRONE) — but
 * always renders the same drone glyph, since that is the only visual
 * this module implements now.
 */
export function platformGlyphSvg(_platformType: PlatformType): string {
  return `<svg viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">${DRONE_GLYPH}</svg>`;
}
