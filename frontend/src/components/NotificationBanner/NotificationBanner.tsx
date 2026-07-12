export function NotificationBanner({ message, tone = 'info' }: { message: string; tone?: 'info' | 'warning' | 'error' | 'success' }) {
  if (!message) return null;
  return <div className={`banner ${tone}`}>{message}</div>;
}
