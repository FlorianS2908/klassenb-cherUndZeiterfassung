import { useEffect, useState } from 'react';
import { ExtractedTextPreview } from '../components/ExtractedTextPreview/ExtractedTextPreview';
import { FileUpload } from '../components/FileUpload/FileUpload';
import { RangeSelector } from '../components/RangeSelector/RangeSelector';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { analyzeFile, getOpenAiStatus, previewRange, uploadFile } from '../services/fileService';
import { saveAnalysisHistory } from '../services/analysisHistoryService';
import { diagnosticFileUrl, getLatestKlassenbuchDiagnostics } from '../services/diagnosticsService';
import { getOpenKlassenbuecher, prepareKlassenbuch } from '../services/klassenbuchService';
import type { AnalysisResult, KlassenbuchDiagnostics, KlassenbuchEntry, UeItem, UploadedFileInfo } from '../types';
import { ApiError } from '../services/api';

const KLASSENBUCH_GROUPS = [
  'offene Themendokumentationen',
  'Überfällige Themendokumentationen',
  'Freigegebene Themendokumentationen',
  'Korrektur notwendig',
];

function groupKlassenbuecher(items: KlassenbuchEntry[], groups?: Record<string, KlassenbuchEntry[]>) {
  const grouped = Object.fromEntries(KLASSENBUCH_GROUPS.map((name) => [name, groups?.[name] ?? []])) as Record<string, KlassenbuchEntry[]>;
  if (!groups) {
    for (const item of items) {
      const tab = item.tab && KLASSENBUCH_GROUPS.includes(item.tab) ? item.tab : 'offene Themendokumentationen';
      grouped[tab].push(item);
    }
  }
  return grouped;
}

function klassenbuchError(error: unknown): { message: string; diagnostics: KlassenbuchDiagnostics | null } {
  if (error instanceof ApiError) {
    const data = error.data as { message?: string; diagnostics?: KlassenbuchDiagnostics; exception_type?: string };
    return {
      message: data.message ?? error.message,
      diagnostics: data.diagnostics ? { ...data.diagnostics, exception_type: data.exception_type ?? data.diagnostics.exception_type } : null,
    };
  }
  if (error instanceof Error) return { message: error.message, diagnostics: null };
  return { message: String(error), diagnostics: null };
}

function fileName(path?: string) {
  if (!path) return '';
  return path.replace(/\\/g, '/').split('/').pop() ?? '';
}

function DiagnosticLinks({ diagnostics }: { diagnostics: KlassenbuchDiagnostics }) {
  const runId = diagnostics.run_id;
  const links = [
    ['Screenshot', diagnostics.screenshot_path || diagnostics.screenshots?.[diagnostics.screenshots.length - 1]],
    ['HTML-Snapshot', diagnostics.html_snapshot_path || diagnostics.html_snapshots?.[diagnostics.html_snapshots.length - 1]],
    ['Console-Log', diagnostics.console_log],
    ['Network-Log', diagnostics.network_log],
    ['Playwright Trace', diagnostics.trace_path || diagnostics.trace_file],
  ];
  if (!runId) return null;
  return (
    <div className="actions">
      {links.map(([label, path]) => {
        const name = fileName(path);
        return name ? <a className="secondary" key={label} href={diagnosticFileUrl(runId, name)} target="_blank" rel="noreferrer">{label}</a> : null;
      })}
    </div>
  );
}

export function KlassenbuchPage() {
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [selection, setSelection] = useState('');
  const [preview, setPreview] = useState({ text: '', length: 0 });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [items, setItems] = useState<UeItem[]>([]);
  const [message, setMessage] = useState('');
  const [openAi, setOpenAi] = useState<{ active: boolean; key_present: boolean; source: string; message: string; display_path: string; model: string; max_input_chars: number } | null>(null);
  const [openBooks, setOpenBooks] = useState<KlassenbuchEntry[]>([]);
  const [bookGroups, setBookGroups] = useState<Record<string, KlassenbuchEntry[]>>(groupKlassenbuecher([]));
  const [bookDiagnostics, setBookDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);
  const [selectedBook, setSelectedBook] = useState<KlassenbuchEntry | null>(null);
  const [webRunMessage, setWebRunMessage] = useState('');
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [latestDiagnostics, setLatestDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);

  useEffect(() => {
    getOpenAiStatus().then(setOpenAi);
    getLatestKlassenbuchDiagnostics().then((result) => setLatestDiagnostics(result as KlassenbuchDiagnostics)).catch(() => undefined);
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

  async function loadOpenBooks() {
    setLoadingBooks(true);
    setWebRunMessage('');
    try {
      const result = await getOpenKlassenbuecher();
      setOpenBooks(result.items);
      setBookGroups(groupKlassenbuecher(result.items, result.groups));
      setBookDiagnostics(result.diagnostics ?? null);
      setLatestDiagnostics((result.diagnostics ?? null) as KlassenbuchDiagnostics | null);
      setWebRunMessage(`${result.count ?? result.items.length} Klassenbuecher geladen.`);
    } catch (error) {
      const parsedError = klassenbuchError(error);
      setOpenBooks([]);
      setBookGroups(groupKlassenbuecher([]));
      setBookDiagnostics(parsedError.diagnostics);
      setLatestDiagnostics(parsedError.diagnostics);
      setWebRunMessage(`Klassenbuecher konnten nicht geladen werden: ${parsedError.message}`);
    } finally {
      setLoadingBooks(false);
    }
  }

  async function prepareSelectedBook() {
    if (!selectedBook || items.length !== 9) {
      setWebRunMessage('Bitte zuerst ein Klassenbuch auswaehlen und genau 9 UE erzeugen.');
      return;
    }
    const result = await prepareKlassenbuch({
      klassenbuch: selectedBook,
      ue_items: items,
      file: file?.filename,
      selected_range: selection,
    });
    setWebRunMessage(JSON.stringify(result, null, 2));
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
      <section className="panel">
        <div className="page-head">
          <h2>Klassenbuecher</h2>
          <button className="secondary" onClick={loadOpenBooks} disabled={loadingBooks}>{loadingBooks ? 'Laedt...' : 'Klassenbuecher laden'}</button>
        </div>
        {webRunMessage && <div className="banner info">{webRunMessage}</div>}
        {openBooks.length === 0 && bookDiagnostics && (
          <div className="banner warning">
            <strong>Keine Klassenbuecher gefunden. Diagnose anzeigen.</strong>
            <p>Bitte pruefen: Login erfolgreich? Richtige URL? Tabelle geladen?</p>
            <p>Schritt: {bookDiagnostics.step || '-'}</p>
            <p>Fehlertyp: {bookDiagnostics.exception_type || '-'}</p>
            <p>URL: {bookDiagnostics.current_url || '-'}</p>
            <p>Titel: {bookDiagnostics.page_title || '-'}</p>
            <p>Tabs: {(bookDiagnostics.tabs_found ?? bookDiagnostics.tab_names_found)?.join(', ') || '-'}</p>
            <p>Tabellen: {bookDiagnostics.table_count ?? 0} · Zeilen: {bookDiagnostics.row_count ?? 0}</p>
            <p>Diagnoseordner: {bookDiagnostics.diagnostics_folder || '-'}</p>
            {bookDiagnostics.screenshot_path && <p>Screenshot: {bookDiagnostics.screenshot_path}</p>}
            {bookDiagnostics.html_snapshot_path && <p>HTML-Snapshot: {bookDiagnostics.html_snapshot_path}</p>}
            <DiagnosticLinks diagnostics={bookDiagnostics} />
            {bookDiagnostics.tab_errors && bookDiagnostics.tab_errors.length > 0 && (
              <ul>
                {bookDiagnostics.tab_errors.map((tabError, index) => (
                  <li key={`${tabError.tab ?? 'tab'}-${index}`}>{tabError.tab}: {tabError.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {KLASSENBUCH_GROUPS.map((groupName) => {
          const groupItems = bookGroups[groupName] ?? [];
          return (
            <div className="table-panel" key={groupName}>
              <h3>{groupName} ({groupItems.length})</h3>
              <table>
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Status</th>
                    <th>Nummer</th>
                    <th>Titel</th>
                    <th>Raum</th>
                    <th>Beginn</th>
                    <th>Ende</th>
                    <th>Einsatzzeit</th>
                    <th>Bearbeitbar</th>
                    <th>Aktion</th>
                  </tr>
                </thead>
                <tbody>
                  {groupItems.map((book) => (
                    <tr key={book.id}>
                      <td>{book.datum || book.date || '-'}</td>
                      <td>{book.status || '-'}</td>
                      <td>{book.nummer || book.number || '-'}</td>
                      <td>{book.titel || book.title || book.raw || '-'}</td>
                      <td>{book.raum || '-'}</td>
                      <td>{book.beginn || '-'}</td>
                      <td>{book.ende || '-'}</td>
                      <td>{book.einsatzzeit_von || '-'} - {book.einsatzzeit_bis || '-'}</td>
                      <td>{book.editable ? 'ja' : 'nein'}</td>
                      <td><button className="secondary" onClick={() => setSelectedBook(book)}>Auswaehlen</button></td>
                    </tr>
                  ))}
                  {groupItems.length === 0 && <tr><td colSpan={10}>Keine Eintraege in dieser Gruppe.</td></tr>}
                </tbody>
              </table>
            </div>
          );
        })}
        <div className="actions">
          <button className="primary" onClick={prepareSelectedBook} disabled={!selectedBook || items.length !== 9}>Dry-Run Klassenbuch vorbereiten</button>
        </div>
      </section>
      <section className="panel">
        <div className="page-head">
          <h2>Diagnose</h2>
          <button className="secondary" onClick={() => getLatestKlassenbuchDiagnostics().then((result) => setLatestDiagnostics(result as KlassenbuchDiagnostics))}>Letzte Diagnose oeffnen</button>
        </div>
        {latestDiagnostics?.run_id ? (
          <div className="banner info">
            <p><strong>Letzter Klassenbuch-Lauf:</strong> {latestDiagnostics.run_id}</p>
            <p>Ergebnis: {latestDiagnostics.success ? 'Erfolg' : 'Fehler'} · Eintraege: {latestDiagnostics.entries_returned ?? '-'}</p>
            <p>Fehler: {latestDiagnostics.error_message || '-'}</p>
            <p>Schritt: {latestDiagnostics.step || '-'}</p>
            <p>URL: {latestDiagnostics.current_url || '-'}</p>
            <p>Titel: {latestDiagnostics.page_title || '-'}</p>
            <p>Tabellen: {latestDiagnostics.table_count ?? latestDiagnostics.tables_found ?? '-'} · Zeilen: {latestDiagnostics.row_count ?? latestDiagnostics.rows_found ?? '-'}</p>
            <p>Diagnoseordner: {latestDiagnostics.diagnostics_folder || '-'}</p>
            <DiagnosticLinks diagnostics={latestDiagnostics} />
          </div>
        ) : <p className="muted">Noch kein Klassenbuch-Diagnoselauf vorhanden.</p>}
      </section>
    </>
  );
}
