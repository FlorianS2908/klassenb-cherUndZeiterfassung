import { useEffect, useState } from 'react';
import { apiGet } from '../services/api';
import { getOpenAiStatus } from '../services/fileService';
import { checkSetup } from '../services/setupService';
import type { SetupCheckResult } from '../types';

type OpenAiStatus = {
  active: boolean;
  key_present: boolean;
  source: string;
  message: string;
  display_path: string;
  model: string;
  max_input_chars: number;
};

export function SettingsPage({ setPage }: { setPage: (page: string) => void }) {
  const [settings, setSettings] = useState<unknown>(null);
  const [openAi, setOpenAi] = useState<OpenAiStatus | null>(null);
  const [setup, setSetup] = useState<SetupCheckResult | null>(null);
  useEffect(() => {
    apiGet('/api/settings').then(setSettings);
    getOpenAiStatus().then(setOpenAi);
    checkSetup().then((response) => setSetup(response.data));
  }, []);
  return (
    <>
      <div className="page-head"><h1>Einstellungen</h1></div>
      <section className="panel">
        <h2>Setup</h2>
        <div className="small-cards">
          <div><span>Vollstaendig</span><strong>{setup && !setup.setup_required ? 'Ja' : 'Nein'}</strong></div>
          <div><span>.env vorhanden</span><strong>{setup?.env_exists ? 'Ja' : 'Nein'}</strong></div>
          <div><span>Fehlende Werte</span><strong>{setup?.missing.length ? setup.missing.join(', ') : '-'}</strong></div>
          <div><span>API-Key</span><strong>{openAi?.key_present ? 'Vorhanden' : 'Nicht vorhanden'}</strong></div>
        </div>
        <div className="actions">
          <button className="secondary" onClick={() => setPage('setup')}>Setup in UI oeffnen</button>
        </div>
      </section>
      <section className="panel">
        <h2>OpenAI API</h2>
        <div className="small-cards">
          <div><span>Status</span><strong>{openAi?.active ? 'Aktiv' : 'Inaktiv'}</strong></div>
          <div><span>Quelle</span><strong>{openAi?.source || 'nicht vorhanden'}</strong></div>
          <div><span>Modell</span><strong>{openAi?.model || '-'}</strong></div>
          <div><span>Datei</span><strong>{openAi?.display_path || '-'}</strong></div>
        </div>
        <p>{openAi?.message}</p>
        <div className="actions">
          <button className="secondary" onClick={() => getOpenAiStatus().then(setOpenAi)}>API-Key-Datei pruefen</button>
        </div>
      </section>
      <pre className="preview">{JSON.stringify(settings, null, 2)}</pre>
    </>
  );
}
