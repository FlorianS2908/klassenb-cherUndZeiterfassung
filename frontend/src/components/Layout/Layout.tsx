import { BookOpen, Camera, ClipboardCheck, FileClock, FileText, KeyRound, LayoutDashboard, Settings, Timer, ScrollText } from 'lucide-react';
import type { ReactNode } from 'react';

const nav = [
  ['dashboard', 'Dashboard', LayoutDashboard],
  ['klassenbuch', 'Klassenbuch', BookOpen],
  ['timebutler', 'Zeiterfassung', Timer],
  ['review', 'Review', ClipboardCheck],
  ['analysis-history', 'Historie', FileClock],
  ['screenshots', 'Screenshots', Camera],
  ['logs', 'Logs', ScrollText],
  ['setup', 'Setup', KeyRound],
  ['settings', 'Einstellungen', Settings],
] as const;

export function Layout({ page, setPage, children }: { page: string; setPage: (page: string) => void; children: ReactNode }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><FileText size={24} /> Klassenbuch</div>
        <nav>
          {nav.map(([id, label, Icon]) => (
            <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}>
              <Icon size={18} /> {label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
