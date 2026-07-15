import { useState } from 'react';
import { ExtractedTextPreview } from '../components/ExtractedTextPreview/ExtractedTextPreview';
import { FileUpload } from '../components/FileUpload/FileUpload';
import { RangeSelector } from '../components/RangeSelector/RangeSelector';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { analyzeFile, previewRange, uploadFile } from '../services/fileService';
import { saveAnalysisHistory } from '../services/analysisHistoryService';
import type { AnalysisResult, UeItem, UploadedFileInfo } from '../types';
import { normalizeEntries, uploadedFileFromInfo, type WorkflowState } from '../state/workflowState';

export function FileAnalysisPage({
  setPage,
  workflow,
  setWorkflow,
}: {
  setPage: (page: string) => void;
  workflow: WorkflowState;
  setWorkflow: (patch: Partial<WorkflowState>) => void;
}) {
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [selection, setSelection] = useState(workflow.selectedRange);
  const [preview, setPreview] = useState({ text: '', length: 0 });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [items, setItems] = useState<UeItem[]>(workflow.generatedEntries.map((entry) => ({ number: entry.number, content: entry.content, formats: entry.formats })));
  const [message, setMessage] = useState('');
  const canAnalyze = Boolean(workflow.selectedClassbook && file && selection.trim());
  const canGoReview = items.length === 9 && items.every((item) => item.content.trim());

  if (!workflow.selectedClassbook) {
    return (
      <section className="panel">
        <h1>Kein Klassenbuch ausgewaehlt</h1>
        <p>Bitte waehlen Sie zuerst unter Klassenbuecher ein bearbeitbares Klassenbuch aus.</p>
        <button className="primary" onClick={() => setPage('klassenbuch')}>Zu den Klassenbuechern</button>
      </section>
    );
  }

  const selectedBook = workflow.selectedClassbook;

  async function onFile(next: File) {
    const result = await uploadFile(next);
    if (result.ok) {
      setFile(result.data);
      setWorkflow({ uploadedFile: uploadedFileFromInfo(result.data) });
    }
    setMessage(result.message);
  }

  async function loadPreview() {
    if (!file || !selection.trim()) return;
    const result = await previewRange(file.file_id, file.filename, selection);
    setPreview({ text: result.text_preview, length: result.text_length });
    setWorkflow({ selectedRange: selection });
  }

  async function analyze() {
    if (!canAnalyze || !file) return;
    const result = await analyzeFile(file.file_id, file.filename, selection);
    const nextItems = Array.from({ length: 9 }, (_, index) => {
      const source = result.ue_items[index];
      return {
        number: index + 1,
        content: source?.content || `UE ${index + 1}: Bitte Thema ergaenzen.`,
        formats: source?.formats?.length ? source.formats.slice(0, 2) : ['Aufgaben-/Uebungsbesprechung', 'betreute Einzelarbeit'],
      };
    });
    setAnalysis(result);
    setItems(nextItems);
    setWorkflow({
      uploadedFile: uploadedFileFromInfo(file),
      selectedRange: selection,
      analysisResult: result,
      generatedEntries: normalizeEntries(nextItems),
      analysisDone: true,
      reviewConfirmed: false,
      signatureReady: false,
      reviewDone: false,
      currentStep: 'analysis',
    });
    await saveAnalysisHistory({ ...result, filename: file.filename, selection });
  }

  function updateItems(nextItems: UeItem[]) {
    setItems(nextItems);
    setWorkflow({ generatedEntries: normalizeEntries(nextItems), analysisDone: nextItems.length === 9 && nextItems.every((item) => item.content.trim()), reviewConfirmed: false, signatureReady: false, reviewDone: false });
  }

  function goReview() {
    if (!canGoReview) return;
    setWorkflow({ generatedEntries: normalizeEntries(items), analysisDone: true, currentStep: 'review' });
    setPage('review');
  }

  function resetSelection() {
    setWorkflow({
      selectedClassbook: null,
      uploadedFile: null,
      selectedRange: '',
      analysisResult: null,
      generatedEntries: [],
      analysisDone: false,
      reviewConfirmed: false,
      signatureReady: false,
      reviewDone: false,
      currentStep: 'classbooks',
    });
    setPage('klassenbuch');
  }

  return (
    <>
      <section className="panel">
        <h1>Datei & Analyse</h1>
        <h2>Ausgewaehltes Klassenbuch</h2>
        <div className="small-cards">
          <div><span>Titel</span><strong>{selectedBook.titel || selectedBook.title || selectedBook.raw || '-'}</strong></div>
          <div><span>Nummer</span><strong>{selectedBook.nummer || selectedBook.number || '-'}</strong></div>
          <div><span>Datum</span><strong>{selectedBook.datum || selectedBook.date || '-'}</strong></div>
          <div><span>Raum</span><strong>{selectedBook.raum || '-'}</strong></div>
          <div><span>Status</span><strong>{selectedBook.status || '-'}</strong></div>
          <div><span>Tab/Gruppe</span><strong>{selectedBook.tab || '-'}</strong></div>
          <div><span>Einsatzzeit von</span><strong>{selectedBook.einsatzzeit_von || selectedBook.beginn || '-'}</strong></div>
          <div><span>Einsatzzeit bis</span><strong>{selectedBook.einsatzzeit_bis || selectedBook.ende || '-'}</strong></div>
        </div>
        {workflow.selectedClassbook && workflow.uploadedFile && <div className="banner info">Aus vorheriger Sitzung wiederhergestellt.</div>}
        <div className="actions">
          <button className="secondary" onClick={() => setPage('klassenbuch')}>Anderes Klassenbuch auswaehlen</button>
          <button className="secondary" onClick={resetSelection}>Auswahl zuruecksetzen</button>
        </div>
        <FileUpload onFile={onFile} />
        {message && <div className="banner info">{message}</div>}
        {file && (
          <>
            <RangeSelector value={selection} onChange={setSelection} unit={file.unit_label} />
            {!selection.trim() && <div className="banner warning">Bitte geben Sie die Folien-/Seitenrange ein, bevor die KI-Analyse gestartet wird.</div>}
            <div className="actions">
              <button className="secondary" disabled={!selection.trim()} onClick={loadPreview}>Vorschau laden</button>
              <button className="primary" disabled={!canAnalyze} onClick={analyze}>KI-Analyse starten</button>
            </div>
          </>
        )}
        {!file && <div className="banner info">Bitte laden Sie zuerst eine Datei hoch.</div>}
      </section>
      <ExtractedTextPreview text={preview.text} length={preview.length} />
      {analysis && (
        <section className="panel">
          <h2>KI-Ergebnis</h2>
          <p>Es wurden {items.length} UE-Eintraege erzeugt.</p>
        </section>
      )}
      {items.length > 0 && (
        <>
          <UeEditor items={items} onChange={updateItems} />
          <div className="actions">
            <button className="primary" disabled={!canGoReview} onClick={goReview}>Zur Review</button>
          </div>
        </>
      )}
    </>
  );
}
