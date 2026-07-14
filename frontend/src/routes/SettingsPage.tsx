import { useEffect, useState } from 'react';
import { apiGet } from '../services/api';
import { getOpenAiStatus } from '../services/fileService';

export function SettingsPage({ setPage }: { setPage: (page: string) => void }) {
  const [settings, setSettings] = useState<unknown>(null);
  const [openAi, setOpenAi] = useState<unknown>(null);
  useEffect(() => {
    apiGet('/api/settings').then(setSettings);
    getOpenAiStatus().then(setOpenAi);
  }, []);
  return (
    <>
      <div className="page-head"><h1>Einstellungen</h1></div>
      <section className="panel">
        <h2>OpenAI API</h2>
        <pre className="preview">{JSON.stringify(openAi, null, 2)}</pre>
        <div className="actions">
          <button className="secondary" onClick={() => setPage('setup')}>Setup oeffnen</button>
          <button className="secondary" onClick={() => getOpenAiStatus().then(setOpenAi)}>API-Key-Datei pruefen</button>
        </div>
      </section>
      <pre className="preview">{JSON.stringify(settings, null, 2)}</pre>
    </>
  );
}
