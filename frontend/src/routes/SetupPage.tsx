import { Eye, EyeOff, KeyRound, Save, ShieldCheck, TestTube2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { SetupPayload } from '../types';
import { getSetupDefaults, saveSetup, validateOpenAiKeyFile } from '../services/setupService';

const emptyPayload: SetupPayload = {
  klassenbuch_url: '',
  timebutler_url: '',
  klassenbuch_username: '',
  klassenbuch_password: '',
  timebutler_username: '',
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
  github_remote_url: '',
  git_default_branch: 'main',
};

type Props = {
  setPage: (page: string) => void;
};

export function SetupPage({ setPage }: Props) {
  const [form, setForm] = useState<SetupPayload>(emptyPayload);
  const [status, setStatus] = useState<{ kind: 'info' | 'success' | 'error'; text: string } | null>(null);
  const [showSecrets, setShowSecrets] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getSetupDefaults()
      .then((defaults) => setForm({ ...emptyPayload, ...defaults }))
      .catch((error) => setStatus({ kind: 'error', text: String(error) }));
  }, []);

  function setValue<K extends keyof SetupPayload>(key: K, value: SetupPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function checkKeyFile() {
    const result = await validateOpenAiKeyFile(form.openai_api_key_file);
    setStatus({ kind: result.has_content ? 'success' : 'error', text: result.message });
  }

  async function submit() {
    setSaving(true);
    setStatus(null);
    try {
      const response = await saveSetup(form);
      setStatus({ kind: response.ok ? 'success' : 'error', text: response.message });
      if (response.ok) setPage('dashboard');
    } catch (error) {
      setStatus({ kind: 'error', text: String(error) });
    } finally {
      setSaving(false);
    }
  }

  const secretType = showSecrets ? 'text' : 'password';

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Setup</h1>
          <p>Zugangsdaten und lokale Pfade werden nur in der lokalen .env gespeichert.</p>
        </div>
        <div className="actions compact">
          <button className="secondary" onClick={() => setShowSecrets((value) => !value)}>
            {showSecrets ? <EyeOff size={18} /> : <Eye size={18} />}
            {showSecrets ? 'Verbergen' : 'Anzeigen'}
          </button>
          <button className="primary" disabled={saving} onClick={submit}>
            <Save size={18} /> {saving ? 'Speichert...' : 'Setup speichern'}
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
          <label className="field wide">
            API-Key direkt eintragen
            <input type={secretType} value={form.openai_api_key} placeholder="Optional, leer lassen = vorhandenen Wert behalten" onChange={(event) => setValue('openai_api_key', event.target.value)} />
          </label>
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
          <label className="checkline">
            <input type="checkbox" checked={form.auto_submit} onChange={(event) => setValue('auto_submit', event.target.checked)} />
            Produktivaktionen erlauben
          </label>
        </div>
      </section>
    </>
  );
}
