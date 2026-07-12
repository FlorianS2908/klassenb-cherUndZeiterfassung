import { useEffect, useState } from 'react';
import { ExtractedTextPreview } from '../components/ExtractedTextPreview/ExtractedTextPreview';
import { FileUpload } from '../components/FileUpload/FileUpload';
import { RangeSelector } from '../components/RangeSelector/RangeSelector';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { analyzeFile, getOpenAiStatus, previewRange, uploadFile } from '../services/fileService';
import { saveAnalysisHistory } from '../services/analysisHistoryService';
import type { AnalysisResult, UeItem, UploadedFileInfo } from '../types';

export function KlassenbuchPage() {
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [selection, setSelection] = useState('');
  const [preview, setPreview] = useState({ text: '', length: 0 });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [items, setItems] = useState<UeItem[]>([]);
  const [message, setMessage] = useState('');
  const [openAi, setOpenAi] = useState<{ active: boolean; key_present: boolean; source: string; message: string; display_path: string; model: string; max_input_chars: number } | null>(null);

  useEffect(() => {
    getOpenAiStatus().then(setOpenAi);
  }, []);

  async function onFile(next: File) {
    const result = await uploadFile(next);
    if (result.ok) setFile(result.data);
    setMessage(result.message);
  }

  async function loadPreview() {
    if (!file) return;
    const result = await previewRange(file.file_id, file.filename, selection);
    setPreview({ text: result.text_preview, length: result.text_length });
  }

  async function analyze() {
    if (!file) return;
    const result = await analyzeFile(file.file_id, file.filename, selection);
    setAnalysis(result);
    setItems(result.ue_items);
    await saveAnalysisHistory({ ...result, filename: file.filename, selection });
  }

  return (
    <>
      <div className="page-head"><h1>Klassenbuch</h1></div>
      <FileUpload onFile={onFile} />
      {message && <div className="banner info">{message}</div>}
      {file && (
        <section className="panel">
          <h2>{file.filename}</h2>
          <p>{file.file_type}: {file.total_items} {file.unit_label}</p>
          <RangeSelector value={selection} onChange={setSelection} unit={file.unit_label} />
          <div className="actions">
            <button className="secondary" onClick={loadPreview}>Vorschau laden</button>
            <button className="primary" onClick={analyze}>Analyse starten</button>
          </div>
        </section>
      )}
      <section className="panel">
        <h2>KI-Status</h2>
        <div className="cards small-cards">
          <div><span>OpenAI API aktiv</span><strong>{openAi?.active ? 'ja' : 'nein'}</strong></div>
          <div><span>API-Key vorhanden</span><strong>{openAi?.key_present ? 'ja' : 'nein'}</strong></div>
          <div><span>Quelle</span><strong>{openAi?.source ?? '-'}</strong></div>
          <div><span>Modell</span><strong>{openAi?.model ?? '-'}</strong></div>
        </div>
        {openAi && !openAi.active && <div className="banner warning">{openAi.message}</div>}
        {openAi?.display_path && <p className="muted">Key-Datei: {openAi.display_path}</p>}
        <div className="actions">
          <button className="primary" disabled={!file || !openAi?.active} onClick={analyze}>KI-Analyse starten</button>
          <button className="secondary" disabled={!file || !openAi?.active} onClick={analyze}>KI-Ergebnis neu generieren</button>
          <button className="secondary" disabled={!file} onClick={analyze}>Manuell ohne KI fortfahren</button>
        </div>
      </section>
      <ExtractedTextPreview text={preview.text} length={preview.length} />
      {analysis && (
        <section className="panel">
          <h2>Erkannte Themen</h2>
          <p>Confidence: {(analysis.confidence_score * 100).toFixed(0)}%</p>
          <p>KI verwendet: {analysis.ai_used ? 'ja' : 'nein'} · Modell: {analysis.ai_model || '-'}</p>
          {analysis.ai_truncated && <div className="banner warning">Extrahierter Text wurde vor der KI-Analyse gekuerzt.</div>}
          {analysis.ai_warnings.length > 0 && <div className="banner warning">{analysis.ai_warnings.join(' ')}</div>}
          <p>Ausgewertet: {analysis.range.selected.join(', ')}</p>
          <p>Der Analyse-Lauf wurde in der Historie gespeichert.</p>
          <div className="chips">{analysis.topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
        </section>
      )}
      {items.length > 0 && <UeEditor items={items} onChange={setItems} />}
    </>
  );
}
