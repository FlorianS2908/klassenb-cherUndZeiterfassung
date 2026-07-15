export function RangeSelector({ value, onChange, unit }: { value: string; onChange: (value: string) => void; unit: string }) {
  return (
    <div className="field">
      <label>Auswertungsbereich</label>
      <input value={value} placeholder={`z. B. 5-10 ${unit}`} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
