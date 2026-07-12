export function ExtractedTextPreview({ text, length }: { text: string; length: number }) {
  return (
    <section className="panel">
      <h2>Textvorschau</h2>
      <p className="muted">Extrahierter Umfang: {length} Zeichen</p>
      <pre className="preview">{text || 'Noch keine Vorschau geladen.'}</pre>
    </section>
  );
}
