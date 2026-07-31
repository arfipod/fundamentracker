import { lazy, Suspense, useEffect, useState } from 'react';
import './App.css';
import { useWatchlist } from './hooks/useWatchlist';
import { useScanSettings } from './hooks/useScanSettings';
import { useTheme } from './hooks/useTheme';
import { DashboardHeader } from './components/DashboardHeader';
import { AlertForm } from './components/AlertForm';
import { SignalInbox } from './components/SignalInbox';
import { Icon, type IconName } from './components/Icon';
import { apiFetch } from './lib/apiClient';
import type { MetricCatalogItem } from './types/metrics';

const WatchlistSection = lazy(() =>
  import('./components/WatchlistSection').then((module) => ({ default: module.WatchlistSection }))
);
const ExplorerSection = lazy(() =>
  import('./components/ExplorerSection').then((module) => ({ default: module.ExplorerSection }))
);

type WorkspaceView = 'signals' | 'watchlist' | 'explorer';

const NAV_ITEMS: Array<{ id: WorkspaceView; label: string; description: string; icon: IconName }> = [
  { id: 'signals', label: 'Signals', description: 'Items that need review', icon: 'signals' },
  { id: 'watchlist', label: 'Watchlist', description: 'Companies and alert rules', icon: 'watchlist' },
  { id: 'explorer', label: 'Explorer', description: 'Inspect a metric in context', icon: 'explorer' },
];

function getInitialView(): WorkspaceView {
  const storedView = window.localStorage.getItem('fundamentracker-view');
  return NAV_ITEMS.some((item) => item.id === storedView) ? storedView as WorkspaceView : 'signals';
}

function App() {
  const [activeView, setActiveView] = useState<WorkspaceView>(getInitialView);
  const [metricCatalog, setMetricCatalog] = useState<MetricCatalogItem[]>([]);
  const [metricCatalogError, setMetricCatalogError] = useState<string | null>(null);
  const [signalRefreshToken, setSignalRefreshToken] = useState(0);
  const { theme, toggleTheme } = useTheme();
  const {
    watchlist,
    loading,
    error,
    fetchWatchlist,
    handleAddAlertInline,
    handleUpdateTarget,
    handleDeleteAlert,
    handleDelete,
    handleToggleAlert,
    handleAddTag,
    handleRemoveTag,
    handleUpdateMetadata,
    undoQueue,
    handleUndo,
  } = useWatchlist();

  const {
    scanInterval,
    lastScanTime,
    isScanning,
    scanError,
    currentServerTime,
    nextScanTime,
    fetchScanSettings,
    handleUpdateInterval,
    handleScan,
  } = useScanSettings(async () => {
    await fetchWatchlist();
    setSignalRefreshToken((current) => current + 1);
  });

  useEffect(() => {
    window.localStorage.setItem('fundamentracker-view', activeView);
  }, [activeView]);

  useEffect(() => {
    let cancelled = false;

    const fetchMetricCatalog = async () => {
      try {
        const response = await apiFetch('/metrics/catalog');
        if (!response.ok) throw new Error('The metric catalog could not be loaded.');
        const catalog = await response.json();
        if (!cancelled) {
          setMetricCatalog(catalog);
          setMetricCatalogError(null);
        }
      } catch (catalogError) {
        if (!cancelled) {
          setMetricCatalogError(
            catalogError instanceof Error ? catalogError.message : 'The metric catalog could not be loaded.'
          );
        }
      }
    };

    void fetchMetricCatalog();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    void fetchWatchlist();
    void fetchScanSettings();
  }, [fetchWatchlist, fetchScanSettings]);

  const handleAddNewAlert = async (
    ticker: string,
    metric: string,
    operator: string,
    targetValue: number,
    alertType: string
  ): Promise<boolean> => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue, alertType);
    if (success) await fetchScanSettings();
    return success;
  };

  const handleInlineAdd = async (
    ticker: string,
    metric: string,
    operator: string,
    targetValue: number,
    alertType = 'absolute'
  ) => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue, alertType);
    if (success) await fetchScanSettings();
  };

  const combinedError = error || scanError || metricCatalogError;
  const watchlistCount = watchlist ? Object.keys(watchlist).length : 0;

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to workspace</a>
      <div className="app-shell">
        <DashboardHeader
          scanInterval={scanInterval}
          lastScanTime={lastScanTime}
          isScanning={isScanning}
          currentServerTime={currentServerTime}
          nextScanTime={nextScanTime}
          theme={theme}
          onToggleTheme={toggleTheme}
          onUpdateInterval={handleUpdateInterval}
          onForceScan={handleScan}
        />

        <nav className="primary-nav" aria-label="Workspace views">
          <div className="primary-nav-track">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`nav-item${activeView === item.id ? ' active' : ''}`}
                aria-current={activeView === item.id ? 'page' : undefined}
                onClick={() => setActiveView(item.id)}
              >
                <Icon name={item.icon} />
                <span className="nav-item-copy">
                  <strong>{item.label}</strong>
                  <span>{item.description}</span>
                </span>
                {item.id === 'watchlist' && watchlistCount > 0 && (
                  <span className="nav-count" aria-label={`${watchlistCount} companies`}>{watchlistCount}</span>
                )}
              </button>
            ))}
          </div>
        </nav>

        <main className="workspace" id="main-content">
          {combinedError && (
            <div className="notice notice-error" role="alert">
              <strong>Something needs attention.</strong>
              <span>{combinedError}</span>
            </div>
          )}

          <Suspense fallback={<div className="loading-state" role="status">Loading workspace…</div>}>
            <div id={`view-${activeView}`}>
              {activeView === 'signals' ? (
                <SignalInbox refreshToken={signalRefreshToken} />
              ) : activeView === 'watchlist' ? (
                <>
                  <AlertForm metrics={metricCatalog} onAdd={handleAddNewAlert} />
                  <WatchlistSection
                    watchlist={watchlist}
                    loading={loading}
                    metrics={metricCatalog}
                    onDeleteTicker={handleDelete}
                    onAddInline={handleInlineAdd}
                    onUpdateAlert={handleUpdateTarget}
                    onDeleteAlert={handleDeleteAlert}
                    onToggleAlert={handleToggleAlert}
                    onAddTag={handleAddTag}
                    onRemoveTag={handleRemoveTag}
                    onUpdateMetadata={handleUpdateMetadata}
                  />
                </>
              ) : (
                <ExplorerSection metrics={metricCatalog} />
              )}
            </div>
          </Suspense>
        </main>

        {undoQueue && (
          <div className="undo-toast" role="status" aria-live="polite">
            <span>
              Removed {undoQueue.alerts.length} alert{undoQueue.alerts.length === 1 ? '' : 's'} from{' '}
              <strong>{undoQueue.ticker}</strong>.
            </span>
            <button className="button button-secondary button-small" type="button" onClick={handleUndo}>
              Undo
            </button>
          </div>
        )}

        <footer className="footer">Private, self-hosted investment workspace.</footer>
      </div>
    </>
  );
}

export default App;
