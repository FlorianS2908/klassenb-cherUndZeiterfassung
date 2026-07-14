import { useEffect, useState, type ReactNode } from 'react';

export function AppErrorBoundary({ children, resetKey, setPage }: { children: ReactNode; resetKey: string; setPage: (page: string) => void }) {
  const [error, setError] = useState('');

  useEffect(() => {
    setError('');
  }, [resetKey]);

  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      setError(event.message || 'Unerwarteter Frontend-Fehler');
    };
    const onRejection = (event: PromiseRejectionEvent) => {
      setError(String(event.reason?.message ?? event.reason ?? 'Unerwarteter Frontend-Fehler'));
    };
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);

  if (!error) return children;
  return (
    <section className="panel">
      <h1>Ein Fehler ist aufgetreten</h1>
      <p>Die Ansicht konnte nicht geladen werden. Du kannst zur Startseite wechseln oder die letzte Diagnose oeffnen.</p>
      <div className="actions">
        <button className="primary" onClick={() => setPage('dashboard')}>Zur Startseite</button>
        <button className="secondary" onClick={() => setPage('klassenbuch')}>Letzte Diagnose oeffnen</button>
      </div>
      <details>
        <summary>Technische Details</summary>
        <pre>{error}</pre>
      </details>
    </section>
  );
}
