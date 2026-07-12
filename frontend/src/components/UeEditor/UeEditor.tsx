import type { UeItem } from '../../types';

const formats = ['Aufgaben-/Uebungsbesprechung', 'betreute Einzelarbeit', 'Lehrgespraech', 'Praesentation', 'Gruppenarbeit'];

export function UeEditor({ items, onChange }: { items: UeItem[]; onChange: (items: UeItem[]) => void }) {
  function update(index: number, item: UeItem) {
    const next = [...items];
    next[index] = item;
    onChange(next);
  }
  return (
    <section className="ue-grid">
      {items.map((item, index) => (
        <article className="ue-card" key={item.number}>
          <h3>UE {item.number}</h3>
          <textarea value={item.content} maxLength={500} onChange={(event) => update(index, { ...item, content: event.target.value })} />
          <small>{item.content.length}/500</small>
          <div className="chips">
            {formats.map((format) => (
              <label key={format}>
                <input
                  type="checkbox"
                  checked={item.formats.includes(format)}
                  disabled={!item.formats.includes(format) && item.formats.length >= 2}
                  onChange={(event) => {
                    const nextFormats = event.target.checked ? [...item.formats, format].slice(0, 2) : item.formats.filter((value) => value !== format);
                    update(index, { ...item, formats: nextFormats });
                  }}
                />
                {format}
              </label>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}
