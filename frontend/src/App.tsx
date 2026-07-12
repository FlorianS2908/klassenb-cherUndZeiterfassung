import { useState } from 'react';
import type { ReactNode } from 'react';
import { Layout } from './components/Layout/Layout';
import { DashboardPage } from './routes/DashboardPage';
import { AnalysisHistoryPage } from './routes/AnalysisHistoryPage';
import { KlassenbuchPage } from './routes/KlassenbuchPage';
import { LogsPage } from './routes/LogsPage';
import { ReviewPage } from './routes/ReviewPage';
import { ScreenshotsPage } from './routes/ScreenshotsPage';
import { SettingsPage } from './routes/SettingsPage';
import { TimebutlerPage } from './routes/TimebutlerPage';

export default function App() {
  const [page, setPage] = useState('dashboard');
  const pages: Record<string, ReactNode> = {
    dashboard: <DashboardPage setPage={setPage} />,
    klassenbuch: <KlassenbuchPage />,
    timebutler: <TimebutlerPage />,
    review: <ReviewPage />,
    'analysis-history': <AnalysisHistoryPage />,
    screenshots: <ScreenshotsPage />,
    logs: <LogsPage />,
    settings: <SettingsPage />,
  };
  return <Layout page={page} setPage={setPage}>{pages[page]}</Layout>;
}
