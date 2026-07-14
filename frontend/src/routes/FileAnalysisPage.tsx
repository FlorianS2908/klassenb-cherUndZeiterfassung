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

  if (!workflow.selectedClassbook) {
    return (
      <section className="panel">
        <h1>Kein Klassenbuch ausgewaehlt</h1>
        <p>Bitte zuerst ein Klassenbuch auswaehlen.</p>
        <button className="primary" onClick={() => setPage('klassenbuch')}>Zu den Klassenbuechern</button>
      </section>
    );
  }

  async function onFile(next: File) {
    const result = await uploadFile(next);
    if (result.ok) {
      setFile(result.data);
      setWorkflow({ uploadedFile: uploadedFileFromInfo(result.data) });
    }
    setMessage(result.message);
  }

  async function loadPreview() {
    if (!file) return;
    const result = await previewRange(file.file_id, file.filename, selection);
    setPreview({ text: result.text_preview, length: result.text_length });
    setWorkflow({ selectedRange: selection });
  }

  async function analyze() {
    if (!file) return;
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
    setWorkflow({ uploadedFile: uploadedFileFromInfo(file), selectedRange: selection, generatedEntries: normalizeEntries(nextItems), analysisDone: true });
    await saveAnalysisHistory({ ...result, filename: file.filename, selection });
  }

  function updateItems(nextItems: UeItem[]) {
    setItems(nextItems);
    setWorkflow({ generatedEntries: normalizeEntries(nextItems), analysisDone: nextItems.length === 9 });
  }

  function goReview() {
    setWorkflow({ generatedEntries: normalizeEntries(items), analysisDone: true, currentStep: 'review' });
    setPage('review');
  }

  return (
    <>
      <section className="panel">
        <h1>Datei & Analyse</h1>
        <div className="small-cards">
          <div><span>Ausgewaehltes Klassenbuch</span><strong>{workflow.selectedClassbook.titel || workflow.selectedClassbook.title || workflow.selectedClassbook.raw || '-'}</strong></div>
          <div><span>Nummer</span><strong>{workflow.selectedClassbook.nummer || workflow.selectedClassbook.number || '-'}</strong></div>
          <div><span>Datum</span><strong>{workflow.selectedClassbook.datum || workflow.selectedClassbook.date || '-'}</strong></div>
          <div><span>Raum</span><strong>{workflow.selectedClassbook.raum || '-'}</strong></div>
        </div>
        <FileUpload onFile={onFile} />
        {message && <div className="banner info">{message}</div>}
        {file && (
          <>
            <RangeSelector value={selection} onChange={setSelection} unit={file.unit_label} />
            <div className="actions">
              <button className="secondary" onClick={loadPreview}>Vorschau laden</button>
              <button className="primary" onClick={analyze}>KI-Analyse starten</button>
            </div>
          </>
        )}
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
            <button className="primary" disabled={items.length !== 9} onClick={goReview}>Zur Review</button>
          </div>
        </>
      )}
    </>
  );
}
