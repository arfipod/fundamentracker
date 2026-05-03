import { useState, useEffect } from 'react';

/**
 * Props for the DashboardHeader component.
 * @interface Props
 * @property {number} scanInterval - The configured scan interval in seconds.
 * @property {number} lastScanTime - The Unix timestamp of the last scan.
 * @property {boolean} isScanning - Whether a scan is currently in progress.
 * @property {number} currentServerTime - The current Unix timestamp from the server.
 * @property {number} nextScanTime - The expected Unix timestamp of the next scan.
 * @property {Function} onUpdateInterval - Callback to update the scan interval.
 * @property {Function} onForceScan - Callback to manually force a scan.
 */
interface Props {
  scanInterval: number;
  lastScanTime: number;
  isScanning: boolean;
  currentServerTime: number;
  nextScanTime: number;
  onUpdateInterval: (interval: number) => void;
  onForceScan: () => void;
}

/**
 * DashboardHeader component displays the title, scan interval controls,
 * and current scanning status and timing information.
 * 
 * @param {Props} props - The component props
 * @returns {JSX.Element} The rendered DashboardHeader component
 */
export function DashboardHeader({
  scanInterval,
  lastScanTime,
  isScanning,
  currentServerTime,
  nextScanTime,
  onUpdateInterval,
  onForceScan
}: Props) {
  const [localInterval, setLocalInterval] = useState({ d: 0, h: 0, m: 0 });
  const [marketStats, setMarketStats] = useState<{symbol: string, current: number, change_percent: number}[]>([]);

  useEffect(() => {
    setLocalInterval({
      d: Math.floor(scanInterval / 86400),
      h: Math.floor((scanInterval % 86400) / 3600),
      m: Math.floor((scanInterval % 3600) / 60)
    });
  }, [scanInterval]);

  useEffect(() => {
    const fetchMarketStats = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/market-overview`);
        if (res.ok) {
          const data = await res.json();
          setMarketStats(data);
        }
      } catch (err) {
        console.error("Failed to fetch market stats:", err);
      }
    };
    fetchMarketStats();
    // Refresh market stats every 5 minutes
    const interval = setInterval(fetchMarketStats, 300000);
    return () => clearInterval(interval);
  }, []);

  const handleApplyInterval = () => {
    const total = (localInterval.d * 86400) + (localInterval.h * 3600) + (localInterval.m * 60);
    if (total !== scanInterval) {
      onUpdateInterval(total);
    }
  };

  return (
    <>
      {marketStats.length > 0 && (
        <div className="top-bar-tickers" style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '2rem',
          padding: '0.3rem 1rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          borderBottom: '1px solid var(--border-color)',
          marginBottom: '1.5rem',
          backgroundColor: 'transparent'
        }}>
          {marketStats.map(stat => (
            <div key={stat.symbol} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontWeight: '600', opacity: 0.8 }}>{stat.symbol}</span>
              <span>{stat.current.toFixed(2)}</span>
              <span style={{ color: stat.change_percent >= 0 ? '#10b981' : '#ef4444', fontWeight: '500' }}>
                {stat.change_percent >= 0 ? '▲' : '▼'} {Math.abs(stat.change_percent).toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      )}

      <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '1rem' }}>
        <div className="header-left">
          <h1 style={{ margin: 0, fontSize: '1.8rem' }}>FundamenTracker Dashboard</h1>
        </div>
        
        <div className="header-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.6rem' }}>
          <div className="header-status-row" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              <span>Server time: {new Date(currentServerTime * 1000).toLocaleTimeString()}</span>
              <span>|</span>
              <span>Last scan: {lastScanTime ? new Date(lastScanTime * 1000).toLocaleTimeString() : 'Nunca'}</span>
              <span>|</span>
              <span>Next scan: {nextScanTime ? new Date(nextScanTime * 1000).toLocaleTimeString() : 'Manual'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {isScanning && <span style={{ fontSize: '0.85rem', color: 'var(--primary)', fontWeight: 'bold' }}>Scanning...</span>}
              <button className="btn-primary" onClick={onForceScan} disabled={isScanning} style={{ padding: '0.4rem 1rem', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                Force Scan
              </button>
            </div>
          </div>

          <div className="scan-interval-selector" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', backgroundColor: 'var(--panel-bg)', padding: '0.3rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Auto-Scan:</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" className="stopwatch-input" value={localInterval.d}
                onChange={e => setLocalInterval({...localInterval, d: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">d</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" max="23" className="stopwatch-input" value={localInterval.h}
                onChange={e => setLocalInterval({...localInterval, h: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">h</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <input 
                type="number" min="0" max="59" className="stopwatch-input" value={localInterval.m}
                onChange={e => setLocalInterval({...localInterval, m: Number(e.target.value)})}
                onBlur={handleApplyInterval}
              /><span className="stopwatch-label">m</span>
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
