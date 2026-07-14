import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
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
import { checkSetup } from './services/setupService';

export default function App() {
  const initialPage = window.location.pathname.toLowerCase().includes('/setup') ? 'setup' : 'dashboard';
  const [page, setPageState] = useState(initialPage);
  const setPage = (nextPage: string) => {
    setPageState(nextPage);
    const path = nextPage === 'setup' ? '/setup' : '/';
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
  };
  return <Layout page={page} setPage={setPage}>{pages[page]}</Layout>;
}
