import { useEffect, useState } from 'react';
import { ErrorReportButton } from '../components/ErrorReportButton/ErrorReportButton';
import { NotificationBanner } from '../components/NotificationBanner/NotificationBanner';
import { StatusCard } from '../components/StatusCard/StatusCard';
import { StepTimeline } from '../components/StepTimeline/StepTimeline';
import { getStatus } from '../services/statusService';
import type { AppStatus } from '../types';

export function DashboardPage({ setPage }: { setPage: (page: string) => void }) {
  const [status, setStatus] = useState<AppStatus | null>(null);
  useEffect(() => {
    getStatus().then(setStatus);
  }, []);
  if (!status) return <p>Lade Status...</p>;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p>Lokales Automatisierungstool fuer Klassenbuch und Zeiterfassung</p>
        </div>
        <ErrorReportButton />
      </div>
      <NotificationBanner message={status.blocked ? status.blocked_reason : status.mode === 'dry-run' ? 'Dry-Run-Modus aktiv' : ''} tone={status.blocked ? 'warning' : 'info'} />
      <div className="cards">
        <StatusCard label="RUN_ID" value={status.run_id} />
        <StatusCard label="Modus" value={status.mode} tone={status.mode === 'dry-run' ? 'orange' : 'green'} />
        <StatusCard label="AUTO_SUBMIT" value={status.auto_submit ? 'true' : 'false'} />
        <StatusCard label="Zieltag" value={status.target_date ?? '-'} />
      </div>
      <section className="panel">
        <div className="progress"><span style={{ width: `${status.progress}%` }} /></div>
        <StepTimeline steps={status.steps} />
      </section>
      <section className="actions">
        <button className="primary" onClick={() => setPage('klassenbuch')}>Datei hochladen</button>
        <button className="secondary" onClick={() => setPage('klassenbuch')}>Klassenbuch vorbereiten</button>
        <button className="secondary" onClick={() => setPage('timebutler')}>Zeiterfassung vorbereiten</button>
        <button className="secondary" onClick={() => setPage('review')}>Zur Review</button>
      </section>
    </>
  );
}
