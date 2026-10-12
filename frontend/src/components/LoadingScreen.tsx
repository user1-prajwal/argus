import "./LoadingScreen.css";

export function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-screen__mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="loading-screen__text">Connecting to ARGUS session…</p>
    </div>
  );
}
