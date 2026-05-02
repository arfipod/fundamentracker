import { useState, useEffect } from 'react';

interface Props {
  scanInterval: number;
  lastScanTime: number;
  isScanning: boolean;
  currentServerTime: number;
  nextScanTime: number;
  onUpdateInterval: (interval: number) => void;
  onForceScan: () => void;
}

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

  useEffect(() => {
    setLocalInterval({
      d: Math.floor(scanInterval / 86400),
      h: Math.floor((scanInterval % 86400) / 3600),
      m: Math.floor((scanInterval % 3600) / 60)
    });
  }, [scanInterval]);

  const handleApplyInterval = () => {
    const total = (localInterval.d * 86400) + (localInterval.h * 3600) + (localInterval.m * 60);
    if (total !== scanInterval) {
      onUpdateInterval(total);
    }
  };

  return (
    <header className="header">
      <h1>FundamenTracker Dashboard</h1>
      <div className="header-actions" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
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
    </header>
  );
}
