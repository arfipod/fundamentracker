import { useEffect, useState, type FormEvent } from 'react';
import { apiFetch } from '../lib/apiClient';
import type { Theme } from '../hooks/useTheme';
import { Icon } from './Icon';

interface Props {
  scanInterval: number;
  lastScanTime: number;
  isScanning: boolean;
  currentServerTime: number;
  nextScanTime: number;
  theme: Theme;
  onToggleTheme: () => void;
  onUpdateInterval: (interval: number) => void;
  onForceScan: () => void;
}

interface MarketStat { symbol: string; current: number; change_percent: number; }
interface IntervalParts { d: number; h: number; m: number; }

function intervalParts(totalSeconds: number): IntervalParts {
  return { d: Math.floor(totalSeconds / 86400), h: Math.floor((totalSeconds % 86400) / 3600), m: Math.floor((totalSeconds % 3600) / 60) };
}
function intervalSeconds(parts: IntervalParts) { return (parts.d * 86400) + (parts.h * 3600) + (parts.m * 60); }
function formatClock(timestamp: number, fallback: string) {
  if (!timestamp) return fallback;
  return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function formatSchedule(seconds: number) {
  if (seconds <= 0) return 'Manual only';
  const parts = intervalParts(seconds);
  const values = [parts.d ? `${parts.d}d` : '', parts.h ? `${parts.h}h` : '', parts.m ? `${parts.m}m` : ''].filter(Boolean);
  return values.join(' ') || 'Under 1m';
}
function clamp(value: string, max?: number) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number) || number < 0) return 0;
  return max === undefined ? number : Math.min(number, max);
}

export function DashboardHeader({ scanInterval, lastScanTime, isScanning, currentServerTime, nextScanTime, theme, onToggleTheme, onUpdateInterval, onForceScan }: Props) {
  const [localInterval, setLocalInterval] = useState<IntervalParts>(() => intervalParts(scanInterval));
  const [marketStats, setMarketStats] = useState<MarketStat[]>([]);

  useEffect(() => { setLocalInterval(intervalParts(scanInterval)); }, [scanInterval]);
  useEffect(() => {
    const fetchMarketStats = async () => {
      try {
        const response = await apiFetch('/market-overview');
        if (response.ok) setMarketStats(await response.json());
      } catch (error) {
        console.error('Market overview could not be loaded.', error);
      }
    };
    void fetchMarketStats();
    const refreshTimer = window.setInterval(fetchMarketStats, 300000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  const localSeconds = intervalSeconds(localInterval);
  const scheduleChanged = localSeconds !== scanInterval;
  const handleScheduleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (scheduleChanged) onUpdateInterval(localSeconds);
  };

  return (
    <>
      {marketStats.length > 0 && (
        <div className="market-strip" aria-label="Market overview">
          <div className="market-strip-track">
            {marketStats.map((stat) => (
              <div className="market-quote" key={stat.symbol}>
                <strong>{stat.symbol}</strong>
                <span className="market-price">{stat.current.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                <span className={stat.change_percent >= 0 ? 'market-change positive' : 'market-change negative'}>
                  {stat.change_percent >= 0 ? '+' : ''}{stat.change_percent.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <header className="product-header">
        <div className="header-main">
          <div className="brand">
            <div className="brand-line"><span className="brand-status" aria-hidden="true" /><h1>FundamenTracker</h1></div>
            <p>Private company research and valuation alerts</p>
          </div>
          <div className="header-actions">
            <button type="button" className="icon-button" onClick={onToggleTheme} title={`Use ${theme === 'light' ? 'dark' : 'light'} theme`} aria-label={`Use ${theme === 'light' ? 'dark' : 'light'} theme`}>
              <Icon name={theme === 'light' ? 'moon' : 'sun'} />
            </button>
            <button type="button" className="button button-primary" onClick={onForceScan} disabled={isScanning}>
              <Icon name="scan" />{isScanning ? 'Scanning…' : 'Run scan'}
            </button>
          </div>
        </div>

        <div className="header-utility">
          <div className="scan-summary" aria-live="polite">
            <span className={`scan-state-dot${isScanning ? ' scanning' : ''}`} aria-hidden="true" />
            <span>{isScanning ? 'Scan in progress' : `Last scan ${formatClock(lastScanTime, 'not run yet')}`}</span>
            <span className="utility-separator" aria-hidden="true">·</span><span>Next {formatClock(nextScanTime, 'manual')}</span>
            <span className="utility-separator desktop-only" aria-hidden="true">·</span><span className="desktop-only">Server {formatClock(currentServerTime, 'unavailable')}</span>
          </div>

          <details className="scan-settings">
            <summary><Icon name="settings" /><span>Auto scan</span><strong>{formatSchedule(scanInterval)}</strong><Icon name="chevronDown" className="disclosure-chevron" /></summary>
            <form className="scan-settings-panel" onSubmit={handleScheduleSubmit}>
              <p>Set the interval between automatic scans. Use zero in every field for manual scans only.</p>
              <div className="schedule-fields">
                <label><span>Days</span><input type="number" min="0" inputMode="numeric" value={localInterval.d} onChange={(event) => setLocalInterval({ ...localInterval, d: clamp(event.target.value) })} /></label>
                <label><span>Hours</span><input type="number" min="0" max="23" inputMode="numeric" value={localInterval.h} onChange={(event) => setLocalInterval({ ...localInterval, h: clamp(event.target.value, 23) })} /></label>
                <label><span>Minutes</span><input type="number" min="0" max="59" inputMode="numeric" value={localInterval.m} onChange={(event) => setLocalInterval({ ...localInterval, m: clamp(event.target.value, 59) })} /></label>
              </div>
              <button className="button button-secondary button-small" type="submit" disabled={!scheduleChanged}>Apply schedule</button>
            </form>
          </details>
        </div>
      </header>
    </>
  );
}
