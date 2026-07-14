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
import { checkSetup } from './services/setupService';

const pagePaths: Record<string, string> = {
  dashboard: '/',
  klassenbuch: '/klassenbuch',
  timebutler: '/timebutler',
  review: '/review',
  'analysis-history': '/analysis-history',
  screenshots: '/screenshots',
  logs: '/logs',
  settings: '/settings',
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
    '/screenshots': 'screenshots',
    '/logs': 'logs',
    '/settings': 'settings',
  };
  return routes[normalized] ?? 'not-found';
}

export default function App() {
  const initialPage = pageFromPath(window.location.pathname);
  const [page, setPageState] = useState(initialPage);
  const setPage = (nextPage: string) => {
    setPageState(nextPage);
    const path = pagePaths[nextPage] ?? '/';
    window.history.replaceState(null, '', path);
  };
  useEffect(() => {
    checkSetup()
      .then((response) => {
        if (response.data.setup_required) setPage('setup');
      })
      .catch(() => setPage('setup'));
  }, []);
  const pages: Record<string, ReactNode> = {
    dashboard: <DashboardPage setPage={setPage} />,
    klassenbuch: <KlassenbuchPage />,
    timebutler: <TimebutlerPage />,
    review: <ReviewPage />,
    'analysis-history': <AnalysisHistoryPage />,
    screenshots: <ScreenshotsPage />,
    logs: <LogsPage />,
    settings: <SettingsPage setPage={setPage} />,
    setup: <SetupPage setPage={setPage} />,
    'not-found': <NotFoundPage setPage={setPage} />,
  };
  return (
    <Layout page={page} setPage={setPage}>
      <AppErrorBoundary resetKey={page} setPage={setPage}>{pages[page] ?? pages['not-found']}</AppErrorBoundary>
    </Layout>
  );
}
