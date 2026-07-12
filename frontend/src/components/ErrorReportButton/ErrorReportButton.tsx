import { Bug } from 'lucide-react';
import { apiPost } from '../../services/api';

export function ErrorReportButton() {
  async function create() {
    const result = await apiPost<any>('/api/error-report');
    alert(result.message);
  }
  return <button className="secondary" onClick={create}><Bug size={16} /> Fehlerbericht erstellen</button>;
}
