import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { apiFetch } from '../lib/apiClient';
import { Icon } from './Icon';

interface HistoryData { date: string; value: number; }
interface MetricChartProps { ticker: string; metric: string; currentValue?: number | null; targetValue?: number | null; height?: number; showPeriodToggle?: boolean; showReferenceLineToggle?: boolean; }
const PERIODS = [{ label: '1M', value: '1mo' }, { label: '3M', value: '3mo' }, { label: '6M', value: '6mo' }, { label: '1Y', value: '1y' }, { label: '2Y', value: '2y' }, { label: '5Y', value: '5y' }, { label: '10Y', value: '10y' }, { label: 'Max', value: 'max' }];

export function MetricChart({ ticker, metric, currentValue, targetValue, height = 400, showPeriodToggle = true, showReferenceLineToggle = true }: MetricChartProps) {
  const [period, setPeriod] = useState('1y'); const [historyData, setHistoryData] = useState<HistoryData[]>([]); const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const [showMax, setShowMax] = useState(false); const [showMin, setShowMin] = useState(false); const [showAvg, setShowAvg] = useState(false); const [showMedian, setShowMedian] = useState(false); const [showStdDev, setShowStdDev] = useState(false); const [showCurrent, setShowCurrent] = useState(false); const [showTarget, setShowTarget] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const fetchHistory = async () => {
      if (!ticker || !metric) return; setLoading(true); setError(null);
      try {
        const response = await apiFetch(`/history?ticker=${encodeURIComponent(ticker)}&metric=${encodeURIComponent(metric)}&period=${encodeURIComponent(period)}`, { signal: controller.signal });
        if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'Historical data could not be loaded.'); }
        setHistoryData(await response.json());
      } catch (historyError) {
        if (!(historyError instanceof DOMException && historyError.name === 'AbortError')) { setError(historyError instanceof Error ? historyError.message : 'Historical data could not be loaded.'); setHistoryData([]); }
      } finally { if (!controller.signal.aborted) setLoading(false); }
    };
    void fetchHistory(); return () => controller.abort();
  }, [ticker, metric, period]);
  const values = historyData.map((point) => point.value).filter((value) => Number.isFinite(value));
  const dataMax = values.length ? Math.max(...values) : null; const dataMin = values.length ? Math.min(...values) : null; const dataAvg = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  const dataStd = values.length && dataAvg !== null ? Math.sqrt(values.reduce((sum, value) => sum + Math.pow(value - dataAvg, 2), 0) / values.length) : null;
  const sortedValues = [...values].sort((left, right) => left - right);
  const dataMedian = values.length ? values.length % 2 === 0 ? (sortedValues[values.length / 2 - 1] + sortedValues[values.length / 2]) / 2 : sortedValues[Math.floor(values.length / 2)] : null;

  return (
    <div className="metric-chart-container">
      <div className="chart-toolbar">
        {showPeriodToggle && <div className="period-selector" aria-label="Chart period">{PERIODS.map((option) => <button key={option.value} type="button" className={period === option.value ? 'active' : ''} aria-pressed={period === option.value} onClick={() => setPeriod(option.value)}>{option.label}</button>)}</div>}
        {showReferenceLineToggle && <details className="chart-options"><summary><Icon name="settings" size={16} />Reference lines</summary><div className="chart-option-list"><label><input type="checkbox" checked={showMax} onChange={(event) => setShowMax(event.target.checked)} />Maximum</label><label><input type="checkbox" checked={showMin} onChange={(event) => setShowMin(event.target.checked)} />Minimum</label><label><input type="checkbox" checked={showAvg} onChange={(event) => setShowAvg(event.target.checked)} />Average</label><label><input type="checkbox" checked={showMedian} onChange={(event) => setShowMedian(event.target.checked)} />Median</label><label><input type="checkbox" checked={showStdDev} onChange={(event) => setShowStdDev(event.target.checked)} />±1 standard deviation</label>{currentValue !== undefined && currentValue !== null && <label><input type="checkbox" checked={showCurrent} onChange={(event) => setShowCurrent(event.target.checked)} />Current value</label>}{targetValue !== undefined && targetValue !== null && <label><input type="checkbox" checked={showTarget} onChange={(event) => setShowTarget(event.target.checked)} />Alert target</label>}</div></details>}
      </div>
      {loading ? <div className="chart-state" style={{ minHeight: height }} role="status">Loading history…</div> : error ? <div className="chart-state chart-error" style={{ minHeight: height }} role="alert">{error}</div> : historyData.length > 0 ? (
        <div className="chart-canvas" style={{ height }} role="img" aria-label={`${ticker} ${metric} history for ${period}`}><ResponsiveContainer><LineChart data={historyData} margin={{ top: 16, right: 20, left: 0, bottom: 4 }}><CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="3 5" /><XAxis dataKey="date" stroke="var(--text-subtle)" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} minTickGap={28} tickFormatter={(value) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : `${date.getMonth() + 1}/${date.getFullYear().toString().slice(2)}`; }} /><YAxis stroke="var(--text-subtle)" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} width={52} domain={['auto', 'auto']} /><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--line-strong)', borderRadius: 8, color: 'var(--text)' }} labelStyle={{ color: 'var(--text-muted)' }} itemStyle={{ color: 'var(--chart-line)' }} /><Line type="monotone" dataKey="value" name={metric.toUpperCase()} stroke="var(--chart-line)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          {showMax && dataMax !== null && <ReferenceLine y={dataMax} label={{ value: 'Max', position: 'insideTopLeft', fill: 'var(--danger)' }} stroke="var(--danger)" strokeDasharray="4 4" />}{showMin && dataMin !== null && <ReferenceLine y={dataMin} label={{ value: 'Min', position: 'insideBottomLeft', fill: 'var(--positive)' }} stroke="var(--positive)" strokeDasharray="4 4" />}{showAvg && dataAvg !== null && <ReferenceLine y={dataAvg} label={{ value: 'Average', position: 'insideBottomLeft', fill: 'var(--warning)' }} stroke="var(--warning)" strokeDasharray="4 4" />}{showStdDev && dataAvg !== null && dataStd !== null && <ReferenceLine y={dataAvg + dataStd} label={{ value: '+1 SD', position: 'insideTopLeft', fill: 'var(--warning)' }} stroke="var(--warning)" strokeDasharray="4 4" opacity={0.6} />}{showStdDev && dataAvg !== null && dataStd !== null && <ReferenceLine y={dataAvg - dataStd} label={{ value: '-1 SD', position: 'insideBottomLeft', fill: 'var(--warning)' }} stroke="var(--warning)" strokeDasharray="4 4" opacity={0.6} />}{showMedian && dataMedian !== null && <ReferenceLine y={dataMedian} label={{ value: 'Median', position: 'insideTopLeft', fill: 'var(--chart-secondary)' }} stroke="var(--chart-secondary)" strokeDasharray="4 4" />}{showCurrent && currentValue !== null && currentValue !== undefined && <ReferenceLine y={currentValue} label={{ value: 'Current', position: 'right', fill: 'var(--chart-current)' }} stroke="var(--chart-current)" strokeDasharray="4 4" />}{showTarget && targetValue !== null && targetValue !== undefined && <ReferenceLine y={targetValue} label={{ value: 'Target', position: 'left', fill: 'var(--chart-target)' }} stroke="var(--chart-target)" strokeDasharray="4 4" />}
        </LineChart></ResponsiveContainer></div>
      ) : <div className="chart-state" style={{ minHeight: height }}>No historical observations are available for this period.</div>}
    </div>
  );
}
