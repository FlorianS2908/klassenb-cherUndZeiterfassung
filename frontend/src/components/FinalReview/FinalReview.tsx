export function FinalReview({ data, autoSubmit, confirmed, onConfirmed }: { data: unknown; autoSubmit: boolean; confirmed: boolean; onConfirmed: (value: boolean) => void }) {
  return (
    <section className="panel">
      <h2>Finale Review</h2>
      <div className={`banner ${autoSubmit ? 'warning' : 'info'}`}>{autoSubmit ? 'Produktivaktion kann nach Bestaetigung erlaubt werden.' : 'AUTO_SUBMIT=false: finale Aktionen bleiben deaktiviert.'}</div>
      <pre className="preview">{JSON.stringify(data, null, 2)}</pre>
      <label className="checkline">
        <input type="checkbox" checked={confirmed} onChange={(event) => onConfirmed(event.target.checked)} />
        Ich habe die Daten geprueft
      </label>
      <button className="primary" disabled={!autoSubmit || !confirmed}>Final bestaetigen und speichern</button>
    </section>
  );
}
