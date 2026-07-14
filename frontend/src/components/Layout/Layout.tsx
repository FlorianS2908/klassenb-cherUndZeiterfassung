import { Check, ClipboardCheck, FileText, LayoutDashboard, Moon, Settings, Sun, Wrench } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import type { WorkflowState } from '../../state/workflowState';

const workflowNav = [
  ['dashboard', '1 Uebersicht', LayoutDashboard],
  ['klassenbuch', '2 Klassenbuecher', FileText],
  ['analysis', '3 Datei & Analyse', FileText],
  ['review', '4 Review', ClipboardCheck],
] as const;

function isDisabled(id: string, workflow: WorkflowState) {
  if (id === 'analysis') return !workflow.selectedClassbook;
  if (id === 'review') return !workflow.analysisDone || workflow.generatedEntries.length !== 9;
  return false;
}

function isDone(id: string, workflow: WorkflowState) {
  if (id === 'dashboard') return workflow.currentStep !== 'overview';
  if (id === 'klassenbuch') return Boolean(workflow.selectedClassbook);
  if (id === 'analysis') return workflow.analysisDone;
  if (id === 'review') return workflow.reviewDone;
  return false;
}

function disabledTitle(id: string) {
  if (id === 'analysis') return 'Zuerst Klassenbuch auswaehlen';
  if (id === 'review') return 'Zuerst Analyse abschliessen';
  return '';
}

export function Layout({
  page,
  setPage,
  workflow,
  resetWorkflow,
  children,
}: {
  page: string;
  setPage: (page: string) => void;
  workflow: WorkflowState;
  resetWorkflow: () => void;
  children: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dark, setDark] = useState(false);

  function toggleTheme() {
    setDark((value) => {
      document.body.classList.toggle('dark', !value);
      return !value;
    });
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><FileText size={24} /> Klassenbuch</div>
        <nav className="workflow-nav">
          {workflowNav.map(([id, label, Icon]) => {
            const disabled = isDisabled(id, workflow);
            return (
              <button key={id} className={page === id ? 'active' : ''} disabled={disabled} title={disabled ? disabledTitle(id) : ''} onClick={() => setPage(id)}>
                {isDone(id, workflow) ? <Check size={18} /> : <Icon size={18} />} {label}
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="main">
        <div className="topbar">
          <button className="secondary" onClick={toggleTheme}>{dark ? <Sun size={18} /> : <Moon size={18} />}{dark ? 'Light' : 'Dark'}</button>
          <div className="gear-menu">
            <button className="secondary" onClick={() => setMenuOpen((value) => !value)}><Settings size={18} /> Menue</button>
            {menuOpen && (
              <div className="gear-dropdown">
                <button onClick={() => setPage('dashboard')}>Status</button>
                <button onClick={() => setPage('settings')}>Einstellungen</button>
                <button onClick={() => setPage('klassenbuch')}>Diagnose</button>
                <button onClick={resetWorkflow}>Workflow zuruecksetzen</button>
                <button onClick={() => setPage('timebutler')}><Wrench size={16} /> Erweiterte Tools</button>
              </div>
            )}
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
