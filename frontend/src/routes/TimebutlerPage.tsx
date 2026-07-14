import { useEffect, useState } from 'react';
import { TimebutlerEditor } from '../components/TimebutlerEditor/TimebutlerEditor';
import { getTimebutlerDefaults, prepareTimebutler, submitTimebutler } from '../services/timebutlerService';
import type { TimebutlerPayload } from '../types';

export function TimebutlerPage() {
  const [defaults, setDefaults] = useState<TimebutlerPayload | null>(null);
  const [payload, setPayload] = useState<TimebutlerPayload | null>(null);
  const [message, setMessage] = useState('');
  useEffect(() => {
    getTimebutlerDefaults().then((value) => {
      setDefaults(value);
      setPayload(value);
    });
  }, []);
  if (!payload || !defaults) return <p>Lade Standardwerte...</p>;
  return (
    <>
      <div className="page-head"><h1>Zeiterfassung</h1></div>
      <TimebutlerEditor value={payload} onChange={setPayload} onReset={() => setPayload(defaults)} />
      <div className="actions">
        <button className="secondary" onClick={async () => setMessage(JSON.stringify(await prepareTimebutler(payload), null, 2))}>Dry-Run Zeiterfassung vorbereiten</button>
        <button className="primary" onClick={async () => setMessage(JSON.stringify(await submitTimebutler(payload, false), null, 2))}>Final speichern pruefen</button>
      </div>
      {message && <pre className="preview">{message}</pre>}
    </>
  );
}
