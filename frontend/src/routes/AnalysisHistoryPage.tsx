import { useEffect, useState } from 'react';
import { AnalysisHistoryTable } from '../components/AnalysisHistoryTable/AnalysisHistoryTable';
import { deleteAnalysisHistory, getAnalysisHistory, type AnalysisHistoryItem } from '../services/analysisHistoryService';

export function AnalysisHistoryPage() {
  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [selected, setSelected] = useState<AnalysisHistoryItem | null>(null);

  async function refresh() {
    const result = await getAnalysisHistory();
    setItems(result.items);
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <>
      <div className="page-head"><h1>Analysehistorie</h1></div>
      <AnalysisHistoryTable
        items={items}
        onReopen={(id) => setSelected(items.find((item) => item.id === id) ?? null)}
        onDelete={async (id) => {
          await deleteAnalysisHistory(id);
          refresh();
        }}
      />
      {selected && (
        <section className="panel">
          <h2>{selected.filename ?? selected.id}</h2>
          <pre className="preview">{JSON.stringify(selected, null, 2)}</pre>
        </section>
      )}
    </>
  );
}
