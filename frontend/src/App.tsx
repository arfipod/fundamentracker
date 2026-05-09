import { lazy, Suspense, useEffect, useState } from 'react';
import './App.css';
import { useWatchlist } from './hooks/useWatchlist';
import { useScanSettings } from './hooks/useScanSettings';
import { DashboardHeader } from './components/DashboardHeader';
import { AlertForm } from './components/AlertForm';
import { SignalInbox } from './components/SignalInbox';
import { apiFetch } from './lib/apiClient';
import type { MetricCatalogItem } from './types/metrics';

const WatchlistSection = lazy(() =>
  import('./components/WatchlistSection').then((module) => ({ default: module.WatchlistSection }))
);
const ExplorerSection = lazy(() =>
  import('./components/ExplorerSection').then((module) => ({ default: module.ExplorerSection }))
);

function App() {
  const [activeTab, setActiveTab] = useState<'signals' | 'watchlist' | 'explorer'>('signals');
  const [metricCatalog, setMetricCatalog] = useState<MetricCatalogItem[]>([]);
  const [metricCatalogError, setMetricCatalogError] = useState<string | null>(null);
  const [signalRefreshToken, setSignalRefreshToken] = useState(0);
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
    handleUndo
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
    handleScan
  } = useScanSettings(async () => {
    await fetchWatchlist();
    setSignalRefreshToken((current) => current + 1);
  });

  useEffect(() => {
    let cancelled = false;

    const fetchMetricCatalog = async () => {
      try {
        const response = await apiFetch('/metrics/catalog');
        if (!response.ok) {
          throw new Error('Failed to load metric catalog');
        }
        const catalog = await response.json();
        if (!cancelled) {
          setMetricCatalog(catalog);
          setMetricCatalogError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setMetricCatalogError(error instanceof Error ? error.message : 'Failed to load metric catalog');
        }
      }
    };

    fetchMetricCatalog();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    fetchWatchlist();
    fetchScanSettings();
  }, [fetchWatchlist, fetchScanSettings]);

  const handleAddNewAlert = async (ticker: string, metric: string, operator: string, targetValue: number, alertType: string): Promise<boolean> => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue, alertType);
    if (success) {
      await fetchScanSettings();
    }
    return success;
  };

  const handleInlineAdd = async (ticker: string, metric: string, operator: string, targetValue: number, alertType: string = 'absolute') => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue, alertType);
    if (success) {
      await fetchScanSettings();
    }
  };

  const combinedError = error || scanError || metricCatalogError;

  return (
    <div className="dashboard">
      <DashboardHeader
        scanInterval={scanInterval}
        lastScanTime={lastScanTime}
        isScanning={isScanning}
        currentServerTime={currentServerTime}
        nextScanTime={nextScanTime}
        onUpdateInterval={handleUpdateInterval}
        onForceScan={handleScan}
      />

      <div className="tabs-container">
        <button 
          className={`tab-btn ${activeTab === 'signals' ? 'active' : ''}`}
          onClick={() => setActiveTab('signals')}
        >
          Signals
        </button>
        <button 
          className={`tab-btn ${activeTab === 'watchlist' ? 'active' : ''}`}
          onClick={() => setActiveTab('watchlist')}
        >
          Watchlist
        </button>
        <button 
          className={`tab-btn ${activeTab === 'explorer' ? 'active' : ''}`}
          onClick={() => setActiveTab('explorer')}
        >
          Explorer
        </button>
      </div>

      {combinedError && <div className="error-message">{combinedError}</div>}

      <Suspense fallback={<div className="loading">Loading view...</div>}>
        {activeTab === 'signals' ? (
          <SignalInbox refreshToken={signalRefreshToken} />
        ) : activeTab === 'watchlist' ? (
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
        ) : activeTab === 'explorer' ? (
          <ExplorerSection metrics={metricCatalog} />
        ) : null}
      </Suspense>

      {undoQueue && (
        <div className="undo-toast" style={{
          position: 'fixed',
          bottom: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'var(--panel-bg)',
          color: 'var(--text-color)',
          padding: '12px 24px',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          zIndex: 9999,
          border: '1px solid var(--border-color)',
          animation: 'slideUp 0.3s ease-out'
        }}>
          <span>
            Eliminado {undoQueue.alerts.length} alerta(s) de <strong>{undoQueue.ticker}</strong>
          </span>
          <button 
            onClick={handleUndo}
            style={{
              background: 'var(--primary)',
              color: 'white',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            DESHACER
          </button>
        </div>
      )}

      <footer className="footer">
        Made with 💙 by arrf
      </footer>
    </div>
  );
}

export default App;
