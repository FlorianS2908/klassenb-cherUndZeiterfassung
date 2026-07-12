export function describeSelection(selected: number[]) {
  return selected.length ? selected.join(', ') : 'Gesamte Datei';
}
