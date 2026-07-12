import { useEffect, useState } from 'react';
import { apiGet } from '../services/api';

export function SettingsPage() {
  const [settings, setSettings] = useState<unknown>(null);
  useEffect(() => {
    apiGet('/api/settings').then(setSettings);
  }, []);
  return <><div className="page-head"><h1>Einstellungen</h1></div><pre className="preview">{JSON.stringify(settings, null, 2)}</pre></>;
}
