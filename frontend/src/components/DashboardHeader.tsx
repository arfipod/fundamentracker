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
    <header className="header" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>FundamenTracker Dashboard</h1>
          {marketStats.length > 0 && (
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.85rem' }}>
              {marketStats.map(stat => (
                <div key={stat.symbol} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.2rem 0.5rem', background: 'var(--panel-bg)', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontWeight: 'bold' }}>{stat.symbol}</span>
                  <span>{stat.current.toFixed(2)}</span>
                  <span style={{ color: stat.change_percent >= 0 ? '#10b981' : '#ef4444' }}>
                    {stat.change_percent >= 0 ? '▲' : '▼'} {Math.abs(stat.change_percent).toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="header-actions" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="scan-interval-selector" style={{ display: 'flex', flexWrap: 'nowrap', whiteSpace: 'nowrap', alignItems: 'center', gap: '0.4rem', backgroundColor: 'var(--panel-bg)', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.5rem' }}>Auto-Scan:</label>
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
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {isScanning && <span style={{ fontSize: '0.85rem', color: 'var(--primary)', fontWeight: 'bold' }}>Scanning...</span>}
              <button className="btn-primary" onClick={onForceScan} disabled={isScanning}>
                Force Scan
              </button>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '4px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Server time: {new Date(currentServerTime * 1000).toLocaleTimeString()}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Last scan: {lastScanTime ? new Date(lastScanTime * 1000).toLocaleTimeString() : 'Nunca'}
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Next scan: {nextScanTime ? new Date(nextScanTime * 1000).toLocaleTimeString() : 'Manual'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
