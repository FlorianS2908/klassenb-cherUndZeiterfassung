import { useEffect, useState } from 'react';
import { FinalReview } from '../components/FinalReview/FinalReview';
import { confirmReview } from '../services/reviewService';
import { getStatus } from '../services/statusService';
import { apiGet } from '../services/api';

export function ReviewPage() {
  const [confirmed, setConfirmed] = useState(false);
  const [signatureConfirmed, setSignatureConfirmed] = useState(false);
  const [autoSubmit, setAutoSubmit] = useState(false);
  const [signatureValue, setSignatureValue] = useState('Schaffer');
  const data = { hinweis: 'Review sammelt die finalen Klassenbuch- und Timebutler-Daten aus dem aktuellen Lauf.', dryRunDefault: true, signatur: { wert: signatureValue, modus: autoSubmit ? 'Produktiv' : 'Dry-Run' }, kiMetadaten: { verwendet: 'siehe aktueller Analyse-Lauf', confidence_score: 'siehe Klassenbuch-Seite', warnungen: 'siehe Klassenbuch-Seite' } };
  useEffect(() => {
    getStatus().then((status) => setAutoSubmit(status.auto_submit));
    apiGet<any>('/api/settings').then((settings) => setSignatureValue(settings.default_signature || 'Schaffer'));
  }, []);
  async function set(value: boolean) {
    setConfirmed(value);
    if (value) await confirmReview({ ...data, signature_confirmed: signatureConfirmed });
  }
  async function setSignature(value: boolean) {
    setSignatureConfirmed(value);
    if (confirmed) await confirmReview({ ...data, signature_confirmed: value });
  }
  return <FinalReview data={data} autoSubmit={autoSubmit} confirmed={confirmed} signatureConfirmed={signatureConfirmed} signatureValue={signatureValue} signatureMode={autoSubmit ? 'Produktiv' : 'Dry-Run'} onConfirmed={set} onSignatureConfirmed={setSignature} />;
}
