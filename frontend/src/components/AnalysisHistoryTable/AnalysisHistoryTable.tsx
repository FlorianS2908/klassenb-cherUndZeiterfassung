import type { AnalysisHistoryItem } from '../../services/analysisHistoryService';

export function AnalysisHistoryTable({ items, onReopen, onDelete }: { items: AnalysisHistoryItem[]; onReopen: (id: string) => void; onDelete: (id: string) => void }) {
  return (
    <section className="panel table-panel">
      <table>
        <thead>
          <tr>
            <th>Gespeichert</th>
            <th>Datei</th>
            <th>Bereich</th>
            <th>Confidence</th>
            <th>Aktion</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.saved_at ?? '-'}</td>
              <td>{item.filename ?? '-'}</td>
              <td>{item.selection || 'gesamte Datei'}</td>
              <td>{item.confidence_score == null ? '-' : `${Math.round(item.confidence_score * 100)}%`}</td>
              <td>
                <div className="actions compact">
                  <button className="secondary" onClick={() => onReopen(item.id)}>Oeffnen</button>
                  <button className="secondary" onClick={() => onDelete(item.id)}>Loeschen</button>
                </div>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={5}>Noch keine gespeicherten Analysen.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
