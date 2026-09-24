import type { ControlAction } from "../hooks/useScenario";
import type { ScenarioPhase, StepResponse } from "../types/argus";
import "./ControlBar.css";

/**
 * No Start button here by design: the project's flow submits the
 * operating area, fleet, and every configured mission together in one
 * request that also starts planning immediately (see App.tsx's
 * handleStart / useScenario.ts's createAreaAndStart) — there is no
 * separate "created but not yet started" state a user ever sees, so a
 * Start control here would always render disabled. Step/Run/Reset
 * remain exactly as before.
 */
interface ControlBarProps {
  phase: ScenarioPhase | null;
  tick: number | null;
  pendingAction: ControlAction;
  isPlaying: boolean;
  lastStepResult: StepResponse | null;
  onStep: () => void;
  onRun: () => void;
  onReset: () => void;
}

function ActivityGroup({
  label,
  ids,
  colorVar,
}: {
  label: string;
  ids: string[];
  colorVar: string;
}) {
  return (
    <div className="control-bar__activity-group">
      <span
        className="control-bar__activity-dot"
        style={{ background: `var(${colorVar})` }}
      />
      <span className="control-bar__activity-label">{label}</span>
      <span className="control-bar__activity-count data">{ids.length}</span>
    </div>
  );
}

export function ControlBar({
  phase,
  tick,
  pendingAction,
  isPlaying,
  lastStepResult,
  onStep,
  onRun,
  onReset,
}: ControlBarProps) {
  const notStarted = phase === "not_started";
  const settled = phase === "settled";
  const busy = pendingAction !== null || isPlaying;

  return (
    <div className="control-bar">
      <div className="control-bar__buttons">
        <button
          className="control-bar__btn"
          onClick={onStep}
          disabled={busy || notStarted || settled}
        >
          {pendingAction === "step" ? "Stepping…" : "Step"}
        </button>
        <button
          className="control-bar__btn"
          onClick={onRun}
          disabled={busy || notStarted || settled}
        >
          {isPlaying ? "Running…" : "Run"}
        </button>
        <button
          className="control-bar__btn control-bar__btn--ghost"
          onClick={onReset}
          disabled={pendingAction === "reset"}
        >
          {pendingAction === "reset" ? "Resetting…" : "Reset"}
        </button>
      </div>

      <div className="control-bar__divider" />

      <div className="control-bar__tick">
        <span className="control-bar__tick-label">Tick</span>
        <span className="control-bar__tick-value data">
          {tick !== null ? tick : "—"}
        </span>
      </div>

      <div className="control-bar__divider" />

      <div className="control-bar__activity">
        <ActivityGroup
          label="Moved"
          ids={lastStepResult?.moved ?? []}
          colorVar="--status-executing"
        />
        <ActivityGroup
          label="Waiting"
          ids={lastStepResult?.waiting ?? []}
          colorVar="--status-returning"
        />
        <ActivityGroup
          label="Completed"
          ids={lastStepResult?.completed_missions ?? []}
          colorVar="--status-completed"
        />
        <ActivityGroup
          label="Failed"
          ids={lastStepResult?.failed_missions ?? []}
          colorVar="--status-failed"
        />
        <ActivityGroup
          label="Returned"
          ids={lastStepResult?.returned_home ?? []}
          colorVar="--status-idle"
        />
      </div>
    </div>
  );
}
