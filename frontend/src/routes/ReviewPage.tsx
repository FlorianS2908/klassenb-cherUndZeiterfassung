import { useState } from 'react';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { prepareKlassenbuch } from '../services/klassenbuchService';
import type { UeItem } from '../types';
import { normalizeEntries, type WorkflowEntry, type WorkflowState } from '../state/workflowState';

function toUeItems(entries: WorkflowEntry[]): UeItem[] {
  return entries.map((entry, index) => ({
    number: index + 1,
    content: entry.content,
    formats: entry.formats,
  }));
}

export function ReviewPage({
  setPage,
  workflow,
  setWorkflow,
}: {
  setPage: (page: string) => void;
  workflow: WorkflowState;
  setWorkflow: (patch: Partial<WorkflowState>) => void;
}) {
  const [items, setItems] = useState<UeItem[]>(toUeItems(workflow.generatedEntries));
  const [reviewed, setReviewed] = useState(false);
  const [message, setMessage] = useState('');
  const ready = Boolean(workflow.selectedClassbook && workflow.analysisDone && workflow.generatedEntries.length === 9);

  function updateItems(nextItems: UeItem[]) {
    setItems(nextItems);
    setWorkflow({ generatedEntries: normalizeEntries(nextItems), analysisDone: nextItems.length === 9 });
  }

  async function submitReview() {
    if (!workflow.selectedClassbook || items.length !== 9 || !reviewed) return;
    setMessage('Klassenbuch-Eintrag wird vorbereitet ...');
    const result = await prepareKlassenbuch({
      klassenbuch: workflow.selectedClassbook,
      classbook: workflow.selectedClassbook,
      ue_items: items,
      entries: items,
      file: workflow.uploadedFile?.name,
      selected_range: workflow.selectedRange,
      review_confirmed: true,
    });
    setWorkflow({ generatedEntries: normalizeEntries(items), reviewDone: true, currentStep: 'submit_done' });
    setMessage(JSON.stringify(result, null, 2));
  }

  if (!ready) {
    return (
      <section className="panel">
        <h1>Review noch nicht verfuegbar</h1>
        <p>Bitte zuerst ein Klassenbuch auswaehlen und in der Datei-Analyse genau 9 UE erzeugen.</p>
        <div className="actions">
          <button className="primary" onClick={() => setPage(workflow.selectedClassbook ? 'analysis' : 'klassenbuch')}>Zur Datei & Analyse</button>
        </div>
      </section>
    );
  }

  return (
    <>
      <section className="panel">
        <h1>Review</h1>
        <div className="small-cards">
          <div><span>Klassenbuch</span><strong>{workflow.selectedClassbook?.titel || workflow.selectedClassbook?.title || workflow.selectedClassbook?.raw || '-'}</strong></div>
          <div><span>Datei</span><strong>{workflow.uploadedFile?.name || '-'}</strong></div>
          <div><span>Bereich</span><strong>{workflow.selectedRange || '-'}</strong></div>
          <div><span>UE</span><strong>{items.length}/9</strong></div>
        </div>
      </section>
      <UeEditor items={items} onChange={updateItems} />
      <section className="panel">
        <label className="check-row">
          <input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />
          Ich habe die Eintraege geprueft.
        </label>
        <div className="actions">
          <button className="secondary" onClick={() => setPage('analysis')}>Zurueck zur Analyse</button>
          <button className="primary" disabled={!reviewed || items.length !== 9} onClick={submitReview}>Ins Klassenbuch eintragen</button>
        </div>
        {message && <pre className="output">{message}</pre>}
      </section>
    </>
  );
}
