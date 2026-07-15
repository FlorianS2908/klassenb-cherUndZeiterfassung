import { useEffect, useState } from 'react';
import { checkKlassenbuchBrowserHealth, diagnosticFileUrl, exportLatestKlassenbuchDiagnostic, getLatestKlassenbuchDiagnostics } from '../services/diagnosticsService';
import { deleteKlassenbuchCredentials, getKlassenbuchCredentialStatus, getOpenKlassenbuecher, getOpenKlassenbuecherDiagnostic, saveKlassenbuchCredentials, testKlassenbuchLoginDirect } from '../services/klassenbuchService';
import { ApiError } from '../services/api';
import type { KlassenbuchDiagnostics, KlassenbuchEntry } from '../types';
import type { WorkflowState } from '../state/workflowState';

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

export function KlassenbuchPage({
  setPage,
  workflow,
  setWorkflow,
}: {
  setPage: (page: string, options?: { selectedClassbook?: boolean }) => void;
  workflow: WorkflowState;
  setWorkflow: (patch: Partial<WorkflowState>) => void;
}) {
  const [openBooks, setOpenBooks] = useState<KlassenbuchEntry[]>([]);
  const [bookGroups, setBookGroups] = useState<Record<string, KlassenbuchEntry[]>>(groupKlassenbuecher([]));
  const [bookDiagnostics, setBookDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);
  const [webRunMessage, setWebRunMessage] = useState('');
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [latestDiagnostics, setLatestDiagnostics] = useState<KlassenbuchDiagnostics | null>(null);
  const [browserHealth, setBrowserHealth] = useState<Record<string, unknown> | null>(null);
  const [diagnosticExport, setDiagnosticExport] = useState<Record<string, unknown> | null>(null);
  const [exportingDiagnostic, setExportingDiagnostic] = useState(false);
  const [testingKlassenbuchLogin, setTestingKlassenbuchLogin] = useState(false);
  const [credentialUsername, setCredentialUsername] = useState('');
  const [credentialPassword, setCredentialPassword] = useState('');
  const [credentialStatus, setCredentialStatus] = useState<Record<string, unknown>>({ source: 'missing' });
  const [credentialMessage, setCredentialMessage] = useState('');
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [deletingCredentials, setDeletingCredentials] = useState(false);
  const [lastLoginTest, setLastLoginTest] = useState('Noch nicht getestet');

  useEffect(() => {
    getLatestKlassenbuchDiagnostics().then((result) => setLatestDiagnostics(result as KlassenbuchDiagnostics)).catch(() => undefined);
    refreshCredentialStatus();
  }, []);

  async function refreshCredentialStatus() {
    const response = await getKlassenbuchCredentialStatus();
    const data = (response as { data?: Record<string, unknown> }).data ?? {};
    setCredentialStatus(data);
  }

  async function loadOpenBooks() {
    setLoadingBooks(true);
    setWebRunMessage('Klassenbuecher werden geladen ... Login/Session wird geprueft ... Offene Klassenbuecher werden gelesen ...');
    try {
      const result = await getOpenKlassenbuecher();
      setOpenBooks(result.items);
      setBookGroups(groupKlassenbuecher(result.items, result.groups));
      setBookDiagnostics(result.diagnostics ?? null);
      setLatestDiagnostics((result.diagnostics ?? null) as KlassenbuchDiagnostics | null);
      const timings = (result.diagnostics as { timings_ms?: Record<string, number> } | undefined)?.timings_ms;
      const timingText = timings?.total ? ` (${timings.total} ms)` : '';
      setWebRunMessage(`${result.count ?? result.items.length} offene Klassenbuch-Eintraege geladen.${timingText}`);
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

  async function loadOpenBooksDiagnostic() {
    setLoadingBooks(true);
    setWebRunMessage('Vollstaendige Diagnose wird geladen. Das kann laenger dauern ...');
    try {
      const result = await getOpenKlassenbuecherDiagnostic();
      setOpenBooks(result.items);
      setBookGroups(groupKlassenbuecher(result.items, result.groups));
      setBookDiagnostics(result.diagnostics ?? null);
      setLatestDiagnostics((result.diagnostics ?? null) as KlassenbuchDiagnostics | null);
      setWebRunMessage(`${result.count ?? result.items.length} Klassenbuecher mit Diagnose geladen.`);
    } catch (error) {
      const parsedError = klassenbuchError(error);
      setOpenBooks([]);
      setBookGroups(groupKlassenbuecher([]));
      setBookDiagnostics(parsedError.diagnostics);
      setLatestDiagnostics(parsedError.diagnostics);
      setWebRunMessage(`Diagnose konnte nicht geladen werden: ${parsedError.message}`);
    } finally {
      setLoadingBooks(false);
    }
  }

  function selectBook(book: KlassenbuchEntry) {
    if (!book.editable) return;
    setWorkflow({
      selectedClassbook: book,
      uploadedFile: null,
      selectedRange: '',
      analysisResult: null,
      generatedEntries: [],
      analysisDone: false,
      reviewConfirmed: false,
      signatureReady: false,
      reviewDone: false,
      currentStep: 'analysis',
    });
    setWebRunMessage(`Klassenbuch ausgewaehlt: ${book.titel || book.title || book.nummer || book.number || book.datum || book.date || book.raw || 'unbekannt'}`);
    setPage('analysis', { selectedClassbook: true });
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

  async function runKlassenbuchLoginCheck() {
    setTestingKlassenbuchLogin(true);
    setWebRunMessage('Login-Test laeuft im Hintergrund ...');
    try {
      const response = await testKlassenbuchLoginDirect(credentialUsername || undefined, credentialPassword || undefined);
      const ok = Boolean((response as { ok?: boolean }).ok);
      setLastLoginTest(ok ? 'Erfolgreich' : 'Fehlgeschlagen');
      setWebRunMessage(ok ? 'Login erfolgreich.' : 'Login fehlgeschlagen. Die lokal gespeicherten Zugangsdaten wurden abgelehnt.');
    } catch {
      setLastLoginTest('Fehlgeschlagen');
      setWebRunMessage('Login-Test konnte nicht ausgefuehrt werden.');
    } finally {
      setTestingKlassenbuchLogin(false);
    }
  }

  async function saveCredentials() {
    if (!credentialUsername.trim() || !credentialPassword) {
      setCredentialMessage('Bitte Benutzername und Passwort eingeben.');
      return;
    }
    setSavingCredentials(true);
    setCredentialMessage('');
    try {
      await saveKlassenbuchCredentials(credentialUsername, credentialPassword);
      setCredentialPassword('');
      await refreshCredentialStatus();
      setCredentialMessage('Klassenbuch-Zugangsdaten wurden lokal gespeichert.');
    } catch {
      setCredentialMessage('Zugangsdaten konnten nicht lokal gespeichert werden.');
    } finally {
      setSavingCredentials(false);
    }
  }

  async function deleteCredentials() {
    setDeletingCredentials(true);
    setCredentialMessage('');
    try {
      await deleteKlassenbuchCredentials();
      setCredentialPassword('');
      await refreshCredentialStatus();
      setCredentialMessage('Lokale Klassenbuch-Zugangsdaten wurden geloescht.');
    } catch {
      setCredentialMessage('Lokale Zugangsdaten konnten nicht geloescht werden.');
    } finally {
      setDeletingCredentials(false);
    }
  }

  async function exportSanitizedDiagnostic() {
    setExportingDiagnostic(true);
    try {
      const result = await exportLatestKlassenbuchDiagnostic();
      setDiagnosticExport(result);
      setWebRunMessage(`Fehlerbericht exportiert: ${String(result.export_folder ?? '-')}`);
    } catch {
      setDiagnosticExport(null);
      setWebRunMessage('Noch keine Diagnose vorhanden. Bitte zuerst Klassenbuecher laden.');
    } finally {
      setExportingDiagnostic(false);
    }
  }

  return (
    <>
      <div className="page-head"><h1>Klassenbuch</h1></div>
      <section className="panel">
        <h2>Klassenbuch-Zugangsdaten</h2>
        <p className="muted">Die Zugangsdaten werden nur lokal gespeichert und nicht ins Repository uebernommen. Das Passwort wird nach dem Speichern nicht mehr angezeigt.</p>
        {credentialMessage && <div className="banner info">{credentialMessage}</div>}
        <div className="form-grid">
          <label className="field">
            Benutzername
            <input value={credentialUsername} onChange={(event) => setCredentialUsername(event.target.value)} placeholder="name@example.com" />
          </label>
          <label className="field">
            Passwort
            <input type="password" value={credentialPassword} onChange={(event) => setCredentialPassword(event.target.value)} placeholder="Wird nur lokal gespeichert" />
          </label>
          <div className="small-cards wide">
            <div><span>Zugangsdatenquelle</span><strong>{String(credentialStatus.source ?? 'missing')}</strong></div>
            <div><span>Benutzer vorhanden</span><strong>{credentialStatus.username_present ? 'Ja' : 'Nein'}</strong></div>
            <div><span>Passwort vorhanden</span><strong>{credentialStatus.password_present ? 'Ja' : 'Nein'}</strong></div>
            <div><span>Letzter Login-Test</span><strong>{lastLoginTest}</strong></div>
          </div>
        </div>
        <div className="actions">
          <button className="secondary" onClick={saveCredentials} disabled={savingCredentials}>{savingCredentials ? 'Speichert...' : 'Zugangsdaten lokal speichern'}</button>
          <button className="secondary" onClick={runKlassenbuchLoginCheck} disabled={testingKlassenbuchLogin}>{testingKlassenbuchLogin ? 'Login-Test laeuft ...' : 'Login testen'}</button>
          <button className="secondary" onClick={loadOpenBooks} disabled={loadingBooks}>{loadingBooks ? 'Login laeuft ...' : 'Klassenbuecher laden'}</button>
          <button className="secondary" onClick={deleteCredentials} disabled={deletingCredentials}>{deletingCredentials ? 'Loescht...' : 'Lokale Zugangsdaten loeschen'}</button>
        </div>
      </section>

      <section className="panel">
        <div className="page-head">
          <h2>Klassenbuecher</h2>
          <div className="actions">
            <button className="secondary" onClick={loadOpenBooks} disabled={loadingBooks}>{loadingBooks ? 'Login laeuft ...' : 'Klassenbuecher laden'}</button>
            <button className="secondary" onClick={loadOpenBooksDiagnostic} disabled={loadingBooks}>Vollstaendige Diagnose laden</button>
            <button className="secondary" onClick={openLatestDiagnostics}>Letzte Diagnose oeffnen</button>
            <button className="secondary" onClick={runBrowserHealth}>Browser-Check</button>
            <button className="secondary" onClick={runKlassenbuchLoginCheck} disabled={testingKlassenbuchLogin}>{testingKlassenbuchLogin ? 'Login-Test laeuft ...' : 'Login testen'}</button>
            <button className="secondary" onClick={() => setPage('setup')}>Zum Setup</button>
          </div>
        </div>
        {workflow.selectedClassbook && (
          <div className="banner info">
            Ausgewaehlt: {workflow.selectedClassbook.titel || workflow.selectedClassbook.title || workflow.selectedClassbook.raw || '-'}
          </div>
        )}
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
            <p>Tabellen: {bookDiagnostics.table_count ?? 0} / Zeilen: {bookDiagnostics.row_count ?? 0}</p>
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
                  {groupItems.map((book) => {
                    const editable = book.editable === true;
                    const statusWarning = editable && book.status && book.status.toLowerCase() !== 'offen';
                    return (
                      <tr key={book.id}>
                        <td>{book.datum || book.date || '-'}</td>
                        <td>{book.status || '-'}</td>
                        <td>{book.nummer || book.number || '-'}</td>
                        <td>{book.titel || book.title || book.raw || '-'}</td>
                        <td>{book.raum || '-'}</td>
                        <td>{book.beginn || '-'}</td>
                        <td>{book.ende || '-'}</td>
                        <td>{book.einsatzzeit_von || '-'} - {book.einsatzzeit_bis || '-'}</td>
                        <td>{editable ? 'ja' : 'nein'}{statusWarning ? <div className="muted">Dieses Klassenbuch ist nicht im Status Offen.</div> : null}</td>
                        <td><button className="secondary" disabled={!editable} onClick={() => selectBook(book)}>{editable ? 'Bearbeiten / Auswaehlen & weiter' : 'Nicht bearbeitbar'}</button></td>
                      </tr>
                    );
                  })}
                  {groupItems.length === 0 && <tr><td colSpan={10}>Keine Eintraege in dieser Gruppe.</td></tr>}
                </tbody>
              </table>
            </div>
          );
        })}
      </section>

      <section className="panel">
        <div className="page-head">
          <h2>Diagnose</h2>
          <button className="secondary" onClick={openLatestDiagnostics}>Letzte Diagnose oeffnen</button>
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
            <p><strong>Browser-Check:</strong> {browserHealth.ok ? 'ok' : 'Fehler'} / Schritt: {String(browserHealth.step ?? '-')}</p>
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
            <p>Ergebnis: {latestDiagnostics.success ? 'Erfolg' : 'Fehler'} / Eintraege: {latestDiagnostics.entries_returned ?? '-'}</p>
            <p>Fehler: {latestDiagnostics.error_message || '-'}</p>
            <p>Wahrscheinliche Ursache: {latestDiagnostics.probable_cause || '-'}</p>
            <p>Naechste Aktion: {latestDiagnostics.next_action || '-'}</p>
            <p>Schritt: {latestDiagnostics.step || '-'}</p>
            <p>URL: {latestDiagnostics.current_url || '-'}</p>
            <p>Titel: {latestDiagnostics.page_title || '-'}</p>
            <p>Tabellen: {latestDiagnostics.table_count ?? latestDiagnostics.tables_found ?? '-'} / Zeilen: {latestDiagnostics.row_count ?? latestDiagnostics.rows_found ?? '-'}</p>
            <p>Diagnoseordner: {latestDiagnostics.diagnostics_folder || '-'}</p>
            <DiagnosticStatusCards diagnostics={latestDiagnostics} />
            <DiagnosticLinks diagnostics={latestDiagnostics} />
          </div>
        ) : <p className="muted">Noch kein Klassenbuch-Diagnoselauf vorhanden.</p>}
      </section>
    </>
  );
}
