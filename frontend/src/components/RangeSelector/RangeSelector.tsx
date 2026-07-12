export function RangeSelector({ value, onChange, unit }: { value: string; onChange: (value: string) => void; unit: string }) {
  return (
    <div className="field">
      <label>Auswertungsbereich</label>
      <input value={value} placeholder={`leer = alle ${unit}; z. B. 1-5, 8, 10-12`} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
