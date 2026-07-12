export function StatusCard({ label, value, tone = 'neutral' }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <section className={`status-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}
