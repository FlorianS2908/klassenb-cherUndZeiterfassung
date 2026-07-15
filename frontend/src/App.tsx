import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AppErrorBoundary } from './components/ErrorBoundary/AppErrorBoundary';
import { Layout } from './components/Layout/Layout';
import { DashboardPage } from './routes/DashboardPage';
import { AnalysisHistoryPage } from './routes/AnalysisHistoryPage';
import { KlassenbuchPage } from './routes/KlassenbuchPage';
import { LogsPage } from './routes/LogsPage';
import { ReviewPage } from './routes/ReviewPage';
import { ScreenshotsPage } from './routes/ScreenshotsPage';
import { SettingsPage } from './routes/SettingsPage';
import { SetupPage } from './routes/SetupPage';
import { TimebutlerPage } from './routes/TimebutlerPage';
import { NotFoundPage } from './routes/NotFoundPage';
import { FileAnalysisPage } from './routes/FileAnalysisPage';
import { SignatureSettingsPage } from './routes/SignatureSettingsPage';
import { checkSetup } from './services/setupService';
import { useWorkflowState } from './state/workflowState';

const pagePaths: Record<string, string> = {
  dashboard: '/',
  klassenbuch: '/klassenbuch',
  timebutler: '/timebutler',
  review: '/review',
  'analysis-history': '/analysis-history',
  analysis: '/analysis',
  screenshots: '/screenshots',
  logs: '/logs',
  settings: '/settings',
  signature: '/signature',
  setup: '/setup',
  'not-found': window.location.pathname,
};

function pageFromPath(pathname: string) {
  const normalized = pathname.toLowerCase().replace(/\/+$/, '') || '/';
  const routes: Record<string, string> = {
    '/': 'dashboard',
    '/setup': 'setup',
    '/klassenbuch': 'klassenbuch',
    '/timebutler': 'timebutler',
    '/review': 'review',
    '/analysis-history': 'analysis-history',
    '/analysis': 'analysis',
    '/screenshots': 'screenshots',
    '/logs': 'logs',
    '/settings': 'settings',
    '/signature': 'signature',
  };
  return routes[normalized] ?? 'not-found';
}

export default function App() {
  const initialPage = pageFromPath(window.location.pathname);
  const [page, setPageState] = useState(initialPage);
  const [workflowNotice, setWorkflowNotice] = useState('');
  const { workflow, setWorkflow, resetWorkflow } = useWorkflowState();
  const guardedPage = (nextPage: string, options?: { selectedClassbook?: boolean }) => {
    const hasSelectedClassbook = options?.selectedClassbook ?? Boolean(workflow.selectedClassbook);
    if (nextPage === 'analysis' && !hasSelectedClassbook) {
      setWorkflowNotice('Bitte zuerst ein Klassenbuch auswaehlen.');
      setWorkflow({ currentStep: 'classbooks' });
      return 'klassenbuch';
    }
    if (nextPage === 'review' && (!workflow.analysisDone || workflow.generatedEntries.length !== 9)) {
      if (hasSelectedClassbook) {
        setWorkflowNotice('Zuerst Datei hochladen und KI-Analyse abschliessen.');
        setWorkflow({ currentStep: 'analysis' });
        return 'analysis';
      }
      setWorkflowNotice('Bitte zuerst ein Klassenbuch auswaehlen.');
      setWorkflow({ currentStep: 'classbooks' });
      return 'klassenbuch';
    }
    setWorkflowNotice('');
    return nextPage;
  };
  const setPage = (nextPage: string, options?: { selectedClassbook?: boolean }) => {
    const targetPage = guardedPage(nextPage, options);
    setPageState(targetPage);
    setWorkflow({
      currentStep: targetPage === 'dashboard' ? 'overview' : targetPage === 'klassenbuch' ? 'classbooks' : targetPage === 'analysis' ? 'analysis' : targetPage === 'review' ? 'review' : workflow.currentStep,
    });
    const path = pagePaths[targetPage] ?? '/';
    window.history.replaceState(null, '', path);
  };
  useEffect(() => {
    checkSetup()
      .catch(() => undefined);
  }, []);
  useEffect(() => {
    if (page === 'analysis' && !workflow.selectedClassbook) {
      setWorkflowNotice('Bitte zuerst ein Klassenbuch auswaehlen.');
      setWorkflow({ currentStep: 'classbooks' });
      setPageState('klassenbuch');
      window.history.replaceState(null, '', '/klassenbuch');
      return;
    }
    if (page === 'review' && (!workflow.analysisDone || workflow.generatedEntries.length !== 9)) {
      if (workflow.selectedClassbook) {
        setWorkflowNotice('Zuerst Datei hochladen und KI-Analyse abschliessen.');
        setWorkflow({ currentStep: 'analysis' });
        setPageState('analysis');
        window.history.replaceState(null, '', '/analysis');
        return;
      }
      setWorkflowNotice('Bitte zuerst ein Klassenbuch auswaehlen.');
      setWorkflow({ currentStep: 'classbooks' });
      setPageState('klassenbuch');
      window.history.replaceState(null, '', '/klassenbuch');
    }
  }, [page, workflow.selectedClassbook, workflow.analysisDone, workflow.generatedEntries.length]);
  const pages: Record<string, ReactNode> = {
    dashboard: <DashboardPage setPage={setPage} />,
    klassenbuch: <KlassenbuchPage setPage={setPage} workflow={workflow} setWorkflow={setWorkflow} />,
    analysis: <FileAnalysisPage setPage={setPage} workflow={workflow} setWorkflow={setWorkflow} />,
    timebutler: <TimebutlerPage />,
    review: <ReviewPage setPage={setPage} workflow={workflow} setWorkflow={setWorkflow} />,
    'analysis-history': <AnalysisHistoryPage />,
    screenshots: <ScreenshotsPage />,
    logs: <LogsPage />,
    settings: <SettingsPage setPage={setPage} />,
    signature: <SignatureSettingsPage setPage={setPage} />,
    setup: <SetupPage setPage={setPage} />,
    'not-found': <NotFoundPage setPage={setPage} />,
  };
  return (
    <Layout page={page} setPage={setPage} workflow={workflow} resetWorkflow={resetWorkflow}>
      {workflowNotice && <div className="banner warning">{workflowNotice}</div>}
      <AppErrorBoundary resetKey={page} setPage={setPage}>{pages[page] ?? pages['not-found']}</AppErrorBoundary>
    </Layout>
  );
}
