export function FinalReview({
  data,
  autoSubmit,
  confirmed,
  signatureConfirmed,
  signatureValue,
  signatureMode,
  onConfirmed,
  onSignatureConfirmed,
}: {
  data: unknown;
  autoSubmit: boolean;
  confirmed: boolean;
  signatureConfirmed: boolean;
  signatureValue: string;
  signatureMode: 'Dry-Run' | 'Produktiv';
  onConfirmed: (value: boolean) => void;
  onSignatureConfirmed: (value: boolean) => void;
}) {
  return (
    <section className="panel">
      <h2>Finale Review</h2>
      <div className={`banner ${autoSubmit ? 'warning' : 'info'}`}>{autoSubmit ? 'Produktivaktion kann nach Bestaetigung erlaubt werden.' : 'AUTO_SUBMIT=false: finale Aktionen bleiben deaktiviert.'}</div>
      <div className="small-cards">
        <div><span>Signaturwert</span><strong>{signatureValue || '-'}</strong></div>
        <div><span>Signaturmodus</span><strong>{signatureMode}</strong></div>
      </div>
      <div className="banner info">Die Signatur wird nur nach finaler Bestaetigung gesetzt.</div>
      <pre className="preview">{JSON.stringify(data, null, 2)}</pre>
      <label className="checkline">
        <input type="checkbox" checked={confirmed} onChange={(event) => onConfirmed(event.target.checked)} />
        Ich habe die Daten geprueft
      </label>
      <label className="checkline">
        <input type="checkbox" checked={signatureConfirmed} onChange={(event) => onSignatureConfirmed(event.target.checked)} />
        Ich bestaetige, dass die Klassenbuchdaten korrekt sind und signiert werden duerfen.
      </label>
      <button className="primary" disabled={!autoSubmit || !confirmed || !signatureConfirmed}>Final speichern und signieren</button>
    </section>
  );
}
