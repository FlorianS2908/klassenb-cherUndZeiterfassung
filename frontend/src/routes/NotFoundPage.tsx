export function NotFoundPage({ setPage }: { setPage: (page: string) => void }) {
  return (
    <section className="panel">
      <h1>Seite nicht gefunden</h1>
      <p>Diese Ansicht existiert im Tool nicht.</p>
      <div className="actions">
        <button className="primary" onClick={() => setPage('dashboard')}>Zur Startseite</button>
        <button className="secondary" onClick={() => setPage('setup')}>Zum Setup</button>
      </div>
    </section>
  );
}
