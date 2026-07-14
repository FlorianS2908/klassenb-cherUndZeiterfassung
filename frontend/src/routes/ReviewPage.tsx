import { useEffect, useState } from 'react';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { prepareKlassenbuch, prepareKlassenbuchSignature, submitKlassenbuch } from '../services/klassenbuchService';
import { getStatus } from '../services/statusService';
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
  const [signatureConfirmed, setSignatureConfirmed] = useState(false);
  const [signaturePrepared, setSignaturePrepared] = useState(false);
  const [signatureScreenshot, setSignatureScreenshot] = useState('');
  const [autoSubmit, setAutoSubmit] = useState(false);
  const [message, setMessage] = useState('');
  const ready = Boolean(workflow.selectedClassbook && workflow.analysisDone && workflow.generatedEntries.length === 9);
  const payload = {
    klassenbuch: workflow.selectedClassbook,
    classbook: workflow.selectedClassbook,
    ue_items: items,
    entries: items,
    file: workflow.uploadedFile?.name,
    selected_range: workflow.selectedRange,
  };

  useEffect(() => {
    getStatus().then((status) => setAutoSubmit(status.auto_submit)).catch(() => setAutoSubmit(false));
  }, []);

  function updateItems(nextItems: UeItem[]) {
    setItems(nextItems);
    setWorkflow({ generatedEntries: normalizeEntries(nextItems), analysisDone: nextItems.length === 9 });
  }

  async function prepareReview() {
    if (!workflow.selectedClassbook || items.length !== 9 || !reviewed) return;
    setMessage('Klassenbuch-Eintrag wird vorbereitet ...');
    const result = await prepareKlassenbuch({ ...payload, review_confirmed: true });
    setWorkflow({ generatedEntries: normalizeEntries(items), reviewDone: true, currentStep: 'submit_done' });
    setMessage(JSON.stringify(result, null, 2));
  }

  async function prepareSignature() {
    if (!workflow.selectedClassbook || items.length !== 9 || !reviewed) return;
    setMessage('Signatur wird vorbereitet ...');
    const result = await prepareKlassenbuchSignature(payload, reviewed);
    setWorkflow({ generatedEntries: normalizeEntries(items), reviewDone: true });
    setSignaturePrepared(Boolean((result as { ok?: boolean }).ok));
    const data = (result as { data?: { screenshot?: string } }).data;
    setSignatureScreenshot(data?.screenshot || '');
    setMessage(JSON.stringify(result, null, 2));
  }

  async function finalizeSignature() {
    if (!workflow.selectedClassbook || items.length !== 9 || !reviewed || !signaturePrepared || !signatureConfirmed || !autoSubmit) return;
    setMessage('Finale Signatur wird ausgefuehrt ...');
    const result = await submitKlassenbuch(payload, reviewed, signatureConfirmed);
    setWorkflow({ generatedEntries: normalizeEntries(items), reviewDone: Boolean((result as { ok?: boolean }).ok), currentStep: 'submit_done' });
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
          Ich habe die 9 UE geprueft.
        </label>
        <label className="check-row">
          <input type="checkbox" checked={signatureConfirmed} onChange={(event) => setSignatureConfirmed(event.target.checked)} />
          Ich bestaetige, dass diese Signatur final verwendet werden darf.
        </label>
        {signaturePrepared && <div className="banner info">Signatur wurde in das Klassenbuch-Canvas eingetragen.</div>}
        {signatureScreenshot && <div className="banner info">Screenshot nach Signatur: {signatureScreenshot}</div>}
        {!autoSubmit && <div className="banner warning">Final signieren ist deaktiviert, weil AUTO_SUBMIT nicht aktiv ist.</div>}
        <div className="actions">
          <button className="secondary" onClick={() => setPage('analysis')}>Zurueck zur Analyse</button>
          <button className="secondary" disabled={!reviewed || items.length !== 9} onClick={prepareReview}>Klassenbuch vorbereiten</button>
          <button className="secondary" disabled={!reviewed || items.length !== 9} onClick={prepareSignature}>Signatur vorbereiten</button>
          <button className="primary" disabled={!reviewed || !signaturePrepared || !signatureConfirmed || !autoSubmit || items.length !== 9} onClick={finalizeSignature}>Final signieren</button>
        </div>
        {message && <pre className="output">{message}</pre>}
      </section>
    </>
  );
}
