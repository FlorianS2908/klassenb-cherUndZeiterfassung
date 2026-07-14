import { Eye, EyeOff, KeyRound, RotateCcw, Save, ShieldCheck, TestTube2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { OpenAiKeyFileCheck, SetupPayload } from '../types';
import { checkSetup, deleteLocalKlassenbuchCredentials, getLocalKlassenbuchCredentialStatus, getSetupDefaults, saveLocalKlassenbuchCredentials, saveSetup, testKlassenbuchLogin, testKlassenbuchLoginWithCredentials, validateOpenAiKeyFile } from '../services/setupService';

const emptyPayload: SetupPayload = {
  klassenbuch_url: '',
  timebutler_url: '',
  klassenbuch_username: '',
  klassenbuch_password_present: false,
  klassenbuch_password_source: 'missing',
  klassenbuch_credentials_file_exists: false,
  klassenbuch_credentials_file_path: 'runtime/secrets/klassenbuch.credentials.json',
  klassenbuch_password: '',
  timebutler_username: '',
  timebutler_password_present: false,
  timebutler_password_source: 'missing',
  timebutler_password: '',
  use_separate_timebutler_credentials: false,
  openai_api_key_file: '',
  openai_api_key: '',
  openai_model: 'gpt-4o-mini',
  openai_max_input_chars: 30000,
  openai_timeout_seconds: 60,
  openai_retry_count: 2,
  openai_temperature: 0.2,
  auto_submit: false,
  default_signature: 'Schaffer',
  upload_folder: './uploads',
  screenshot_folder: './screenshots',
  log_folder: './logs',
  error_report_folder: './error_reports',
  analysis_history_folder: './analysis_history',
  reference_screenshot_dir: '',
  timebutler_project: 'FbW',
  timebutler_category: 'Training/Coaching',
  timebutler_start: '08:30',
  timebutler_end: '16:30',
  timebutler_pause: '45m',
  timebutler_remark: 'Training/Coaching im Rahmen der FbW-Unterrichtsdurchfuehrung',
  federal_state: 'BW',
  blocked_dates: '',
  vacation_dates: '',
  sick_dates: '',
  desktop_notifications: true,
  auto_open_browser: true,
  auto_dry_run_on_start: false,
  browser_headless: true,
  browser_slow_mo_ms: 0,
  browser_keep_open_on_error: false,
  github_remote_url: '',
  git_default_branch: 'main',
};

type Props = {
  setPage: (page: string) => void;
};

export function SetupPage({ setPage }: Props) {
  const [form, setForm] = useState<SetupPayload>(emptyPayload);
  const [defaults, setDefaults] = useState<SetupPayload>(emptyPayload);
  const [status, setStatus] = useState<{ kind: 'info' | 'success' | 'error'; text: string } | null>(null);
  const [keyStatus, setKeyStatus] = useState<OpenAiKeyFileCheck | null>(null);
  const [envExists, setEnvExists] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingLogin, setTestingLogin] = useState(false);
  const [savingLocalCredentials, setSavingLocalCredentials] = useState(false);
  const [deletingLocalCredentials, setDeletingLocalCredentials] = useState(false);

  useEffect(() => {
    getSetupDefaults()
      .then((loadedDefaults) => {
        const next = { ...emptyPayload, ...loadedDefaults };
        setDefaults(next);
        setForm(next);
      })
      .catch(() => setStatus({ kind: 'error', text: 'Setup-Standardwerte konnten nicht geladen werden.' }));
    checkSetup()
      .then((response) => {
        setEnvExists(response.data.env_exists);
        const credentials = response.data.config_public.credentials as Partial<SetupPayload> | undefined;
        if (credentials) {
          setForm((current) => ({ ...current, ...credentials }));
          setDefaults((current) => ({ ...current, ...credentials }));
        }
      })
      .catch(() => setEnvExists(false));
  }, []);

  function setValue<K extends keyof SetupPayload>(key: K, value: SetupPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function refreshCredentialStatus() {
    const response = await getLocalKlassenbuchCredentialStatus();
    const data = response.data as {
      username_present?: boolean;
      password_present?: boolean;
      source?: string;
      local_file_exists?: boolean;
      credentials_file_exists?: boolean;
      credentials_file_path?: string;
    };
    setForm((current) => ({
      ...current,
      klassenbuch_password_present: Boolean(data.password_present),
      klassenbuch_password_source: data.source ?? 'missing',
      klassenbuch_credentials_file_exists: Boolean(data.local_file_exists ?? data.credentials_file_exists),
      klassenbuch_credentials_file_path: data.credentials_file_path ?? current.klassenbuch_credentials_file_path,
    }));
  }

  async function checkKeyFile() {
    const result = await validateOpenAiKeyFile(form.openai_api_key_file);
    setKeyStatus(result);
    setStatus({ kind: result.non_empty ? 'success' : 'error', text: result.message });
  }

  function validateForm() {
    const missing: string[] = [];
    if (!form.klassenbuch_url.trim()) missing.push('Klassenbuch URL');
    if (!form.timebutler_url.trim()) missing.push('Timebutler URL');
    if (!form.klassenbuch_username.trim()) missing.push('Klassenbuch Benutzer');
    if (!envExists && !form.klassenbuch_password.trim()) missing.push('Klassenbuch Passwort');
    if (form.use_separate_timebutler_credentials && !form.timebutler_username.trim()) missing.push('Timebutler Benutzer');
    if (!envExists && form.use_separate_timebutler_credentials && !form.timebutler_password.trim()) missing.push('Timebutler Passwort');
    if (!/^\d{2}:\d{2}$/.test(form.timebutler_start) || !/^\d{2}:\d{2}$/.test(form.timebutler_end)) missing.push('Start/Ende im Format hh:mm');
    if (missing.length) {
      setStatus({ kind: 'error', text: `Bitte pruefen: ${missing.join(', ')}.` });
      return false;
    }
    setStatus({ kind: 'success', text: 'Eingaben sehen vollstaendig aus.' });
    return true;
  }

  function resetForm() {
    setForm(defaults);
    setKeyStatus(null);
    setStatus({ kind: 'info', text: 'Setup-Formular wurde auf die geladenen Werte zurueckgesetzt.' });
  }

  async function submit() {
    if (!validateForm()) return;
    setSaving(true);
    setStatus(null);
    try {
      const response = await saveSetup(form);
      setStatus({ kind: response.ok ? 'success' : 'error', text: response.message });
      if (response.ok) {
        const configPublic = response.data.config_public as { credentials?: Partial<SetupPayload> } | undefined;
        if (configPublic?.credentials) setForm((current) => ({ ...current, ...configPublic.credentials }));
        setForm((current) => ({ ...current, klassenbuch_password: '', timebutler_password: '', openai_api_key: '' }));
      }
    } catch (error) {
      setStatus({ kind: 'error', text: 'Setup konnte nicht gespeichert werden. Bitte Pflichtfelder und Zeitformat pruefen.' });
    } finally {
      setSaving(false);
    }
  }

  async function runKlassenbuchLoginTest() {
    setTestingLogin(true);
    setStatus(null);
    try {
      const response = form.klassenbuch_password
        ? await testKlassenbuchLoginWithCredentials(form.klassenbuch_username, form.klassenbuch_password)
        : await testKlassenbuchLogin();
      setStatus({ kind: response.ok ? 'success' : 'error', text: response.ok ? 'Login erfolgreich.' : 'Login fehlgeschlagen.' });
    } catch (error) {
      setStatus({ kind: 'error', text: 'Login fehlgeschlagen. Bitte Benutzername und Passwort neu eingeben.' });
    } finally {
      setTestingLogin(false);
    }
  }

  async function saveLocalCredentials() {
    if (!form.klassenbuch_username.trim() || !form.klassenbuch_password) {
      setStatus({ kind: 'error', text: 'Bitte Klassenbuch-Benutzer und Passwort eingeben.' });
      return;
    }
    setSavingLocalCredentials(true);
    setStatus(null);
    try {
      const response = await saveLocalKlassenbuchCredentials(form.klassenbuch_username, form.klassenbuch_password);
      const data = response.data as Partial<SetupPayload>;
      setForm((current) => ({
        ...current,
        ...data,
        klassenbuch_password: '',
        klassenbuch_password_present: true,
        klassenbuch_password_source: 'local_file',
      }));
      await refreshCredentialStatus();
      setStatus({ kind: 'success', text: 'Zugangsdaten lokal gespeichert.' });
    } catch (error) {
      setStatus({ kind: 'error', text: 'Zugangsdaten konnten nicht lokal gespeichert werden.' });
    } finally {
      setSavingLocalCredentials(false);
    }
  }

  async function deleteLocalCredentials() {
    setDeletingLocalCredentials(true);
    setStatus(null);
    try {
      await deleteLocalKlassenbuchCredentials();
      setForm((current) => ({
        ...current,
        klassenbuch_password: '',
        klassenbuch_password_present: false,
        klassenbuch_password_source: 'missing',
        klassenbuch_credentials_file_exists: false,
      }));
      await refreshCredentialStatus();
      setStatus({ kind: 'success', text: 'Lokale Zugangsdaten geloescht.' });
    } catch (error) {
      setStatus({ kind: 'error', text: 'Lokale Zugangsdaten konnten nicht geloescht werden.' });
    } finally {
      setDeletingLocalCredentials(false);
    }
  }

  const secretType = showSecrets ? 'text' : 'password';

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Einrichtung Klassenbuch & Zeiterfassung</h1>
          <p>Passwoerter werden bevorzugt im Windows Credential Manager gespeichert. Sie werden nicht angezeigt, nicht geloggt und nicht ins Repository uebernommen.</p>
        </div>
        <div className="actions compact">
          <button className="secondary" onClick={() => setShowSecrets((value) => !value)}>
            {showSecrets ? <EyeOff size={18} /> : <Eye size={18} />}
            {showSecrets ? 'Verbergen' : 'Anzeigen'}
          </button>
          <button className="primary" disabled={saving} onClick={submit}>
            <Save size={18} /> {saving ? 'Speichert...' : 'Setup speichern'}
          </button>
          <button className="secondary" onClick={validateForm}>
            <ShieldCheck size={18} /> Eingaben pruefen
          </button>
          <button className="secondary" onClick={resetForm}>
            <RotateCcw size={18} /> Zuruecksetzen
          </button>
        </div>
      </div>

      {status && <div className={`banner ${status.kind}`}>{status.text}</div>}

      <section className="panel">
        <h2><KeyRound size={18} /> Zugangsdaten</h2>
        <div className="form-grid">
          <label className="field wide">
            Klassenbuch URL
            <input value={form.klassenbuch_url} onChange={(event) => setValue('klassenbuch_url', event.target.value)} />
          </label>
          <label className="field">
            Klassenbuch Benutzer
            <input value={form.klassenbuch_username} onChange={(event) => setValue('klassenbuch_username', event.target.value)} />
          </label>
          <label className="field">
            Klassenbuch Passwort
            <input type={secretType} value={form.klassenbuch_password} placeholder="Leer lassen = vorhandenes Passwort behalten" onChange={(event) => setValue('klassenbuch_password', event.target.value)} />
          </label>
          <p className="wide muted">Das Passwort wird bevorzugt im Windows Credential Manager gespeichert. Es wird nicht im Code und nicht im Repository abgelegt.</p>
          <div className="small-cards wide">
            <div><span>Klassenbuch Passwort gespeichert</span><strong>{form.klassenbuch_password_present ? 'Ja' : 'Nein'}</strong></div>
            <div><span>Quelle</span><strong>{form.klassenbuch_password_source === 'local_file' ? 'local_file' : form.klassenbuch_password_source === 'keyring' ? 'keyring' : form.klassenbuch_password_source === 'env' ? 'env' : 'missing'}</strong></div>
            <div><span>Benutzer vorhanden</span><strong>{form.klassenbuch_username.trim() ? 'Ja' : 'Nein'}</strong></div>
            <div><span>Passwort vorhanden</span><strong>{form.klassenbuch_password_present ? 'Ja' : 'Nein'}</strong></div>
            <div><span>Credential-Datei</span><strong>{form.klassenbuch_credentials_file_exists ? 'Ja' : 'Nein'}</strong></div>
          </div>
          <p className="wide muted">Lokale Datei: {form.klassenbuch_credentials_file_path ?? 'runtime/secrets/klassenbuch.credentials.json'}</p>
          <div className="actions wide">
            <button className="secondary" onClick={saveLocalCredentials} disabled={savingLocalCredentials}>
              <Save size={18} /> {savingLocalCredentials ? 'Speichert lokal...' : 'Klassenbuch-Zugangsdaten lokal speichern'}
            </button>
            <button className="secondary" onClick={deleteLocalCredentials} disabled={deletingLocalCredentials || !form.klassenbuch_credentials_file_exists}>
              {deletingLocalCredentials ? 'Loescht...' : 'Lokale Zugangsdaten loeschen'}
            </button>
            <button className="secondary" onClick={runKlassenbuchLoginTest} disabled={testingLogin || (!form.klassenbuch_password_present && !form.klassenbuch_password)}>
              <TestTube2 size={18} /> {testingLogin ? 'Test laeuft...' : 'Klassenbuch-Login testen'}
            </button>
          </div>
          <label className="field wide">
            Timebutler URL
            <input value={form.timebutler_url} onChange={(event) => setValue('timebutler_url', event.target.value)} />
          </label>
          <label className="checkline wide">
            <input
              type="checkbox"
              checked={!form.use_separate_timebutler_credentials}
              onChange={(event) => setValue('use_separate_timebutler_credentials', !event.target.checked)}
            />
            Gleiche Zugangsdaten fuer Timebutler verwenden
          </label>
          {form.use_separate_timebutler_credentials && (
            <>
              <label className="field">
                Timebutler Benutzer
                <input value={form.timebutler_username} onChange={(event) => setValue('timebutler_username', event.target.value)} />
              </label>
              <label className="field">
                Timebutler Passwort
                <input type={secretType} value={form.timebutler_password} placeholder="Leer lassen = vorhandenes Passwort behalten" onChange={(event) => setValue('timebutler_password', event.target.value)} />
              </label>
            </>
          )}
        </div>
      </section>

      <section className="panel">
        <h2><TestTube2 size={18} /> OpenAI</h2>
        <div className="form-grid">
          <label className="field wide">
            API-Key-Datei
            <input value={form.openai_api_key_file} onChange={(event) => setValue('openai_api_key_file', event.target.value)} />
          </label>
          {keyStatus && (
            <div className="small-cards wide">
              <div><span>Gefunden</span><strong>{keyStatus.exists ? 'Ja' : 'Nein'}</strong></div>
              <div><span>Lesbar</span><strong>{keyStatus.readable ? 'Ja' : 'Nein'}</strong></div>
              <div><span>Nicht leer</span><strong>{keyStatus.non_empty ? 'Ja' : 'Nein'}</strong></div>
            </div>
          )}
          <label className="field wide">
            API-Key direkt eintragen
            <input type={secretType} value={form.openai_api_key} placeholder="Optional, leer lassen = vorhandenen Wert behalten" onChange={(event) => setValue('openai_api_key', event.target.value)} />
          </label>
          <p className="wide muted">Der API-Key wird niemals angezeigt, geloggt oder ins Repository uebernommen.</p>
          <label className="field">
            Modell
            <input value={form.openai_model} onChange={(event) => setValue('openai_model', event.target.value)} />
          </label>
          <label className="field">
            Max. Eingabezeichen
            <input type="number" value={form.openai_max_input_chars} onChange={(event) => setValue('openai_max_input_chars', Number(event.target.value))} />
          </label>
          <label className="field">
            Timeout Sekunden
            <input type="number" value={form.openai_timeout_seconds} onChange={(event) => setValue('openai_timeout_seconds', Number(event.target.value))} />
          </label>
        </div>
        <div className="actions">
          <button className="secondary" onClick={checkKeyFile}><ShieldCheck size={18} /> API-Key-Datei pruefen</button>
        </div>
      </section>

      <section className="panel">
        <h2>Standardwerte</h2>
        <div className="form-grid">
          <label className="field">
            Signatur
            <input value={form.default_signature} onChange={(event) => setValue('default_signature', event.target.value)} />
          </label>
          <label className="field">
            Bundesland
            <input value={form.federal_state} onChange={(event) => setValue('federal_state', event.target.value)} />
          </label>
          <label className="field">
            Projekt
            <input value={form.timebutler_project} onChange={(event) => setValue('timebutler_project', event.target.value)} />
          </label>
          <label className="field">
            Kategorie
            <input value={form.timebutler_category} onChange={(event) => setValue('timebutler_category', event.target.value)} />
          </label>
          <label className="field">
            Start
            <input value={form.timebutler_start} onChange={(event) => setValue('timebutler_start', event.target.value)} />
          </label>
          <label className="field">
            Ende
            <input value={form.timebutler_end} onChange={(event) => setValue('timebutler_end', event.target.value)} />
          </label>
          <label className="field">
            Pause
            <input value={form.timebutler_pause} onChange={(event) => setValue('timebutler_pause', event.target.value)} />
          </label>
          <label className="field wide">
            Bemerkung
            <textarea value={form.timebutler_remark} onChange={(event) => setValue('timebutler_remark', event.target.value)} />
          </label>
          <label className="field wide">
            Referenz-Screenshot-Ordner
            <input value={form.reference_screenshot_dir} onChange={(event) => setValue('reference_screenshot_dir', event.target.value)} />
          </label>
          <label className="field">
            Sperrtage
            <input value={form.blocked_dates} onChange={(event) => setValue('blocked_dates', event.target.value)} />
          </label>
          <label className="field">
            Urlaubstage
            <input value={form.vacation_dates} onChange={(event) => setValue('vacation_dates', event.target.value)} />
          </label>
          <label className="field">
            Krankheitstage
            <input value={form.sick_dates} onChange={(event) => setValue('sick_dates', event.target.value)} />
          </label>
          <label className="checkline">
            <input type="checkbox" checked={form.desktop_notifications} onChange={(event) => setValue('desktop_notifications', event.target.checked)} />
            Desktop-Benachrichtigungen
          </label>
          <label className="checkline wide">
            <input type="checkbox" checked={!form.browser_headless} onChange={(event) => setValue('browser_headless', !event.target.checked)} />
            Browser sichtbar anzeigen (Debug-Modus)
          </label>
          <p className="wide muted">Im normalen Betrieb laeuft der Browser unsichtbar. Fuer Fehlersuche kann der sichtbare Debug-Modus aktiviert werden.</p>
          <label className="field">
            Browser Slow-Mo ms
            <input type="number" value={form.browser_slow_mo_ms} onChange={(event) => setValue('browser_slow_mo_ms', Number(event.target.value))} />
          </label>
          <label className="checkline">
            <input type="checkbox" checked={form.browser_keep_open_on_error} onChange={(event) => setValue('browser_keep_open_on_error', event.target.checked)} />
            Browser bei Fehler offen halten
          </label>
          <label className="checkline">
            <input type="checkbox" checked={form.auto_submit} onChange={(event) => setValue('auto_submit', event.target.checked)} />
            Produktivaktionen erlauben
          </label>
          {form.auto_submit && <div className="banner warning wide">Produktivaktionen bleiben zusaetzlich durch die finale Review gesperrt. Bitte nur aktivieren, wenn du wirklich speichern/signieren/absenden willst.</div>}
        </div>
      </section>
    </>
  );
}
