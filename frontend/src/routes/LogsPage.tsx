import { useEffect, useState } from 'react';
import { apiGet } from '../services/api';

export function LogsPage() {
  const [content, setContent] = useState('');
  useEffect(() => {
    apiGet<{ content: string }>('/api/logs').then((result) => setContent(result.content));
  }, []);
  return <><div className="page-head"><h1>Logs</h1></div><pre className="preview">{content || 'Noch keine Logs vorhanden.'}</pre></>;
}
