import { useEffect, useState } from 'react';
import { FinalReview } from '../components/FinalReview/FinalReview';
import { confirmReview } from '../services/reviewService';
import { getStatus } from '../services/statusService';

export function ReviewPage() {
  const [confirmed, setConfirmed] = useState(false);
  const [autoSubmit, setAutoSubmit] = useState(false);
  const data = { hinweis: 'Review sammelt die finalen Klassenbuch- und Timebutler-Daten aus dem aktuellen Lauf.', dryRunDefault: true };
  useEffect(() => {
    getStatus().then((status) => setAutoSubmit(status.auto_submit));
  }, []);
  async function set(value: boolean) {
    setConfirmed(value);
    if (value) await confirmReview(data);
  }
  return <FinalReview data={data} autoSubmit={autoSubmit} confirmed={confirmed} onConfirmed={set} />;
}
