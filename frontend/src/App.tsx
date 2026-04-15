import { useEffect } from 'react';
import './App.css';
import { useWatchlist } from './hooks/useWatchlist';
import { useScanSettings } from './hooks/useScanSettings';
import { DashboardHeader } from './components/DashboardHeader';
import { AlertForm } from './components/AlertForm';
import { WatchlistSection } from './components/WatchlistSection';

function App() {
  const {
    watchlist,
    loading,
    error,
    fetchWatchlist,
    handleAddAlertInline,
    handleUpdateTarget,
    handleDeleteAlert,
    handleDelete,
    handleToggleAlert
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
  } = useScanSettings(fetchWatchlist);

  useEffect(() => {
    fetchWatchlist();
    fetchScanSettings();
  }, [fetchWatchlist, fetchScanSettings]);

  const handleAddNewAlert = async (ticker: string, metric: string, operator: string, targetValue: number): Promise<boolean> => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue);
    if (success) {
      await fetchScanSettings();
    }
    return success;
  };

  const handleInlineAdd = async (ticker: string, metric: string, operator: string, targetValue: number) => {
    const success = await handleAddAlertInline(ticker, metric, operator, targetValue);
    if (success) {
      await fetchScanSettings();
    }
  };

  const combinedError = error || scanError;

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

      {combinedError && <div className="error-message">{combinedError}</div>}

      <AlertForm onAdd={handleAddNewAlert} />

      <WatchlistSection
        watchlist={watchlist}
        loading={loading}
        onDeleteTicker={handleDelete}
        onAddInline={handleInlineAdd}
        onUpdateAlert={handleUpdateTarget}
        onDeleteAlert={handleDeleteAlert}
        onToggleAlert={handleToggleAlert}
      />
    </div>
  );
}

export default App;
