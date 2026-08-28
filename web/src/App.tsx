import { useEffect, useState } from "react";

type Health = {
  status: string;
  database: string;
  detector: string;
  model: string;
  version: string;
};

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main>
      <h1>Quire</h1>
      <p className="tagline">
        A prepared redaction review for FOI requests against hospital clinical
        records.
      </p>

      <h2>Stack</h2>
      {error && <p className="bad">API unreachable: {error}</p>}
      {!health && !error && <p className="muted">Checking services…</p>}
      {health && (
        <dl>
          <dt>API</dt>
          <dd className="ok">v{health.version}</dd>
          <dt>Database</dt>
          <dd className={health.database === "ok" ? "ok" : "bad"}>
            {health.database}
          </dd>
          <dt>Detector</dt>
          <dd className={health.detector === "ok" ? "ok" : "bad"}>
            {health.detector}
          </dd>
          <dt>Model</dt>
          <dd className="muted">{health.model}</dd>
        </dl>
      )}

      <h2>Not built yet</h2>
      <p className="muted">
        The review surface — page render with a bounding-box overlay, subtractive
        accept/reject, and the proposed ground visible on every span — is the next
        piece of work. This page exists to prove the three services talk to each
        other.
      </p>
    </main>
  );
}
