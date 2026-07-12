import type { TimebutlerPayload } from '../../types';

export function TimebutlerEditor({ value, onChange, onReset }: { value: TimebutlerPayload; onChange: (value: TimebutlerPayload) => void; onReset: () => void }) {
  const set = (key: keyof TimebutlerPayload, next: string) => onChange({ ...value, [key]: next });
  return (
    <section className="panel form-grid">
      {(['target_date', 'project', 'category', 'start', 'end', 'pause'] as const).map((key) => (
        <label className="field" key={key}>
          {key}
          <input value={value[key]} onChange={(event) => set(key, event.target.value)} />
        </label>
      ))}
      <label className="field wide">
        Bemerkung
        <textarea value={value.remark} maxLength={500} onChange={(event) => set('remark', event.target.value)} />
      </label>
      <button className="secondary" onClick={onReset}>Standardwerte wiederherstellen</button>
    </section>
  );
}
