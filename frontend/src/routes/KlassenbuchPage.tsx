import { useEffect, useState } from 'react';
import { ExtractedTextPreview } from '../components/ExtractedTextPreview/ExtractedTextPreview';
import { FileUpload } from '../components/FileUpload/FileUpload';
import { RangeSelector } from '../components/RangeSelector/RangeSelector';
import { UeEditor } from '../components/UeEditor/UeEditor';
import { analyzeFile, getOpenAiStatus, previewRange, uploadFile } from '../services/fileService';
import { saveAnalysisHistory } from '../services/analysisHistoryService';
import { checkKlassenbuchBrowserHealth, diagnosticFileUrl, exportLatestKlassenbuchDiagnostic, getLatestKlassenbuchDiagnostics } from '../services/diagnosticsService';
import { getOpenKlassenbuecher, prepareKlassenbuch } from '../services/klassenbuchService';
import { getStatus } from '../services/statusService';
import type { AnalysisResult, AppStatus, KlassenbuchDiagnostics, KlassenbuchEntry, UeItem, UploadedFileInfo } from '../types';
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
    ['Summary', diagnostics.summary_path],
    ['Steps', diagnostics.steps_path],
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

function isBrowserStartProblem(diagnostics: KlassenbuchDiagnostics) {
  const text = [
    diagnostics.exception_type,
    diagnostics.error_message,
    diagnostics.message,
    diagnostics.probable_cause,
    diagnostics.step,
  ].join(' ').toLowerCase();

  return diagnostics.step === 'browser_start'
    || text.includes('playwright-browserstart')
    || text.includes('notimplementederror')
    || text.includes('windows asyncio')
    || text.includes('chromium konnte nicht gestartet');
}

function isPlaywrightPythonApiProblem(diagnostics: KlassenbuchDiagnostics) {
  const text = [diagnostics.problem_category, diagnostics.error_message, diagnostics.message, diagnostics.probable_cause].join(' ').toLowerCase();
  return text.includes('playwright_python_api') || (text.includes('locator') && text.includes('not callable'));
}

function DiagnosticStatusCards({ diagnostics }: { diagnostics: KlassenbuchDiagnostics }) {
  const tabsFound = diagnostics.tabs ? Object.values(diagnostics.tabs).filter((tab) => tab.found).length : undefined;
  const cards = [
    ['Browserstart', isBrowserStartProblem(diagnostics) ? 'Fehler' : 'ok/unklar'],
    ['Login', diagnostics.login_success ? 'ok' : 'offen'],
    ['Overview', diagnostics.overview_loaded ? 'ok' : 'offen'],
    ['Tabs', tabsFound ?? '-'],
    ['Tabellen', diagnostics.table_count ?? diagnostics.tables_found ?? '-'],
    ['Zeilen', diagnostics.row_count ?? diagnostics.rows_found ?? '-'],
    ['Eintraege', diagnostics.entries_returned ?? '-'],
  ];
  return <div className="cards small-cards">{cards.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>;
}

export function KlassenbuchPage() {
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [selection, setSelection] = useState('');
  const [preview, setPreview] = useState({ text: '', length: 0 });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [items, setItems] = useState<UeItem[]>([]);
  const [message, setMessage] = useState('');
  const [openAi, setOpenAi] = useState<{ active: boolean; key_present: boolean; source: string; message: string; display_path: string; model: string; max_input_chars: number } | null>(null);
  const [appStatus, setAppStatus] = useState<AppStatus | null>(null);
  const [openBooks, setOpenBooks] = useState<KlassenbuchEntry[]>([]);
  const [bookGroups, setBookGroups] = useState<Record<string, KlassenbuchEntry[]>>(groupKlassenbuecher([]));
  const [bookDiagnostics, setBookDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);
  const [selectedBook, setSelectedBook] = useState<KlassenbuchEntry | null>(null);
  const [webRunMessage, setWebRunMessage] = useState('');
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [latestDiagnostics, setLatestDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);
  const [browserHealth, setBrowserHealth] = useState<Record<string, unknown> | null>(null);
  const [diagnosticExport, setDiagnosticExport] = useState<Record<string, unknown> | null>(null);
  const [exportingDiagnostic, setExportingDiagnostic] = useState(false);

  useEffect(() => {
    getOpenAiStatus().then(setOpenAi);
    getStatus().then(setAppStatus).catch(() => undefined);
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
    setWebRunMessage('Klassenbuecher werden geladen. Login laeuft im Hintergrund ...');
    try {
      const result = await getOpenKlassenbuecher();
      setOpenBooks(result.items);
      setBookGroups(groupKlassenbuecher(result.items, result.groups));
      setBookDiagnostics(result.diagnostics ?? null);
      setLatestDiagnostics((result.diagnostics ?? null) as KlassenbuchDiagnostics | null);
      setWebRunMessage(`${result.count ?? result.items.length} Klassenbuecher geladen.`);
    } catch (error) {
      const parsedError = klassenbuchError(error);
      const lowerMessage = parsedError.message.toLowerCase();
      const friendlyMessage = lowerMessage.includes('zugangsdaten fehlen')
        ? 'Klassenbuch-Zugangsdaten fehlen. Bitte Setup oeffnen oder lokale Credential-Datei anlegen.'
        : lowerMessage.includes('login fehlgeschlagen')
          ? 'Login fehlgeschlagen. Die lokal gespeicherten Zugangsdaten wurden abgelehnt.'
          : parsedError.message;
      setOpenBooks([]);
      setBookGroups(groupKlassenbuecher([]));
      setBookDiagnostics(parsedError.diagnostics);
      setLatestDiagnostics(parsedError.diagnostics);
      setWebRunMessage(`Klassenbuecher konnten nicht geladen werden: ${friendlyMessage}`);
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

  async function openLatestDiagnostics() {
    const result = await getLatestKlassenbuchDiagnostics();
    setLatestDiagnostics(result as KlassenbuchDiagnostics);
    if (!Object.keys(result).length) setWebRunMessage('Noch keine Diagnose vorhanden. Bitte zuerst Klassenbuecher laden.');
  }

  async function runBrowserHealth() {
    const result = await checkKlassenbuchBrowserHealth();
    setBrowserHealth(result);
    const diagnostics = result.diagnostics as KlassenbuchDiagnostics | undefined;
    if (diagnostics) setLatestDiagnostics(diagnostics);
  }

  async function exportSanitizedDiagnostic() {
    setExportingDiagnostic(true);
    try {
      const result = await exportLatestKlassenbuchDiagnostic();
      setDiagnosticExport(result);
      setWebRunMessage(`Fehlerbericht exportiert: ${String(result.export_folder ?? '-')}`);
    } catch (error) {
      setDiagnosticExport(null);
      setWebRunMessage('Noch keine Diagnose vorhanden. Bitte zuerst Klassenbuecher laden.');
    } finally {
      setExportingDiagnostic(false);
    }
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
          <div><span>Browser-Modus</span><strong>{appStatus?.browser_mode ?? '-'}</strong></div>
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
          <div className="actions">
            <button className="secondary" onClick={loadOpenBooks} disabled={loadingBooks}>{loadingBooks ? 'Login laeuft ...' : 'Klassenbuecher laden'}</button>
            <button className="secondary" onClick={openLatestDiagnostics}>Letzte Diagnose oeffnen</button>
            <button className="secondary" onClick={runBrowserHealth}>Browser-Check</button>
          </div>
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
          <button className="secondary" onClick={runBrowserHealth}>Browser-Check ausfuehren</button>
          <button className="secondary" onClick={exportSanitizedDiagnostic} disabled={exportingDiagnostic}>{exportingDiagnostic ? 'Exportiert...' : 'Fehlerbericht fuers Repo exportieren'}</button>
        </div>
        {diagnosticExport?.export_folder && (
          <div className="banner info">
            <p><strong>Sanitisierter Export:</strong> {String(diagnosticExport.export_folder)}</p>
            <p>Bitte nur den Ordner {String(diagnosticExport.export_folder)} committen. Die Rohdaten unter diagnostics/ nicht committen.</p>
          </div>
        )}
        {browserHealth && (
          <div className={browserHealth.ok ? 'banner info' : 'banner warning'}>
            <p><strong>Browser-Check:</strong> {browserHealth.ok ? 'ok' : 'Fehler'} · Schritt: {String(browserHealth.step ?? '-')}</p>
            <p>{String(browserHealth.message ?? '')}</p>
          </div>
        )}
        {latestDiagnostics?.run_id ? (
          <div className="banner info">
            {isBrowserStartProblem(latestDiagnostics) && (
              <div className="banner warning">
                <h3>Browser konnte nicht gestartet werden</h3>
                <p>Der Fehler ist vor dem Oeffnen der Klassenbuch-Webseite aufgetreten. Es liegt sehr wahrscheinlich an Playwright/Chromium oder am Windows-Eventloop, nicht an den Klassenbuch-Selektoren.</p>
                <p>Naechste Schritte: KlassenbuchTool_starten.bat erneut starten, Playwright-Installation pruefen, ggf. python -m playwright install ausfuehren und Browser-Check erneut starten.</p>
              </div>
            )}
            {isPlaywrightPythonApiProblem(latestDiagnostics) && (
              <div className="banner warning">
                <h3>Playwright-Python-API-Fehler</h3>
                <p>Der Browser wurde geoeffnet und die Loginseite wurde erreicht. Der Fehler liegt im Code beim Suchen, Klicken oder Fuellen von Elementen. Ursache ist wahrscheinlich .first() statt .first/.nth(0).</p>
              </div>
            )}
            <p><strong>Letzter Klassenbuch-Lauf:</strong> {latestDiagnostics.run_id}</p>
            <p>Ergebnis: {latestDiagnostics.success ? 'Erfolg' : 'Fehler'} · Eintraege: {latestDiagnostics.entries_returned ?? '-'}</p>
            <p>Fehler: {latestDiagnostics.error_message || '-'}</p>
            <p>Wahrscheinliche Ursache: {latestDiagnostics.probable_cause || '-'}</p>
            <p>Naechste Aktion: {latestDiagnostics.next_action || '-'}</p>
            <p>Schritt: {latestDiagnostics.step || '-'}</p>
            <p>URL: {latestDiagnostics.current_url || '-'}</p>
            <p>Titel: {latestDiagnostics.page_title || '-'}</p>
            <p>Tabellen: {latestDiagnostics.table_count ?? latestDiagnostics.tables_found ?? '-'} · Zeilen: {latestDiagnostics.row_count ?? latestDiagnostics.rows_found ?? '-'}</p>
            <p>Diagnoseordner: {latestDiagnostics.diagnostics_folder || '-'}</p>
            <DiagnosticStatusCards diagnostics={latestDiagnostics} />
            <DiagnosticLinks diagnostics={latestDiagnostics} />
          </div>
        ) : <p className="muted">Noch kein Klassenbuch-Diagnoselauf vorhanden.</p>}
      </section>
    </>
  );
}
